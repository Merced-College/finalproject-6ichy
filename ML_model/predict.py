"""
predict.py
-----------
Loads a saved PGM image and runs it through the trained MNIST model.
Prints the predicted digit and confidence score.
Sends the confidence score to the Arduino Uno over serial to light LEDs.

Usage:
    python3 predict.py output_0.pgm

Requires mnist_model.h5 — run train_model.py first.
"""

import sys
import numpy as np
from PIL import Image
import tensorflow as tf
import serial
import time

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_PATH = "mnist_model.h5"
UNO_PORT   = "/dev/cu.usbmodem101"
UNO_BAUD   = 9600
# ─────────────────────────────────────────────────────────────────────────────

# ── Load model ────────────────────────────────────────────────────────────────
try:
    model = tf.keras.models.load_model(MODEL_PATH)
except Exception as e:
    print(f"ERROR could not load model: {e}")
    print("Run train_model.py first to generate mnist_model.h5")
    sys.exit(1)

# ── Load image ────────────────────────────────────────────────────────────────
if len(sys.argv) < 2:
    print("Usage: python3 predict.py <image.pgm>")
    sys.exit(1)

image_path = sys.argv[1]

try:
    img = Image.open(image_path).convert("L")
except Exception as e:
    print(f"ERROR could not open image: {e}")
    sys.exit(1)

img    = img.resize((28, 28))
pixels = np.array(img) / 255.0
pixels = pixels.reshape(1, 28, 28, 1)

# ── Predict ───────────────────────────────────────────────────────────────────
predictions     = model.predict(pixels, verbose=0)
predicted_digit = np.argmax(predictions[0])
confidence      = predictions[0][predicted_digit] * 100

print(f"Predicted: {predicted_digit}  ({confidence:.1f}% confidence)")

print("\nAll scores:")
for digit, score in enumerate(predictions[0]):
    bar = "#" * int(score * 40)
    print(f"  {digit}: {bar} {score*100:.1f}%")

# ── Send confidence to Arduino Uno ────────────────────────────────────────────
try:
    uno = serial.Serial(UNO_PORT, UNO_BAUD, timeout=2)
    time.sleep(2)  # wait for Uno to reset after connection opens

    uno.write(f"{confidence:.1f}\n".encode())
    print(f"\nSent confidence {confidence:.1f} to Arduino Uno")

    response = uno.readline().decode().strip()
    if response:
        print(f"Uno responded: {response}")

    uno.close()

except Exception as e:
    print(f"\n[WARN] Could not connect to Uno: {e}")
    print("Check that the Uno is connected and UNO_PORT is correct")