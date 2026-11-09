#include "ControlServo.h"

ControlServo::ControlServo(uint8_t pin)
    : pin_(pin), posicionSolicitada_(CERRADA) {}

bool ControlServo::iniciar(int posicionInicial) {
  if (posicionInicial != CERRADA && posicionInicial != ABIERTA) {
    return false;
  }
  servo_.write(posicionInicial);
  servo_.attach(pin_);
  if (!servo_.attached()) {
    return false;
  }
  posicionSolicitada_ = posicionInicial;
  return true;
}

void ControlServo::abrir() {
  servo_.write(ABIERTA);
  posicionSolicitada_ = ABIERTA;
}

void ControlServo::cerrar() {
  servo_.write(CERRADA);
  posicionSolicitada_ = CERRADA;
}

int ControlServo::posicionSolicitada() const {
  return posicionSolicitada_;
}

bool ControlServo::estaAbierta() const {
  return posicionSolicitada_ == ABIERTA;
}
