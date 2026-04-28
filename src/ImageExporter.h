/*
    * Richy Manzo
    * 2026-04-27
    * This header file defines the imageExporter class
    * which exports the smoothed strokes as 28x28 image for neural network input.
*/

#ifndef IMAGE_EXPORTER_H
#define IMAGE_EXPORTER_H
#include <vector>
#include <string>
#include "StrokeRecorder.h"
#include "StrokeFilter.h"
using namespace std;

class ImageExporter {
public:

    // This function takes the smoothed strokes from the large canvas and renders them as a 28x28 image.
    void render (vector<vector<Point>> smoothedStrokes, int canvasWidth, int canvasHeight);

    // This fuction saves the rendered image as a PGM file
    bool save(string filename);

    // Clear the 28x28 grid for the next image.
    void clear();

private:

    // 28x28 grid is stored as a static 2D array, this will not change.
    int grid[28][28];
    void drawLine(float x0, float y0, float x1, float y1);
};

#endif