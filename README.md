# TinyML Handwriting Recognition System

A handwriting recognition system built around an Arduino Nano 33 BLE Sense and an Arduino Uno. You draw a digit in the air using the BLE microcontroller, it shows up on a canvas on your computer in real time, and a machine learning model identifies what digit you drew and lights up an LED on the Uno based on how confident it is.

---

## How it works

The BLE board reads gyroscope data 119 times per second and streams it over USB serial. A C++ program reads that data and forwards it over UDP to a Python canvas running locally on your machine. When you finish drawing and press save, the canvas sends the stroke data to a C++ stroke processor which smooths it, scales it down to 28x28 pixels, and saves it as a PGM image file. That image is then passed into a pretrained CNN model which returns a predicted digit and a confidence score. The confidence score is sent to the Arduino Uno over serial, which lights a green LED for high confidence and red for low confidence.

**Everything must be run locally on your machine. The canvas, serial reader, and stroke processor all communicate with physical hardware through your USB ports and cannot run in a cloud environment like GitHub Codespaces.**

---

## Hardware Setup

- Arduino Nano 33 BLE Sense
- Arduino Uno
- 1 green LED → pin 12 → 220 ohm resistor → GND
- 1 red LED → pin 13 → 220 ohm resistor → GND

---

## How to Run

### Step 1 — Flash the Arduino boards

Open Arduino IDE and flash the following sketches:

- Flash `BLE_IMU/IMU_Reader/IMU_Reader.ino` onto the **Arduino Nano 33 BLE Sense**
- Flash `Arduino_UNO/LED_Feedback.ino` onto the **Arduino Uno**

You will need the `Arduino_LSM9DS1` library installed. Go to Sketch → Include Library → Manage Libraries and search for it.

---

### Step 2 — Compile the serial reader

The serial reader reads gyroscope data from the BLE over USB and forwards it as UDP packets to the Python canvas. **This must be compiled and run locally.**

Navigate to the `BLE_IMU` folder and compile:

```bash
g++ -O2 -std=c++17 -o serial_reader serial_reader.cpp
```

Find your BLE serial port by going to Tools → Port in Arduino IDE. Then run:

```bash
./serial_reader /dev/cu.usbmodem1101
```

Replace `/dev/cu.usbmodem1101` with your actual port. On Windows it will look like `COM3`.

---

### Step 3 — Compile the stroke processor

The stroke processor receives stroke data from the canvas, smooths it, and exports it as a 28x28 PGM image file. **This must be compiled locally — the executable cannot be shared across different operating systems.**

Navigate to the `src` folder and compile:

```bash
g++ -O2 -std=c++17 -o stroke_processor main.cpp StrokeRecorder.cpp StrokeFilter.cpp ImageExporter.cpp AppController.cpp PredictionManager.cpp
```

Move the compiled `stroke_processor` executable into the same folder as `canvas.py`:

```bash
mv stroke_processor ../canvas_demo/
```

---

### Step 4 — Run the canvas

The canvas must be run locally to communicate with the BLE and stroke processor. Navigate to the `canvas_demo` folder and run:

```bash
python3 canvas.py
```

A window will open. Use the BLE board to draw a digit in the air. Controls:

| Key | Action |
|-----|--------|
| SPACE | Toggle pen down / up |
| S | Save drawing as PGM file |
| C | Clear canvas |
| Q | Quit |

When you press S, the stroke processor runs automatically and saves a file called `output_0.pgm` in the same folder.

---

### Step 5 — Run the prediction

Copy the saved `output_0.pgm` file into the `ML_model` folder. Before running the prediction, open `ML_model/predict.py` and set the port for your Arduino Uno:

```python
UNO_PORT = "/dev/cu.usbmodem101"  # replace with your Uno's port
```

You can find the Uno's port in Arduino IDE under Tools → Port.

Then run:

```bash
cd ML_model
python3 predict.py output_0.pgm
```

The predicted digit and confidence score will print in the terminal. If confidence is 95% or above the green LED on the Uno lights up. Below 95% the red LED lights up.

---

## Getting the Model

The trained model `mnist_model.h5` is included in the `ML_model` folder of this repository. If you need to retrain it, run:

```bash
python3 train_model.py
```

This downloads the MNIST dataset, trains a CNN, and saves the model as `mnist_model.h5`. Note: on macOS you may need to fix SSL certificates first by running:

```bash
sudo /Applications/Python\ 3.13/Install\ Certificates.command
```

---

## Project Structure

```
/Arduino_UNO
    LED_Feedback.ino        — lights LEDs based on confidence score
/BLE_IMU
    /IMU_Reader
        IMU_Reader.ino      — reads gyroscope and streams over serial
    serial_reader.cpp       — reads serial port, forwards UDP to canvas
/canvas_demo
    canvas.py               — real time drawing canvas
    udp_test.py             — test script to verify UDP pipeline
/docs
    /diagrams               — wiring diagrams
    /screenshots            — demo screenshots
/ML_model
    predict.py              — runs prediction and sends result to Uno
    train_model.py          — trains and saves the MNIST model
    mnist_model.h5          — pretrained CNN model
/report
    final_report.pdf
/src
    main.cpp                — entry point, creates AppController
    AppController.h/.cpp    — coordinates all C++ classes
    StrokeRecorder.h/.cpp   — stores stroke points in vectors
    StrokeFilter.h/.cpp     — smooths strokes using moving average
    ImageExporter.h/.cpp    — renders strokes to 28x28 PGM file
    PredictionManager.h/.cpp — stores and categorizes prediction results
README.md
```

---

## Data Structures

- `vector<vector<Point>>` — stores all strokes and their points in StrokeRecorder
- `vector<Point>` — stores smoothed points of a single stroke in StrokeFilter
- `int grid[28][28]` — fixed 2D array storing pixel values in ImageExporter

## Algorithms

- **Moving Average** — smooths jittery stroke points by averaging neighbors, O(n × w)
- **Line Rasterization** — draws lines between points on the 28x28 grid using linear interpolation, O(p × d)
- **Grid Clearing** — resets all 784 pixels to black before each render, O(n²)

---

## Contributors

Richy Manzo — Merced College, CPSC-25: Advanced C++ Programming, Spring 2026
