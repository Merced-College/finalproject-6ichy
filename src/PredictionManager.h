/*
    * Richy Manzo
    * 2026-04-27
    * Recieves a predicted digit and confindence from the Python canvas
    * and formats the prediction and confidence in the terminal for display.
*/

#ifndef PREDICTION_MANAGER_H
#define PREDICTION_MANAGER_H
#include <string>
using namespace std;

class PredictionManager {
public:
    // Stores prediction and confidence
    void setPrediction(int digit, float confidence);

    // returns the predicted digit
    int getDigit() const;

    // returns the confidence of the prediction
    float getConfidence() const;

    // returns a formatted string for display
    string getResult() const;

    // returns the whether the confidence is HIGH or LOW
    string getConfidenceLevel() const;

    // returns true if the confidence is above threshold
    bool isConfident() const;

private:
    int digit = 0;
    float confidence = 0.0;

    // Threshold for high confidence, can be adjusted as needed
    static const int THRESHOLD = 95;
};

#endif