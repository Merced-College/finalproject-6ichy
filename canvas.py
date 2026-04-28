"""
canvas.py  —  Air Writing Edition
-----------------------------------
Receives 6-axis IMU data (accel + gyro) over UDP.
Uses a Madgwick filter to estimate orientation and remove gravity,
then double-integrates clean linear acceleration to get cursor position.
Zero-velocity detection (ZUPT) kills drift when hand is still.

Controls:
    SPACE  — toggle pen down/up
    S      — save canvas as PNG
    C      — clear canvas
    Q      — quit
"""

import tkinter as tk
import socket
import struct
import threading
import math
import subprocess
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
UDP_PORT      = 5005
CANVAS_W      = 560
CANVAS_H      = 560
BRUSH_RADIUS  = 4
SAVE_DIR      = Path("saved_images")
DT            = 1.0 / 119.0

# path to the compiled C++ processor
CPP_PROCESSOR = "./stroke_processor"

# Madgwick filter tuning
BETA          = 0.033                 # lower = smoother but slower to correct

# Position scaling — how many pixels per (m/s²·s²)
# Tune this if cursor moves too fast or slow
PIXEL_SCALE   = 4500.0

# ZUPT (zero velocity update) — if accel magnitude stays near 1g, hand is still
ZUPT_THRESHOLD = 0.03                # g — variance threshold to detect stillness
ZUPT_WINDOW    = 12                  # samples to average over (~100ms)
# ─────────────────────────────────────────────────────────────────────────────

G = 9.81  # m/s²


# ── Madgwick AHRS filter (pure Python) ───────────────────────────────────────
class Madgwick:
    """
    Madgwick sensor fusion filter.
    Fuses accelerometer + gyroscope to estimate orientation quaternion.
    Ref: https://x-io.co.uk/open-source-imu-and-ahrs-algorithms/
    """

    def __init__(self, beta=BETA):
        self.beta = beta
        self.q = [1.0, 0.0, 0.0, 0.0]  # w, x, y, z

    def update(self, ax, ay, az, gx, gy, gz, dt):
        q1, q2, q3, q4 = self.q

        # Convert gyro from dps to rad/s
        gx = math.radians(gx)
        gy = math.radians(gy)
        gz = math.radians(gz)

        # Normalize accelerometer
        norm = math.sqrt(ax*ax + ay*ay + az*az)
        if norm == 0:
            return
        ax /= norm; ay /= norm; az /= norm

        # Gradient descent step
        f1 = 2*(q2*q4 - q1*q3) - ax
        f2 = 2*(q1*q2 + q3*q4) - ay
        f3 = 2*(0.5 - q2*q2 - q3*q3) - az

        j11 = 2*q3; j12 = 2*q4; j13 = 2*q1; j14 = 2*q2
        j31 = -4*q2; j32 = -4*q3

        step1 = j13*f2 - j11*f3
        step2 = j14*f2 + j12*f3 + j31*f1  # fixed sign
        step3 = -j11*f2 + j32*f1
        step4 = j14*f1 + j12*f2

        # Normalize step
        norm = math.sqrt(step1**2 + step2**2 + step3**2 + step4**2)
        if norm == 0:
            return
        step1 /= norm; step2 /= norm; step3 /= norm; step4 /= norm

        # Integrate quaternion rate
        q_dot1 = 0.5*(-q2*gx - q3*gy - q4*gz) - self.beta*step1
        q_dot2 = 0.5*( q1*gx + q3*gz - q4*gy) - self.beta*step2
        q_dot3 = 0.5*( q1*gy - q2*gz + q4*gx) - self.beta*step3
        q_dot4 = 0.5*( q1*gz + q2*gy - q3*gx) - self.beta*step4

        q1 += q_dot1 * dt
        q2 += q_dot2 * dt
        q3 += q_dot3 * dt
        q4 += q_dot4 * dt

        norm = math.sqrt(q1**2 + q2**2 + q3**2 + q4**2)
        self.q = [q1/norm, q2/norm, q3/norm, q4/norm]

    def remove_gravity(self, ax, ay, az):
        """Rotate gravity vector into sensor frame and subtract it."""
        q1, q2, q3, q4 = self.q

        # Gravity in world frame = [0, 0, 1g]
        # Rotate to body frame using conjugate of q
        gx = 2*(q2*q4 - q1*q3)
        gy = 2*(q1*q2 + q3*q4)
        gz = q1**2 - q2**2 - q3**2 + q4**2

        # Subtract gravity estimate (in g units)
        lax = ax - gx
        lay = ay - gy
        laz = az - gz

        return lax, lay, laz

    def world_acceleration(self, ax, ay, az):
        """Rotate linear acceleration from body frame to world frame."""
        q1, q2, q3, q4 = self.q
        lax, lay, laz = self.remove_gravity(ax, ay, az)

        # Rotate to world frame
        wx = (1 - 2*(q3**2 + q4**2))*lax + 2*(q2*q3 - q1*q4)*lay + 2*(q2*q4 + q1*q3)*laz
        wy = 2*(q2*q3 + q1*q4)*lax + (1 - 2*(q2**2 + q4**2))*lay + 2*(q3*q4 - q1*q2)*laz

        return wx, wy   # x and y in world frame (g units)


# ── ZUPT detector ─────────────────────────────────────────────────────────────
class ZUPTDetector:
    """Detects when the hand is stationary by checking accel variance."""

    def __init__(self, window=ZUPT_WINDOW, threshold=ZUPT_THRESHOLD):
        self.window    = window
        self.threshold = threshold
        self.history   = []

    def update(self, ax, ay, az):
        mag = math.sqrt(ax**2 + ay**2 + az**2)
        self.history.append(mag)
        if len(self.history) > self.window:
            self.history.pop(0)

        if len(self.history) < self.window:
            return False

        mean = sum(self.history) / len(self.history)
        var  = sum((v - mean)**2 for v in self.history) / len(self.history)
        return var < self.threshold


# ── UDP receiver thread ───────────────────────────────────────────────────────
class IMUReceiver(threading.Thread):
    def __init__(self, port, callback):
        super().__init__(daemon=True)
        self.callback = callback
        self.sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", port))
        self.sock.settimeout(1.0)

    def run(self):
        # 28 bytes: 6 floats + 1 uint32
        fmt  = "ffffffI"
        size = struct.calcsize(fmt)
        while True:
            try:
                data, _ = self.sock.recvfrom(size)
                if len(data) == size:
                    ax, ay, az, gx, gy, gz, seq = struct.unpack(fmt, data)
                    self.callback(ax, ay, az, gx, gy, gz)
            except socket.timeout:
                continue
            except Exception:
                break


# ── Main canvas app ───────────────────────────────────────────────────────────
class CanvasApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TinyML Air Writing Canvas")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e1e")

        # Filter + detector
        self.madgwick = Madgwick()
        self.zupt     = ZUPTDetector()

        # Integration state
        self.vel_x    = 0.0
        self.vel_y    = 0.0
        self.cursor_x = float(CANVAS_W // 2)
        self.cursor_y = float(CANVAS_H // 2)
        self.last_x   = self.cursor_x
        self.last_y   = self.cursor_y

        self.pen_down     = False
        self.sample_count = 0

        # current stroke points — collected while pen is down
        # sent to C++ when pen is lifted
        self.current_stroke = []

        # launch the C++ stroke processor as a subprocess
        # stdin=PIPE lets us write to it, stdout=PIPE lets us read from it
        try:
            self.cpp = subprocess.Popen(
                [CPP_PROCESSOR],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,          # work with strings not bytes
                bufsize=1           # line buffered so data flows immediately
            )
            # start a thread to listen for responses from C++
            threading.Thread(target=self._read_cpp_output, daemon=True).start()
        except FileNotFoundError:
            self.cpp = None
            print(f"[WARN] C++ processor not found at {CPP_PROCESSOR} — export disabled")

        self._build_ui()
        self._start_receiver()

    def _build_ui(self):
        self.status_var = tk.StringVar(value="Waiting for IMU data...")
        tk.Label(self.root, textvariable=self.status_var,
                 bg="#1e1e1e", fg="#aaaaaa",
                 font=("Menlo", 11), anchor="w"
                 ).pack(fill=tk.X, padx=12, pady=(10, 2))

        self.canvas = tk.Canvas(
            self.root, width=CANVAS_W, height=CANVAS_H,
            bg="black", highlightthickness=2,
            highlightbackground="#444444", cursor="crosshair"
        )
        self.canvas.pack(padx=12, pady=(0, 6))

        r = 5
        cx, cy = CANVAS_W // 2, CANVAS_H // 2
        self.dot = self.canvas.create_oval(
            cx-r, cy-r, cx+r, cy+r,
            fill="red", outline="", tags="cursor"
        )

        btn_frame = tk.Frame(self.root, bg="#1e1e1e")
        btn_frame.pack(pady=(0, 12))

        def btn(text, cmd, color):
            return tk.Button(btn_frame, text=text, command=cmd,
                             bg=color, fg="white", font=("Menlo", 11),
                             relief=tk.FLAT, padx=14, pady=6,
                             activebackground=color, cursor="hand2")

        self._pen_btn = btn("✏  Pen UP  [SPACE]", self._toggle_pen, "#555555")
        self._pen_btn.pack(side=tk.LEFT, padx=5)
        btn("💾  Save  [S]", self._save,  "#3c763d").pack(side=tk.LEFT, padx=5)
        btn("🗑  Clear [C]", self._clear, "#a94442").pack(side=tk.LEFT, padx=5)

        self.root.bind("<space>", lambda e: self._toggle_pen())
        self.root.bind("s",       lambda e: self._save())
        self.root.bind("c",       lambda e: self._clear())
        self.root.bind("q",       lambda e: self.root.destroy())

    def _start_receiver(self):
        IMUReceiver(UDP_PORT, self._on_imu).start()
        self.status_var.set(f"Listening on :{UDP_PORT} — hold still to calibrate, then press SPACE")

    def _send_to_cpp(self, message):
        # sends a line of text to the C++ subprocess via stdin
        # does nothing if C++ processor wasn't found
        if self.cpp and self.cpp.poll() is None:
            self.cpp.stdin.write(message + "\n")
            self.cpp.stdin.flush()

    def _read_cpp_output(self):
        # runs in background thread — listens for responses from C++
        # and updates the status bar when a save completes
        for line in self.cpp.stdout:
            line = line.strip()
            if line.startswith("SAVED"):
                self.root.after(0, self.status_var.set, f"✓ {line}")
            elif line.startswith("ERROR"):
                self.root.after(0, self.status_var.set, f"✗ {line}")

    def _on_imu(self, ax, ay, az, gx, gy, gz):
        self.root.after(0, self._process, ax, ay, az, gx, gy, gz)

    def _process(self, ax, ay, az, gx, gy, gz):
        self.sample_count += 1

        # 1. Update Madgwick orientation estimate
        self.madgwick.update(ax, ay, az, gx, gy, gz, DT)

        # 2. Detect if hand is still → zero velocity
        still = self.zupt.update(ax, ay, az)
        if still:
            self.vel_x = 0.0
            self.vel_y = 0.0

        # 3. Get world-frame linear acceleration (gravity removed)
        world_ax, world_ay = self.madgwick.world_acceleration(ax, ay, az)

        # 4. Integrate acceleration → velocity (skip if still)
        if not still:
            self.vel_x += world_ax * G * DT   # m/s
            self.vel_y += world_ay * G * DT

        # 5. Integrate velocity → position
        dx = self.vel_x * DT * PIXEL_SCALE
        dy = self.vel_y * DT * PIXEL_SCALE

        new_x = max(0, min(CANVAS_W, self.cursor_x + dx))
        new_y = max(0, min(CANVAS_H, self.cursor_y + dy))

        if self.pen_down:
            self._draw_segment(self.cursor_x, self.cursor_y, new_x, new_y)
            # collect the point for C++ processing
            self.current_stroke.append((int(new_x), int(new_y)))

        self.cursor_x = new_x
        self.cursor_y = new_y
        self._move_dot(new_x, new_y)

        # Update status every 60 samples
        if self.sample_count % 60 == 0:
            state = "✏ DRAWING" if self.pen_down else "pen UP"
            zupt  = " | STILL" if still else ""
            self.status_var.set(f"{state}{zupt}  |  vel=({self.vel_x:.2f}, {self.vel_y:.2f})")

    def _draw_segment(self, x0, y0, x1, y1):
        r = BRUSH_RADIUS
        self.canvas.create_oval(x1-r, y1-r, x1+r, y1+r,
                                fill="white", outline="", tags="stroke")
        self.canvas.create_line(x0, y0, x1, y1,
                                fill="white", width=r*2,
                                capstyle=tk.ROUND, smooth=True,
                                tags="stroke")
        self.canvas.tag_raise("cursor")

    def _move_dot(self, x, y):
        r = 5
        self.canvas.coords(self.dot, x-r, y-r, x+r, y+r)

    def _toggle_pen(self):
        self.pen_down = not self.pen_down
        if self.pen_down:
            # pen going down — tell C++ a new stroke is starting
            self.current_stroke = []
            self._send_to_cpp("BEGIN")
            self.status_var.set("✏  Pen DOWN — write in the air")
            self._pen_btn.config(text="✏  Pen DOWN [SPACE]", bg="#2a6496")
        else:
            # pen going up — send all collected points then END
            for x, y in self.current_stroke:
                self._send_to_cpp(f"{x},{y}")
            self._send_to_cpp("END")
            self.vel_x = 0.0
            self.vel_y = 0.0
            self.current_stroke = []
            self.status_var.set("Pen UP — reposition freely")
            self._pen_btn.config(text="✏  Pen UP  [SPACE]", bg="#555555")

    def _save(self):
        # tell C++ to process and export all recorded strokes
        self._send_to_cpp("SAVE")
        self.status_var.set("Saving...")

    def _clear(self):
        self.canvas.delete("stroke")
        self.pen_down       = False
        self.vel_x          = 0.0
        self.vel_y          = 0.0
        self.cursor_x       = float(CANVAS_W // 2)
        self.cursor_y       = float(CANVAS_H // 2)
        self.current_stroke = []
        self._move_dot(self.cursor_x, self.cursor_y)
        self._pen_btn.config(text="✏  Pen UP  [SPACE]", bg="#555555")
        self._send_to_cpp("CLEAR")
        self.status_var.set("Canvas cleared")


if __name__ == "__main__":
    root = tk.Tk()
    CanvasApp(root)
    root.mainloop()