/*
 * Richy Manzo
 * 2026-04-28
 * This is the main cpp file that runs the program.
 * It creates an AppController instance and calls its run() method to start the processing loop.
 * It will read the stroke data from the Python canvas via stdin, and
 * process the data StrokeRecorder, StrokeFilter, and ImageExporter,
 * then saves the result as a 28x28 PGM file.
 * Compile: g++ -O2 -std=c++17 -o stroke_processor main.cpp StrokeRecorder.cpp StrokeFilter.cpp ImageExporter.cpp AppController.cpp PredictionManager.cpp
 */


int main() {
    // Python canvas dimensions: 560x560, Window size for smoothing: 3
    AppController controller(560, 560, 3);
    controller.run();
    return 0;
}