#include "SensorIR.h"

SensorIR::SensorIR(uint8_t pin, uint8_t nivelDeteccion)
    : pin_(pin), nivelDeteccion_(nivelDeteccion), ultimoEstado_(false) {}

void SensorIR::iniciar() {
  pinMode(pin_, INPUT);
  leer();
}

bool SensorIR::leer() {
  ultimoEstado_ = digitalRead(pin_) == nivelDeteccion_;
  return ultimoEstado_;
}

bool SensorIR::ultimoEstado() const {
  return ultimoEstado_;
}
