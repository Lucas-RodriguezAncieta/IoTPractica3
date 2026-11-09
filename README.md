# Práctica 3: Puerta Inteligente para Mascotas con Alexa y AWS IoT Core

Proyecto académico para desarrollar una puerta para mascotas con ESP32, un sensor infrarrojo de presencia y un servomotor. La skill de Alexa en español consultará el estado y enviará comandos a través de AWS Lambda y Device Shadow; DynamoDB guardará las vinculaciones entre usuarios y dispositivos.

El sensor detecta objetos dentro de su alcance, sin identificar mascotas. El diseño definitivo prevé abrir a 180° y cerrar a 0° mediante Alexa, sin automatismos entre el sensor y el servo. El firmware de Fase 4 implementa MQTT sobre TLS y Shadow; queda pendiente su validación. Lambda resolverá el dispositivo vinculado a cada usuario, sin un Thing fijo. El Thing inicial es `puerta-mascotas-01`.

El sensor no garantiza que el paso esté libre y su ausencia de detección no hace seguro cerrar. Se propone un mecanismo ligero y de baja tensión que no ejerza fuerza peligrosa sobre una mascota; su seguridad física permanece pendiente de diseño y verificación. No usar el prototipo con animales. El servo no se adjunta al arrancar y el movimiento está deshabilitado por defecto; habilitarlo puede ejecutar una orden antigua pendiente al conectar o reconectar.

La alimentación prevista es únicamente por USB al ESP32 DOIT DevKit V1. El sensor IR se conecta con OUT a GPIO 27, VCC a 3.3 V y GND a GND; el servo, con señal a GPIO 18, VCC a 5V/VIN y GND a tierra común. Debe confirmarse la compatibilidad de los componentes y la disponibilidad de 5 V en el pin de la placa. El consumo del servo podría causar caídas de tensión o reinicios: la estabilidad de esta configuración de una sola fuente queda pendiente de validación experimental, con el mecanismo desacoplado y sin mascotas. El diagrama está en el [informe](docs/informe.md#diagrama-de-circuito).

## Configuración local de Fase 4

1. Copiar `include/config.example.h` a `include/config.h`, excluido por Git. Completar localmente SSID, contraseña y endpoint ATS completo sin protocolo; mantener puerto 8883 y el Thing configurado.
2. Copiar `include/secrets.example.h` a `include/secrets.h`, también excluido por Git. Pegar en sus tres cadenas multilínea, por separado, los PEM completos de la CA raíz apropiada para ATS, el certificado del dispositivo y la clave privada, con sus encabezados, pies y saltos de línea originales. La clave puede tener otro encabezado PEM válido. Las cadenas vacías de la plantilla no son certificados. No compartir ni subir los archivos locales y comprobar antes de publicar que no estén rastreados; no añadir claves IAM.
3. Mantener `ENABLE_DOOR_MOVEMENT = false` para iniciar sin mover el servo. Solo para pruebas manuales con la puerta desacoplada y lejos de animales, cambiarlo explícitamente a `true` en el archivo local. El Shadow contiene una orden de cierre persistida: puede ejecutarse al iniciar o reconectar. No existe garantía de seguridad antiatrapamiento.
4. El monitor serial a 115200 muestra conexión, suscripciones solicitadas, consulta y respuestas del Shadow, órdenes, reportes y errores, sin imprimir credenciales. Requiere acceso de red a NTP para validar certificados TLS. No hay comandos seriales de movimiento.

Para la comprobación manual posterior, observar los diagnósticos y el Shadow clásico en la consola AWS: `reported.objectDetected` debe proceder de lecturas físicas; `door` y `servoAngle` solo aparecen después de una orden aplicada con movimiento habilitado. Cambiar `desired.door` entre `open` y `closed` únicamente con el mecanismo desacoplado, y comprobar también una desconexión y reconexión. La aceptación de un reporte no demuestra movimiento ni ángulo físico. No se han ejecutado estas verificaciones.

## Diagnóstico manual previsto con MQTT.fx

MQTT.fx es una aplicación externa, no una dependencia de PlatformIO. Para crear un perfil MQTT de conexión directa en la aplicación:

1. Introducir como broker el endpoint ATS completo de la cuenta, sin protocolo ni ruta, en la región `us-east-2`, y puerto `8883`. Elegir un client ID único, por ejemplo `puerta-mascotas-diagnostico`, distinto de `puerta-mascotas-01`; una conexión con el mismo ID desplazaría a la otra.
2. Activar SSL/TLS, usar TLS 1.2 y mantener habilitadas la validación de la CA y del nombre del servidor. En los campos de certificados del perfil seleccionar los archivos PEM locales de la CA raíz apropiada, el certificado X.509 del cliente y su clave privada. Los nombres exactos de las opciones pueden variar con la versión. No usar usuario y contraseña MQTT como sustituto de los certificados.
3. La política asociada a la identidad de diagnóstico debe permitir `iot:Connect` para ese client ID y `iot:Publish`, `iot:Subscribe` e `iot:Receive` para los tópicos correspondientes. La [política de ejemplo](aws/iot-policy.example.json) autoriza solo el client ID del ESP32 y no permite conectar MQTT.fx con otro ID; además, no concede por sí sola todos los permisos de diagnóstico descritos abajo. Los permisos reales de `PuertaMascotasIoTPolicy` no se han confirmado en detalle. Si faltan permisos, su ajuste debe realizarse manualmente en AWS por el usuario. En producción utilizar un certificado y una política independientes y limitados para diagnóstico; compartir el certificado del ESP32 es únicamente una posibilidad académica y no evita la necesidad de autorizar el client ID diferente.

MQTT.fx usa los archivos PEM locales; PlatformIO incorpora sus contenidos desde `secrets.h`. Conservar ambos fuera del repositorio. Referencias: [seguridad TLS de MQTT.fx](https://mqttfx-manual.softblade.net/tls-and-security.html) y [acciones de políticas de AWS IoT](https://docs.aws.amazon.com/iot/latest/developerguide/iot-policy-actions.html).

### Procedimiento pendiente de ejecución

Mantener `ENABLE_DOOR_MOVEMENT = false` y el mecanismo desacoplado para la primera comprobación de conectividad. Suscribirse en MQTT.fx a estos tópicos exactos antes de publicar:

```text
$aws/things/puerta-mascotas-01/shadow/get/accepted
$aws/things/puerta-mascotas-01/shadow/get/rejected
$aws/things/puerta-mascotas-01/shadow/update/accepted
$aws/things/puerta-mascotas-01/shadow/update/rejected
$aws/things/puerta-mascotas-01/shadow/update/delta
```

Publicar `{}` en `$aws/things/puerta-mascotas-01/shadow/get` y observar `get/accepted` o `get/rejected`. Con el mecanismo desacoplado, se puede publicar una orden en `$aws/things/puerta-mascotas-01/shadow/update`:

```json
{"state":{"desired":{"door":"open"}}}
```

Para cierre usar `"closed"`. Observar `update/accepted` o `update/rejected` y, si hay diferencia con `reported`, `update/delta`. Consultar de nuevo `get` para revisar `reported.objectDetected` y, cuando se haya habilitado y aplicado una orden, `reported.door` y `reported.servoAngle`. `desired` es la solicitud, `delta` la diferencia y `reported` la información publicada por el ESP32. El movimiento deshabilitado deja la orden pendiente y puede ejecutarse después si se habilita. La aceptación de AWS solo confirma que se aceptó la actualización; incluso `reported` expresa una orden de software y no confirma la posición física.

La referencia principal obligatoria es [Práctica_3.md](Práctica_3.md), que contiene RF1–RF9, restricciones, entregables y rúbrica. El actuador debe operar a baja tensión (≤ 12 V DC). La integración MQTT está implementada y pendiente de validación; Lambda y Alexa siguen pendientes.

## Tecnologías y estructura

- PlatformIO, framework Arduino y ESP32: `platformio.ini`, `src/`, `include/` y `lib/`.
- AWS Lambda: `lambda/`; skill de Alexa: `alexa/`; configuración de AWS IoT Core y DynamoDB: `aws/`.
- Informe técnico: `docs/informe.md`; evidencias futuras: `evidencias/`.

La configuración de trabajo utiliza la placa `esp32doit-devkit-v1`, la plataforma `espressif32@7.0.1`, el framework Arduino y un monitor serie a 115200 baudios. Proviene de proyectos anteriores y su compatibilidad con la placa física se verificará posteriormente.

`include/config.example.h` e `include/secrets.example.h` son plantillas sin secretos. Los archivos locales `include/config.h` e `include/secrets.h`, los certificados y las claves privadas están excluidos por `.gitignore`. Nunca incluir claves de acceso AWS en el firmware ni en Lambda.

## Fases previstas

Esta división es una planificación general; el estado real y las validaciones pendientes se describen en el informe.

1. Preparación de la estructura del proyecto.
2. Diseño del caso de uso, arquitectura, Shadow y vinculación.
3. Desarrollo del objeto inteligente y sus componentes físicos.
4. Configuración de AWS IoT Core y sincronización del Shadow.
5. Persistencia de vinculaciones con DynamoDB.
6. Desarrollo del backend Lambda para usuarios y dispositivos.
7. Modelo de interacción y configuración de la skill de Alexa.
8. Validación integral de requisitos funcionales y no funcionales.
9. Informe, evidencias y preparación de la demostración y defensa.

El orden y el alcance detallado de las fases posteriores se concretarán antes de implementarlas.
