/*
    * Richy Manzo
    * 2026-04-30
    * This cpp file implements the AppController class
    * This manages the entire loop of the stroke processor
*/

#include "AppController.h"
#include <iostream>
#include <string>
using namespace std;

AppController::AppController(int canvasW, int canvasH, int windowS) {
    canvasWidth = canvasW;
    canvasHeight = canvasH;
    windowSize = windowS;
}

void AppController::run() {
    string line;

    cout << "Ready" << endl;

    // Read lines from stdin until Python signals the end
    while (getline(cin, line)) {

        // BEGIN signals start of a new stroke
        if (line == "BEGIN") {
            begin();
        }

        // END signals end of the current stroke
        else if (line == "END") {
            end();
        }

        // SAVE signals to export coordinates to a 28x28 image
        else if (line == "SAVE") {
            save();
        }

        // CLEAR signals to clear the current strokes and start fresh
        else if (line == "CLEAR") {
            clear();
        }

        // Otherwise, we assume the line is a point coordinate in the format "x,y"
        else {
            addPoint(line);
        }
    }
}

// This function tell the recroder a new stroke is starting
void AppController::begin() {
    recorder.beginStroke();
}

// This function parses a "x,y" strign and adds the point to the current stroke vector in the recorder.
void AppController::addPoint(const string& line) {
    stringstream ss(line);
    int x, y;
    char comma;

    if (ss >> x >> comma >> y && comma == ',') {
        recorder.addPoint(x, y);
    }
}

// eThis function finalizes the current stroke and saves it in the recorder's strokes vector.
void AppController::end() {
    recorder.endStroke();
}

// This function takes the raw strokes from the recorder, smooths them, renders them to a 28x28 grid, and saves the grid as a PGM image.
void AppController::save() {
    // Get raw strokes from the recorder
    vector<vector<Point>> raw = recorder.getStrokes();

    // Smooth the strokes using the filter
    vector<vector<Point>> smoothed = filter.smoothAll(raw, windowSize);

    // Render the smoothed strokes to a 28x28 grid
    exporter.render(smoothed, canvasWidth, canvasHeight);

    // Build a filename for the output image using the save count
    string filename = "output_" + to_string(saveCount++) + ".pgm";

    // Tell the Python program status of save
    if (exporter.save(filename)) {
        cout << "SAVED " << filename << endl;
    } 
    else {
        cout << "ERROR SAVING " << filename << endl;
    }
}

// This function clears the current strokes in the recorder and resets the image exporter for the next drawing.
void AppController::clear() {
    recorder.clear();
    exporter.clear();
    cout << "CLEARED" << endl;
}