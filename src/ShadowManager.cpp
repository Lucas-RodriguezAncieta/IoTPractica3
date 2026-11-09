#include "ShadowManager.h"
#include "config.h"
#include "secrets.h"
#include <WiFi.h>
#include <ArduinoJson.h>
#include <time.h>

namespace {
constexpr unsigned long REINTENTO = 10000;
constexpr unsigned long LECTURA = 200;
constexpr unsigned long REPORTE = 30000;
constexpr unsigned long MIN_REPORTE = 1000;
constexpr unsigned long ESPERA_CONFIRMACION = 15000;
constexpr size_t MAX_JSON = 6144;
}

ShadowManager::ShadowManager(SensorIR& sensor, ControlServo& servo)
    : sensor_(sensor), servo_(servo), mqtt_(tls_) {}

void ShadowManager::iniciar() {
  base_ = String("$aws/things/") + THING_NAME + "/shadow/";
  if (!WIFI_SSID[0] || !AWS_ENDPOINT[0] || !THING_NAME[0] ||
      !AWS_ROOT_CA[0] || !AWS_DEVICE_CERT[0] || !AWS_PRIVATE_KEY[0]) {
    Serial.println("Configuracion local incompleta; conexion deshabilitada.");
    return;
  }
  tls_.setCACert(AWS_ROOT_CA);
  tls_.setCertificate(AWS_DEVICE_CERT);
  tls_.setPrivateKey(AWS_PRIVATE_KEY);
  mqtt_.setServer(AWS_ENDPOINT, AWS_PORT);
  mqtt_.setSocketTimeout(15);
  mqtt_.setKeepAlive(30);
  if (!mqtt_.setBufferSize(MAX_JSON + 512)) {
    Serial.println("No se pudo reservar buffer MQTT.");
    return;
  }
  mqtt_.setCallback([this](char* t, byte* p, unsigned int n) { recibir(t, p, n); });
  WiFi.mode(WIFI_STA);
  ultimoSensor_ = sensor_.ultimoEstado();
  listo_ = true;
  ultimoWifi_ = millis() - REINTENTO;
  Serial.println(ENABLE_DOOR_MOVEMENT ? "Movimiento habilitado: solo pruebas seguras."
                                     : "Movimiento deshabilitado por configuracion.");
}

void ShadowManager::conectarWifi() {
  if (millis() - ultimoWifi_ < REINTENTO) return;
  ultimoWifi_ = millis();
  Serial.printf("[%lu ms] Intentando conexion WiFi.\n", millis());
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void ShadowManager::conectarMqtt() {
  if (millis() - ultimoMqtt_ < REINTENTO) return;
  ultimoMqtt_ = millis();
  Serial.printf("[%lu ms] Intentando conexion MQTT TLS (WiFi=%d, RSSI=%d dBm).\n",
                millis(), static_cast<int>(WiFi.status()), WiFi.RSSI());
  bool conectado = mqtt_.connect(THING_NAME);
  ultimoMqtt_ = millis();
  if (!conectado) {
    Serial.printf("[%lu ms] Error MQTT: %d (WiFi=%d).\n", millis(), mqtt_.state(),
                  static_cast<int>(WiFi.status()));
    return;
  }
  mqttActiva_ = true;
  Serial.printf("[%lu ms] MQTT conectado (estado=%d, WiFi=%d, RSSI=%d dBm).\n",
                millis(), mqtt_.state(), static_cast<int>(WiFi.status()), WiFi.RSSI());
  const char* filtros[] = {"get/accepted", "get/rejected", "update/delta", "update/accepted", "update/rejected"};
  for (const char* filtro : filtros) {
    String topic = base_ + filtro;
    if (!mqtt_.subscribe(topic.c_str(), 1)) {
      Serial.println("Error al enviar suscripcion; se reintentara.");
      registrarDesconexionMqtt("fallo al enviar suscripcion");
      mqtt_.disconnect();
      return;
    }
    Serial.print("Suscripcion solicitada: ");
    Serial.println(topic);
  }
  sincronizado_ = false;
  pendienteReporte_ = true;
  reporteEnCurso_ = false;
  deltaDuranteGet_ = false;
  getPendiente_ = false;
  solicitarShadow();
}

void ShadowManager::registrarDesconexionMqtt(const char* motivo) {
  if (!mqttActiva_) return;
  int estadoWifi = static_cast<int>(WiFi.status());
  Serial.printf("[%lu ms] MQTT desconectado: %s; estado MQTT=%d, WiFi=%d",
                millis(), motivo, mqtt_.state(), estadoWifi);
  if (estadoWifi == WL_CONNECTED) Serial.printf(", RSSI=%d dBm", WiFi.RSSI());
  Serial.println();
  mqttActiva_ = false;
}

void ShadowManager::solicitarShadow() {
  ultimoGet_ = millis();
  Serial.println(mqtt_.publish((base_ + "get").c_str(), "{}") ?
                 "Consulta Shadow enviada." : "Error al enviar consulta Shadow.");
}

void ShadowManager::procesarOrden(const char* orden, uint32_t version) {
  if (!orden || (strcmp(orden, "open") && strcmp(orden, "closed"))) {
    Serial.println("Orden Shadow invalida; ignorada.");
    return;
  }
  if (version < version_) return;
  version_ = version;
  Serial.printf("Orden Shadow solicitada: %s\n", orden);
  if (!ENABLE_DOOR_MOVEMENT) {
    Serial.println("Orden pendiente: movimiento deshabilitado.");
    return;
  }
  const int angulo = strcmp(orden, "open") == 0 ? 180 : 0;
  if (posicionConocida_ && servo_.posicionSolicitada() == angulo) return;
  if (!servoIniciado_) {
    servoIniciado_ = servo_.iniciar(angulo);
    if (!servoIniciado_) {
      Serial.println("No se pudo iniciar servo.");
      return;
    }
  } else if (angulo == 180) {
    servo_.abrir();
  } else {
    servo_.cerrar();
  }
  posicionConocida_ = true;
  pendienteReporte_ = true;
}

void ShadowManager::recibir(char* topic, byte* payload, unsigned int length) {
  if (length > MAX_JSON) { Serial.println("Mensaje Shadow demasiado grande."); return; }
  static StaticJsonDocument<8192> doc;
  DeserializationError error = deserializeJson(doc, payload, length, DeserializationOption::NestingLimit(8));
  if (error) { Serial.println("JSON Shadow invalido o excede memoria."); return; }
  String nombre(topic);
  if (nombre == base_ + "get/rejected") {
    Serial.printf("GET Shadow rechazado: %d\n", doc["code"] | 0);
    if ((doc["code"] | 0) == 404) { sincronizado_ = true; pendienteReporte_ = true; }
    return;
  }
  if (nombre == base_ + "update/rejected") {
    Serial.printf("Update Shadow rechazado: %d\n", doc["code"] | 0);
    const char* token = doc["clientToken"] | "";
    if (reporteEnCurso_ && strcmp(token, tokenReporte_) == 0) {
      reporteEnCurso_ = false;
      pendienteReporte_ = true;
    }
    return;
  }
  if (nombre == base_ + "update/accepted") {
    const char* token = doc["clientToken"] | "";
    if (reporteEnCurso_ && strcmp(token, tokenReporte_) == 0) {
      reporteEnCurso_ = false;
      Serial.println("Reporte propio aceptado por Shadow.");
    } else {
      Serial.println("Shadow acepto otra actualizacion.");
    }
    return;
  }
  bool esGet = nombre == base_ + "get/accepted";
  bool esDelta = nombre == base_ + "update/delta";
  if (!esGet && !esDelta) return;
  if (!doc["version"].is<uint32_t>()) { Serial.println("Shadow sin version valida."); return; }
  uint32_t version = doc["version"].as<uint32_t>();
  if (hayVersion_ && version < version_) return;
  if (esDelta && !sincronizado_) {
    deltaDuranteGet_ = true;
    Serial.println("Delta durante sincronizacion; se solicitara otro GET.");
    return;
  }
  if (esGet && deltaDuranteGet_) {
    deltaDuranteGet_ = false;
    Serial.println("GET potencialmente anterior a delta; se solicitara estado actual.");
    getPendiente_ = true;
    return;
  }
  if (esGet) { sincronizado_ = true; pendienteReporte_ = true; Serial.println("Shadow sincronizado."); }
  else Serial.println("Delta recibido.");
  hayVersion_ = true;
  JsonVariantConst orden;
  if (esGet) {
    orden = doc["state"]["desired"]["door"].as<JsonVariantConst>();
  } else {
    orden = doc["state"]["door"].as<JsonVariantConst>();
  }
  if (!orden.isNull()) {
    if (!orden.is<const char*>()) { Serial.println("Tipo de orden invalido."); return; }
    procesarOrden(orden.as<const char*>(), version);
  } else {
    version_ = version;
  }
}

void ShadowManager::publicarEstado() {
  StaticJsonDocument<256> doc;
  JsonObject reported = doc["state"].createNestedObject("reported");
  reported["objectDetected"] = ultimoSensor_;
  if (posicionConocida_) {
    reported["door"] = servo_.estaAbierta() ? "open" : "closed";
    reported["servoAngle"] = servo_.posicionSolicitada();
  }
  snprintf(tokenReporte_, sizeof(tokenReporte_), "esp32-%lu-%lu", static_cast<unsigned long>(millis()),
           static_cast<unsigned long>(++secuenciaReporte_));
  doc["clientToken"] = tokenReporte_;
  char salida[256];
  size_t n = serializeJson(doc, salida, sizeof(salida));
  if (!n || n >= sizeof(salida)) { Serial.println("Error al serializar estado."); return; }
  ultimoReporte_ = millis();
  // Seleccionar explicitamente la sobrecarga de bytes: n no es la bandera retained.
  if (mqtt_.publish((base_ + "update").c_str(),
                    reinterpret_cast<const uint8_t*>(salida), n, false)) {
    pendienteReporte_ = false;
    reporteEnCurso_ = true;
    inicioReporte_ = millis();
    Serial.printf("Reporte enviado: objeto=%s", ultimoSensor_ ? "detectado" : "no detectado");
    if (posicionConocida_) Serial.printf(", puerta=%s, angulo=%d", servo_.estaAbierta() ? "open" : "closed", servo_.posicionSolicitada());
    Serial.println("; posicion fisica no confirmada.");
  } else {
    pendienteReporte_ = true;
    Serial.printf("Error al enviar reporte MQTT (estado %d, %u bytes).\n",
                  mqtt_.state(), static_cast<unsigned int>(n));
  }
}

void ShadowManager::actualizar() {
  if (!listo_) return;
  unsigned long ahora = millis();
  int estadoWifi = static_cast<int>(WiFi.status());
  if (estadoWifi != ultimoEstadoWifi_) {
    Serial.printf("[%lu ms] Estado WiFi: %d", ahora, estadoWifi);
    if (estadoWifi == WL_CONNECTED) Serial.printf(", RSSI=%d dBm", WiFi.RSSI());
    Serial.println();
    ultimoEstadoWifi_ = estadoWifi;
  }
  if (ahora - ultimaLectura_ >= LECTURA) {
    ultimaLectura_ = ahora;
    bool valor = sensor_.leer();
    if (valor != ultimoSensor_) { ultimoSensor_ = valor; pendienteReporte_ = true; }
  }
  if (estadoWifi != WL_CONNECTED) {
    registrarDesconexionMqtt("WiFi no conectado");
    if (mqtt_.connected()) mqtt_.disconnect();
    sincronizado_ = false;
    if (reporteEnCurso_) pendienteReporte_ = true;
    reporteEnCurso_ = false;
    relojSolicitado_ = false;
    conectarWifi();
    return;
  }
  if (!relojSolicitado_) {
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    relojSolicitado_ = true;
    Serial.println("WiFi conectado; solicitando hora para validar TLS.");
  }
  if (time(nullptr) < 1700000000) return;
  if (!mqtt_.connected()) {
    registrarDesconexionMqtt("conexion de red perdida");
    sincronizado_ = false;
    if (reporteEnCurso_) pendienteReporte_ = true;
    reporteEnCurso_ = false;
    conectarMqtt();
    return;
  }
  if (!mqtt_.loop()) {
    registrarDesconexionMqtt("mqtt.loop interrumpido");
    sincronizado_ = false;
    pendienteReporte_ = true;
    reporteEnCurso_ = false;
    return;
  }
  ahora = millis();
  if (getPendiente_) {
    getPendiente_ = false;
    solicitarShadow();
    ahora = millis();
  }
  if (reporteEnCurso_ && ahora - inicioReporte_ >= ESPERA_CONFIRMACION) {
    Serial.println("Sin confirmacion del reporte; se reintentara.");
    reporteEnCurso_ = false;
    pendienteReporte_ = true;
  }
  if (!sincronizado_ && ahora - ultimoGet_ >= REINTENTO) solicitarShadow();
  if (sincronizado_ && !reporteEnCurso_ && ((pendienteReporte_ && ahora - ultimoReporte_ >= MIN_REPORTE) ||
                         ahora - ultimoReporte_ >= REPORTE)) publicarEstado();
}
