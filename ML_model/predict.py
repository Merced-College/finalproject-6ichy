"""
predict.py
-----------
Loads a saved PGM image and runs it through the trained MNIST model.
Prints the predicted digit and confidence score.

Usage:
    python3 predict.py output_0.pgm

Requires mnist_model.h5 to exist — run train_model.py first.
"""

import sys
import numpy as np
from PIL import Image
import tensorflow as tf

# ── Load model ────────────────────────────────────────────────────────────────
MODEL_PATH = "mnist_model.h5"

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
    img = Image.open(image_path).convert("L")  # open as grayscale
except Exception as e:
    print(f"ERROR could not open image: {e}")
    sys.exit(1)

# Resize to 28x28 just in case
img = img.resize((28, 28))

# Convert to numpy array and normalize to 0-1
pixels = np.array(img) / 255.0

# Reshape to match what the model expects: (1, 28, 28, 1)
pixels = pixels.reshape(1, 28, 28, 1)

# ── Predict ───────────────────────────────────────────────────────────────────
predictions = model.predict(pixels, verbose=0)

# predictions is an array of 10 confidence scores, one per digit
predicted_digit     = np.argmax(predictions[0])
confidence          = predictions[0][predicted_digit] * 100

print(f"Predicted: {predicted_digit}  ({confidence:.1f}% confidence)")

# Show all scores for debugging
print("\nAll scores:")
for digit, score in enumerate(predictions[0]):
    bar = "#" * int(score * 40)
    print(f"  {digit}: {bar} {score*100:.1f}%")