#include <Arduino_LSM9DS1.h>

void setup() {
  Serial.begin(115200);
  while (!Serial);
  IMU.begin();
}

void loop() {
  float x, y, z;
  if (IMU.gyroscopeAvailable()) {
    IMU.readGyroscope(x, y, z);
    Serial.print(x, 2);
    Serial.print(',');
    Serial.println(y, 2);a
  }
}