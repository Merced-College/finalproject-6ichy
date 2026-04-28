/*
 * Author: Richy Manzo
 *
 * Algorithm: Moving Average
 *
 * Description:
 * Smooths a stroke by replacing each point with the average
 * of its neighboring points within a window.
 *
 * How it works:
 * For each point at index i, we look at the points around it
 * within the window size. We add up all their x values and all
 * their y values, then divide by how many points we looked at.
 * The result is a new point that represents the average position
 * of that neighborhood, which removes small jittery movements.
 *
 * Example with windowSize 3:
 * point[2] = average of point[1], point[2], point[3]
 *
 * Time Complexity: O(n * w)
 * n = number of points in the stroke
 * w = window size
 * For small window sizes this is effectively O(n)
 */

#include "StrokeFilter.h"

vector<Point> StrokeFilter::smoothStroke(vector<Point> stroke, int windowSize) {

    // Force windowSize to be odd so half works correctly (seen later)
    if (windowSize % 2 == 0) {
        windowSize++;
    }
    // Return the original stroke if it's too small to smooth.
    if (stroke.size() < windowSize) {
        return stroke; 
    }

    // Create a ne vector to store smoothed points.
    vector<Point> smoothed;

    // Loop through each point in the stroke.
    for (int i = 0; i < stroke.size(); i++) {

        // Initialize sums for x and y coordinates, and count of points in the window.
        int sumX = 0;
        int sumY = 0;
        int count = 0;

        // Divide window size by 2 to get number of points to look on either side.
        int half = windowSize / 2;
        
        // Loop through the window around the current point.
        for (int j = i - half; j <= i + half; j++) {

            // Check if the index j is within the bounds of the stroke.
            if (j >= 0 && j < stroke.size()) {
                sumX += stroke[j].x; // Add the x coordinate to the sum.
                sumY += stroke[j].y; // Add the y coordinate to the sum.
                count++; // Increment the count of points in the window.
            }
        }

        // Create a new point with the average x and y values.
        Point smoothedPoint;
        smoothedPoint.x = sumX / count; // Average x coordinate.
        smoothedPoint.y = sumY / count; // Average y coordinate.

        // Add the smoothed point to the smoothed stroke vector.
        smoothedStroke.push_back(smoothedPoint);
    }
    return smoothed; // Return the new vector of smoothed points.
}

// This calls smoothStroke for each stroke in the vector of strokes.
vector<vector<Point>> StrokeFilter::smoothAll(vector<vector<Point>> strokes, int windowSize) {
    vector<vector<Point>> smoothedStrokes; // Create a new vector to store smoothed strokes.

    // Loop through each stroke in the vector of strokes.
    for (int i = 0; i < strokes.size(); i++) {

        // Smooth the current stroke and add it to the smoothed strokes vector.
        smoothedStrokes.push_back(smoothStroke(strokes[i], windowSize));
    }

    // Return the new vector of smoothed strokes.
    return smoothedStrokes;
}