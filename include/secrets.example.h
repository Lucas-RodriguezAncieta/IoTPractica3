#pragma once

// Copiar a secrets.h e insertar los PEM reales localmente; no publicar.
// Las cadenas vacias impiden la conexion hasta completar la configuracion.
constexpr char AWS_ROOT_CA[] = R"PEM()PEM";
constexpr char AWS_DEVICE_CERT[] = R"PEM()PEM";
constexpr char AWS_PRIVATE_KEY[] = R"PEM()PEM";
