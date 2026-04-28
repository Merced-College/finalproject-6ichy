"""
train_model.py
---------------
Trains a simple CNN on the MNIST dataset and saves it as mnist_model.h5.
Only needs to be run once. Takes about 1-2 minutes.

Run:
    python3 train_model.py
"""

import tensorflow as tf
from tensorflow import keras

print("Loading MNIST dataset...")
(x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()

# Normalize pixel values from 0-255 to 0-1
x_train = x_train / 255.0
x_test  = x_test  / 255.0

# Add channel dimension — keras expects (samples, 28, 28, 1)
x_train = x_train.reshape(-1, 28, 28, 1)
x_test  = x_test.reshape(-1, 28, 28, 1)

print("Building model...")
model = keras.Sequential([
    # First conv layer — learns basic features like edges
    keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(28, 28, 1)),
    keras.layers.MaxPooling2D((2, 2)),

    # Second conv layer — learns more complex features
    keras.layers.Conv2D(64, (3, 3), activation='relu'),
    keras.layers.MaxPooling2D((2, 2)),

    # Flatten and classify
    keras.layers.Flatten(),
    keras.layers.Dense(64, activation='relu'),
    keras.layers.Dense(10, activation='softmax')  # 10 outputs — digits 0-9
])

model.compile(
    optimizer='adam',
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

model.summary()

print("\nTraining...")
model.fit(x_train, y_train, epochs=5, validation_split=0.1, verbose=1)

# Evaluate on test set
loss, accuracy = model.evaluate(x_test, y_test, verbose=0)
print(f"\nTest accuracy: {accuracy:.2%}")

# Save the model
model.save("mnist_model.h5")
print("Model saved as mnist_model.h5")