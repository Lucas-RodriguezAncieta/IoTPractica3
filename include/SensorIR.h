#pragma once
#include <Arduino.h>

class SensorIR {
public:
  SensorIR(uint8_t pin, uint8_t nivelDeteccion);
  void iniciar();
  bool leer();
  bool ultimoEstado() const;

private:
  uint8_t pin_;
  uint8_t nivelDeteccion_;
  bool ultimoEstado_;
};
