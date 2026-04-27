"""
canvas.py
---------
Receives XY gyroscope data over UDP from serial_reader (C++).
Integrates rotation rate → cursor position and draws on a tkinter canvas.

Run alongside serial_reader:
    Terminal 1: ./serial_reader /dev/cu.usbmodem1101
    Terminal 2: python3 canvas.py

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
import time
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
UDP_PORT     = 5005
CANVAS_W     = 560
CANVAS_H     = 560
SENSITIVITY  = 0.015        # dps → pixels (tune this)
BRUSH_RADIUS = 4
SAVE_DIR     = Path("saved_images")
SAMPLE_RATE  = 119.0
DT           = 1.0 / SAMPLE_RATE
# ─────────────────────────────────────────────────────────────────────────────


class IMUReceiver(threading.Thread):
    def __init__(self, port, callback):
        super().__init__(daemon=True)
        self.port     = port
        self.callback = callback
        self.sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", port))
        self.sock.settimeout(1.0)

    def run(self):
        while True:
            try:
                data, _ = self.sock.recvfrom(12)
                if len(data) == 12:
                    x, y, seq = struct.unpack("ffI", data)
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

        self.cursor_x    = float(CANVAS_W // 2)
        self.cursor_y    = float(CANVAS_H // 2)
        self.pen_down    = False
        self.last_draw_x = self.cursor_x
        self.last_draw_y = self.cursor_y

        self._build_ui()
        self._start_receiver()

    def _build_ui(self):
        self.status_var = tk.StringVar(value="Pen UP — press SPACE to draw")
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
        self.receiver = IMUReceiver(UDP_PORT, self._on_imu)
        self.receiver.start()
        self.status_var.set(f"Listening on UDP :{UDP_PORT} — pen UP")

    def _on_imu(self, gx, gy):
        self.root.after(0, self._update_cursor, gx, gy)

    def _update_cursor(self, gx, gy):
        dx = gx * DT * SENSITIVITY * CANVAS_W
        dy = gy * DT * SENSITIVITY * CANVAS_H

        self.cursor_x = max(0, min(CANVAS_W, self.cursor_x + dx))
        self.cursor_y = max(0, min(CANVAS_H, self.cursor_y + dy))

        if self.pen_down:
            self._draw_segment(self.last_draw_x, self.last_draw_y,
                               self.cursor_x,   self.cursor_y)

        self.last_draw_x = self.cursor_x
        self.last_draw_y = self.cursor_y
        self._move_dot(self.cursor_x, self.cursor_y)

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
            self.last_draw_x = self.cursor_x
            self.last_draw_y = self.cursor_y
            self.status_var.set("✏  Pen DOWN — drawing")
            self._pen_btn.config(text="✏  Pen DOWN [SPACE]", bg="#2a6496")
        else:
            self.status_var.set("Pen UP — reposition freely")
            self._pen_btn.config(text="✏  Pen UP  [SPACE]", bg="#555555")

    def _save(self):
        try:
            from PIL import ImageGrab
        except ImportError:
            self.status_var.set("Install Pillow: pip install pillow")
            return
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = SAVE_DIR / f"char_{ts}.png"
        self.canvas.update()
        x = self.root.winfo_rootx() + self.canvas.winfo_x()
        y = self.root.winfo_rooty() + self.canvas.winfo_y()
        img = ImageGrab.grab(bbox=(x, y, x + CANVAS_W, y + CANVAS_H))
        img.save(path)
        self.status_var.set(f"Saved → {path.name}")

    def _clear(self):
        self.canvas.delete("stroke")
        self.pen_down    = False
        self.cursor_x    = float(CANVAS_W // 2)
        self.cursor_y    = float(CANVAS_H // 2)
        self.last_draw_x = self.cursor_x
        self.last_draw_y = self.cursor_y
        self._move_dot(self.cursor_x, self.cursor_y)
        self._pen_btn.config(text="✏  Pen UP  [SPACE]", bg="#555555")
        self.status_var.set("Canvas cleared — pen UP")


if __name__ == "__main__":
    root = tk.Tk()
    app  = CanvasApp(root)
    root.mainloop()