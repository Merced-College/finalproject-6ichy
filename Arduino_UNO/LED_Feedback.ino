/*
 * LED_Feedback.ino
 * -----------------
 * Reads a confidence score from serial sent by predict.py.
 * Lights green LED if confidence is 95 or above.
 * Lights red LED if confidence is below 95.
 *
 * Wiring:
 *   Pin 12 → green LED → 220 ohm resistor → GND
 *   Pin 13 → red LED   → 220 ohm resistor → GND
 *
 * Serial protocol:
 *   Receives a single float as a string e.g. "94.5\n"
 *   Parses it and lights the appropriate LED.
 */

#define GREEN_PIN 12
#define RED_PIN   13

void setup() {
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(RED_PIN,   OUTPUT);

  // start with both LEDs off
  digitalWrite(GREEN_PIN, LOW);
  digitalWrite(RED_PIN,   LOW);

  Serial.begin(9600);
}

void loop() {
  // wait for a line of text from Python
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    // parse the confidence value
    float confidence = input.toFloat();

    // turn both off first
    digitalWrite(GREEN_PIN, LOW);
    digitalWrite(RED_PIN,   LOW);

    // light the correct LED
    if (confidence >= 95.0) {
      digitalWrite(GREEN_PIN, HIGH);
    } else {
      digitalWrite(RED_PIN, HIGH);
    }

    // send confirmation back so predict.py knows it was received
    Serial.print("LED set for confidence: ");
    Serial.println(confidence);
  }
}
