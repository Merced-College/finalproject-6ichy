/*
 * Richy Manzo
 * 2026-04-27
 * This header file defines the StrokeRecorder class, which saves the strokes drawn by the
 * user in a vector.
*/

#ifndef STROKE_RECORDER_H
#define STROKE_RECORDER_H
#include <vector>   // Vector is used because it is dynamic. Points can be added as the user draws. 
using namespace std;


Struct Point {  // Points in the vector are stored as x and y coordinates.
    int x;
    int y;
};

class StrokeRecorder {
public:
    void beginStroke(); // This is called when the user presses space to begin a stroke.
    void addPoint(int x, inty); // This adds the position of the cursor to the current stroke.
    void endStroke(); // This is called when the user presses space to end the stroke.
    vector<vector<Point>> getStrokes() const; // This returns the vector of strokes, and the points within each stroke.
    void clear(); // This clears all the strokes from the vector when user presses C.
private:
    vector<Point> currentStroke; // This is the vector of the current stroke.
    vector<vector<Point>> strokes; // This is a nested vector of strokes and points within each stroke.
    bool isRecording; // This indicates whether the user is currently drawing.
}

#endif