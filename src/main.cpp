#include <Arduino.h>
#include "SensorIR.h"
#include "ControlServo.h"
#include "ShadowManager.h"

namespace {
SensorIR sensor(27, LOW);
ControlServo puerta(18);
ShadowManager shadow(sensor, puerta);
}

void setup() {
  Serial.begin(115200);
  sensor.iniciar();
  shadow.iniciar();
}

void loop() {
  shadow.actualizar();
}
