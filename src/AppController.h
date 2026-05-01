/*
    * Richy Manzo
    * 2026-04-30
    * This header file defines the AppController class
    * This manages the entire loop of the stroke processor
*/

#ifndef APP_CONTROLLER_H
#define APP_CONTROLLER_H
#include <string>
#include "StrokeRecorder.h"
#include "StrokeFilter.h"
#include "ImageExporter.h"
using namespace std;

class AppController {
public:
    // Constructor to initialize the AppController with default values for canvas dimensions and smoothing window size.
    AppController(int canvasW, int canvasH, int windowS);
    
    // This function runs the main loop of the stroke processo
    void run();

private:
    // Instantiate the StrokeRecorder, StrokeFilter, and ImageExporter classes
    StrokeRecorder recorder;
    StrokeFilter filter;
    ImageExporter exporter;

    // Parameters for canvas dimension and smoothing window size to be adjusted as needed.
    int canvasWidth = 560;
    int canvasHeight = 560;
    int windowSize = 3;

    // counter for the number of saved images, for naming the output files.
    int saveCount = 0;

    void begin();
    void end();
    void save();
    void clear();

    // uses const ref because we dont need to modify the input line.
    void addPoint(const string& line);
};

#endif