"""
canvas.py — Gyroscope Edition
------------------------------
Receives XY gyroscope data over UDP from serial_reader (C++).
Maps rotation rate to cursor movement on a tkinter canvas.
Sends completed strokes to stroke_processor (C++) for export.

Controls:
    SPACE  — toggle pen down/up
    S      — save via C++ processor
    C      — clear canvas
    Q      — quit
"""

import tkinter as tk
import socket
import struct
import threading
import subprocess
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
UDP_PORT      = 5005
CANVAS_W      = 560
CANVAS_H      = 560
BRUSH_RADIUS  = 4
DT            = 1.0 / 119.0   # seconds per sample
SENSITIVITY   = 0.015          # dps → pixels (tune if too fast/slow)
CPP_PROCESSOR = "./stroke_processor"
# ─────────────────────────────────────────────────────────────────────────────


class IMUReceiver(threading.Thread):
    def __init__(self, port, callback):
        super().__init__(daemon=True)
        self.callback = callback
        self.sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", port))
        self.sock.settimeout(1.0)

    def run(self):
        # 12 bytes: float x, float y, uint32 seq
        fmt  = "ffI"
        size = struct.calcsize(fmt)
        while True:
            try:
                data, _ = self.sock.recvfrom(size)
                if len(data) == size:
                    x, y, seq = struct.unpack(fmt, data)
                    self.callback(x, y)
            except socket.timeout:
                continue
            except Exception:
                break


class CanvasApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TinyML Handwriting Canvas")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e1e")

        self.cursor_x       = float(CANVAS_W // 2)
        self.cursor_y       = float(CANVAS_H // 2)
        self.pen_down       = False
        self.current_stroke = []

        self._build_ui()
        self._launch_cpp()
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
        self.dot = self.canvas.create_oval(
            CANVAS_W//2-r, CANVAS_H//2-r,
            CANVAS_W//2+r, CANVAS_H//2+r,
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

    def _launch_cpp(self):
        try:
            self.cpp = subprocess.Popen(
                [CPP_PROCESSOR],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            threading.Thread(target=self._read_cpp_output, daemon=True).start()
            self.status_var.set("C++ processor ready")
        except FileNotFoundError:
            self.cpp = None
            self.status_var.set("[WARN] stroke_processor not found — export disabled")

    def _send_to_cpp(self, message):
        if self.cpp and self.cpp.poll() is None:
            self.cpp.stdin.write(message + "\n")
            self.cpp.stdin.flush()

    def _read_cpp_output(self):
        for line in self.cpp.stdout:
            line = line.strip()
            if line.startswith("SAVED"):
                self.root.after(0, self.status_var.set, f"✓ {line}")
            elif line.startswith("ERROR"):
                self.root.after(0, self.status_var.set, f"✗ {line}")

    def _start_receiver(self):
        IMUReceiver(UDP_PORT, self._on_imu).start()
        self.status_var.set(f"Listening on :{UDP_PORT} — press SPACE to draw")

    def _on_imu(self, gx, gy):
        self.root.after(0, self._update_cursor, gx, gy)

    def _update_cursor(self, gx, gy):
        dx = gx * DT * SENSITIVITY * CANVAS_W
        dy = -gy * DT * SENSITIVITY * CANVAS_H  # negated for natural orientation

        self.cursor_x = max(0, min(CANVAS_W, self.cursor_x + dx))
        self.cursor_y = max(0, min(CANVAS_H, self.cursor_y + dy))

        if self.pen_down:
            self.current_stroke.append((int(self.cursor_x), int(self.cursor_y)))
            self._draw_segment(self.cursor_x, self.cursor_y)

        self._move_dot(self.cursor_x, self.cursor_y)

    def _draw_segment(self, x, y):
        r = BRUSH_RADIUS
        if len(self.current_stroke) >= 2:
            prev = self.current_stroke[-2]
            self.canvas.create_line(prev[0], prev[1], x, y,
                                    fill="white", width=r*2,
                                    capstyle=tk.ROUND, smooth=True,
                                    tags="stroke")
        self.canvas.create_oval(x-r, y-r, x+r, y+r,
                                fill="white", outline="", tags="stroke")
        self.canvas.tag_raise("cursor")

    def _move_dot(self, x, y):
        r = 5
        self.canvas.coords(self.dot, x-r, y-r, x+r, y+r)

    def _toggle_pen(self):
        self.pen_down = not self.pen_down
        if self.pen_down:
            self.current_stroke = []
            self._send_to_cpp("BEGIN")
            self.status_var.set("✏  Pen DOWN — drawing")
            self._pen_btn.config(text="✏  Pen DOWN [SPACE]", bg="#2a6496")
        else:
            for x, y in self.current_stroke:
                self._send_to_cpp(f"{x},{y}")
            self._send_to_cpp("END")
            self.current_stroke = []
            self.status_var.set("Pen UP — reposition freely")
            self._pen_btn.config(text="✏  Pen UP  [SPACE]", bg="#555555")

    def _save(self):
        self._send_to_cpp("SAVE")
        self.status_var.set("Saving...")

    def _clear(self):
        self.canvas.delete("stroke")
        self.pen_down       = False
        self.current_stroke = []
        self.cursor_x       = float(CANVAS_W // 2)
        self.cursor_y       = float(CANVAS_H // 2)
        self._move_dot(self.cursor_x, self.cursor_y)
        self._pen_btn.config(text="✏  Pen UP  [SPACE]", bg="#555555")
        self._send_to_cpp("CLEAR")
        self.status_var.set("Canvas cleared")


if __name__ == "__main__":
    root = tk.Tk()
    CanvasApp(root)
    root.mainloop()