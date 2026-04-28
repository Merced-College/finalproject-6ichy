/*
 * Richy Manzo
 * 2026-04-27
 * This cpp file implements the StrokeRecorder class
 */

#include "StrokeRecorder.h"

void StrokeRecorder::beginStroke() { // This is called when the user presses space to begin a stroke.
    currentStroke.clear(); // Clear the current stroke vector to start fresh.
    recording = true; // Set the recording flag to true.
}

void StrokeRecorder::addPoint(int x, int y) {
    if (recording) {
        Point p; // Create a Point struct with the given x and y coordinates.
        p.x = x;
        p.y = y;
        currentStroke.push_back(p); // Add the point to the current stroke vector.
    }
}

void StrokeRecorder::endStroke() {
    if (recording && !currentStroke.empty()) {
        strokes.push_back(currentStroke); // Add the current stroke to the strokes vector.
        currentStroke.clear(); // Clear the current stroke vector for the next stroke.
        recording = false; // Set the recording flag to false.
    }
}

vector<vector<Point>> StrokeRecorder::getStrokes() const {
    return strokes; // Return the vector of strokes and points.
}

void StrokeRecorder::clear() {
    strokes.clear(); // Clear all strokes and points from the vector.
    currentStroke.clear(); // Clear the current stroke vector.
    recording = false; // Set the recording flag to false.
}