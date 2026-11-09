#pragma once
#include <Arduino.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "SensorIR.h"
#include "ControlServo.h"

class ShadowManager {
public:
  ShadowManager(SensorIR& sensor, ControlServo& servo);
  void iniciar();
  void actualizar();

private:
  void conectarWifi();
  void conectarMqtt();
  void recibir(char* topic, byte* payload, unsigned int length);
  void solicitarShadow();
  void procesarOrden(const char* orden, uint32_t version);
  void publicarEstado();
  void registrarDesconexionMqtt(const char* motivo);
  SensorIR& sensor_;
  ControlServo& servo_;
  WiFiClientSecure tls_;
  PubSubClient mqtt_;
  String base_;
  bool listo_ = false;
  bool sincronizado_ = false;
  bool servoIniciado_ = false;
  bool posicionConocida_ = false;
  bool ultimoSensor_ = false;
  bool pendienteReporte_ = true;
  bool relojSolicitado_ = false;
  bool reporteEnCurso_ = false;
  bool deltaDuranteGet_ = false;
  bool hayVersion_ = false;
  bool mqttActiva_ = false;
  bool getPendiente_ = false;
  int ultimoEstadoWifi_ = -1;
  char tokenReporte_[40] = {};
  uint32_t secuenciaReporte_ = 0;
  uint32_t version_ = 0;
  unsigned long ultimoWifi_ = 0;
  unsigned long ultimoMqtt_ = 0;
  unsigned long ultimaLectura_ = 0;
  unsigned long ultimoReporte_ = 0;
  unsigned long ultimoGet_ = 0;
  unsigned long inicioReporte_ = 0;
};
