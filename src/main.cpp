/*
 * Richy Manzo
 * 2026-04-28
 * This is the main cpp file that runs the program.
 * It will read the stroke data from the Python canvas via stdin, and
 * process the data StrokeRecorder, StrokeFilter, and ImageExporter,
 * then saves the result as a 28x28 PGM file.
 */

#include <iostream>
#include <string>
#include <sstream>
#include "StrokeRecorder.h"
#include "StrokeFilter.h"
#include "imageExporter.h"
using namespace std;

// Set the Python canvas dimentions
const int CANVAS_WIDTH = 560;
const int CANVAS_HEIGHT = 560;

// smoothing window size, this can be adjusted to make the strokes smoother or less smooth.
const int WINDOW_SIZE = 3;

// counter for the number of saved images, for naming the output files.
int saveCount = 0;

int main() {

    // Create instances of the StrokeRecorder, StrokeFilter, and ImageExporter classes.
    StrokeRecorder recorder;
    StrokeFilter filter;
    ImageExporter exporter;

    // line holds each line of input from stdin ("BEGIN", "END", or "x,y")
    string line;

    cout << "Ready" << endl;

    // Read lines from stdin until Python signals the end
    while (getline(cin, line)) {

        // BEGIN signals start of a new stroke
        if (line == "BEGIN") {
            recorder.beginStroke();
        }

        // END signals end of the current stroke
        else if (line == "END") {
            recorder.endStroke();
        }

        // SAVE signals to export coordinates to a 28x28 image
        else if (line == "SAVE") {

            // Get raw strokes from the recorder
            vector<vector<Point>> raw = recorder.getStrokes();

            // Smooth the strokes using the filter
            vector<vector<Point>> smoothed = filter.smoothAll(raw, WINDOW_SIZE);

            // Render the smoothed strokes to a 28x28 grid
            exporter.render(smoothed, CANVAS_WIDTH, CANVAS_HEIGHT);

            // Build a filename for the output image using the save count
            string filename = "output_" + to_string(saveCount) + ".pgm";

            // Tell the Python program status of save
            if (exporter.save(filename)) {
                cout << "SAVED" << filename << endl;
            } 
            else {
                cout << "ERROR SAVING" << filename << endl;
            }
        }
        
        // CLEAR signals to clear all stroke
        else if (line == "CLEAR") {
            recorder.clear();
            exporter.clear();
            cout << "CLEARED" << endl;
        }

        // Anything else is a point in x,y format
        else {
            // Parse the line to extract x and y coordinates and add the point to the recorder
            stringstream ss(line);
            int x, y;
            char comma; // to consume the comma between x and y
            if (ss >> x >> comma >> y && comma == ',') {
                recorder.addPoint(x, y);
            }
        }
    }

    return 0;
}