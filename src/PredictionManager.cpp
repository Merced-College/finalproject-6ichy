/*
 * Richy Manzo
 * 2026-04-27
 * This cpp file implements the PredictionManager class
 */

#include "PredictionManager.h"

// Store the predicted digit and confidence from latest ML prediction
void PredictionManager::setPrediction(int d, float c) {
    digit = d
    confidence = c;
}

// returns the predicted digit
int PredictionManager::getDigit() const {
    return digit;
}

// returns the confidence of the prediction
float PredictionManager::getConfidence() const {
    return confidence;
}

// formats the prediction and confidence for display
string PredictionManager::getResult() const {
    return "Predicted: " + to_string(digit) + "  Confidence: " + to_string(confidence) + "%";
}

// returns whether the confidence is HIGH or LOW based on the threshold
string PredictionManager::getConfidenceLevel() const {
    if (confidence >= THRESHOLD) {
        return "HIGH";
    } else {
        return "LOW";
    }
}

// returns true if the confidence is above the threshold
bool PredictionManager::isConfident() const {
    return confidence >= THRESHOLD;
}
