#include <Arduino.h>
#include "SensorIR.h"
#include "ControlServo.h"
#include "ShadowManager.h"

namespace {
SensorIR sensor(18, LOW);
ControlServo puerta(27);
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
