#pragma once
#include <Arduino.h>
#include <ESP32Servo.h>

class ControlServo {
public:
  explicit ControlServo(uint8_t pin);
  // Inicializa la salida solo ante una orden autorizada.
  bool iniciar(int posicionInicial);
  void abrir();
  void cerrar();
  int posicionSolicitada() const;
  bool estaAbierta() const;

private:
  static constexpr int CERRADA = 0;
  static constexpr int ABIERTA = 180;
  uint8_t pin_;
  Servo servo_;
  int posicionSolicitada_;
};
