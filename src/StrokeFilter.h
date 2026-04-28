/*
    * Richy Manzo
    * 2026-04-27
    * This header file defines the StrokeFilter class, which smooths the strokes drawn
    * by the user using a moving average filter.
*/

#ifndef STROKE_FILTER_H
#define STROKE_FILTER_H
#include "StrokeRecorder.h"
using namespace std;

class StrokeFilter {
public:
    // This takes a stroke and smooths it depedning on the window size.
    vector<Point> smoothStroke(vector<Point> stroke, int windowSize); 

    // This calls smoothStroke for each stroke in the vector of strokes and returns a new vector of smoothed strokes.
    vector<vector<Point>> smooothAll(vector<vector<Point>> strokes, int windowSize);
};

#endif