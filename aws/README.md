# Preparación manual de AWS IoT Core

El usuario confirmó que configuró manualmente los recursos indicados abajo. Las instrucciones se conservan como referencia para futuras configuraciones; las opciones de la consola pueden variar. No introducir secretos en el repositorio.

## Datos previstos

- Región confirmada: `us-east-2` (Ohio). Thing confirmado y client ID MQTT propuesto: `puerta-mascotas-01`.
- Shadow clásico confirmado, con `desired.door = closed` y sin estado reportado por el ESP32.
- Certificado X.509 generado, descargado, activo y asociado al Thing; política académica amplia `PuertaMascotasIoTPolicy` asociada al certificado.
- Endpoint ATS localizado con sufijo `-ats.iot.us-east-2.amazonaws.com`; puerto MQTT sobre TLS previsto `8883`. La conexión aún no se ha realizado.
- La solución futura debe soportar otros Things y usuarios; la plantilla de política se restringe a este dispositivo y no es la política académica real.

## Referencia: pasos en la consola

1. Inicia sesión en [AWS IoT Core](https://console.aws.amazon.com/iot/) y selecciona la región confirmada `us-east-2` en el selector superior. Confirma que la cuenta sea la deseada.
2. Para una futura política de mínimo privilegio, abre [iot-policy.example.json](iot-policy.example.json) y reemplaza `<REGION>` y `<ACCOUNT_ID>` antes de usarla en **Security → Policies**. Conserva los símbolos `$aws` literalmente. La política académica actualmente asociada es `PuertaMascotasIoTPolicy`, de permisos amplios; su contenido exacto no fue proporcionado y no se debe confundir con la plantilla.
3. En **Administrar / Manage → All devices → Things**, elige crear un Thing individual e introduce exactamente `puerta-mascotas-01`. Continúa con la creación automática de un certificado X.509. Según el asistente, selecciona la política creada para asociarla y finaliza la creación; el asistente puede adjuntar automáticamente el certificado al Thing.
4. En la pantalla de descarga, guarda el **certificado del dispositivo** y su **clave privada** en una ubicación privada fuera del repositorio. Descarga también la CA raíz apropiada para el endpoint ATS; Amazon Root CA 1 es la opción habitual para la cadena RSA del ejemplo de AWS. La cadena depende del endpoint y del conjunto de cifrado negociado, por lo que debe confirmarse en la futura configuración TLS. Descarga la clave privada antes de cerrar la pantalla: no se puede recuperar después desde AWS. Si se pierde, crea y asocia otro certificado y retira el anterior cuando corresponda.
5. En **Security → Certificates**, revisa el estado y las asociaciones del certificado. El usuario confirmó que está activo, asociado al Thing y a `PuertaMascotasIoTPolicy`; estas comprobaciones administrativas no demuestran conectividad.
6. En **Settings → Device data endpoint**, copia el endpoint de datos ATS de la cuenta y región. Es un nombre de host propio de la cuenta: no incluyas `https://` ni una ruta. Confirma que el endpoint corresponda a `iot:Data-ATS`.
7. En **Manage → All devices → Things → puerta-mascotas-01 → Shadows → Classic Shadow** se configuró `desired.door = closed`. Es una orden pendiente que podrá mover el servo al conectarse. No escribas valores ficticios en `reported` ni sobrescribas datos existentes sin revisarlos.

El contenido lógico de la orden es `{"desired":{"door":"closed"}}`; en una API de actualización se envuelve como `{"state":{"desired":{"door":"closed"}}}`. `desired` expresa lo solicitado, `reported` lo informado por el ESP32 y `delta` las diferencias. No se ha reportado aún el sensor al Shadow; no prellenar su valor ni la posición del servo.

## Tópicos previstos para la Fase 4

El ESP32 deberá usar exactamente estos nombres y suscribirse a cada respuesta antes de publicar solicitudes:

| Tópico | Acción del ESP32 | Finalidad |
|---|---|---|
| `$aws/things/puerta-mascotas-01/shadow/get` | Publicar | Solicitar el documento actual. |
| `$aws/things/puerta-mascotas-01/shadow/get/accepted` | Suscribirse y recibir | Obtener el Shadow actual y recuperar el estado pendiente. |
| `$aws/things/puerta-mascotas-01/shadow/get/rejected` | Suscribirse y recibir | Conocer el fallo; un Shadow inexistente puede devolver 404. |
| `$aws/things/puerta-mascotas-01/shadow/update` | Publicar | Enviar actualizaciones de `reported`. |
| `$aws/things/puerta-mascotas-01/shadow/update/delta` | Suscribirse y recibir | Recibir diferencias entre `desired` y `reported`. |
| `$aws/things/puerta-mascotas-01/shadow/update/accepted` | Suscribirse y recibir | Confirmación de que el servicio aceptó una actualización. |
| `$aws/things/puerta-mascotas-01/shadow/update/rejected` | Suscribirse y recibir | Error de actualización. |

Al conectar o reconectar, el futuro firmware deberá restablecer suscripciones, solicitar `get`, tratar los errores y reconciliar el `desired` válido con el último estado aplicado, incluso si no recibió el `delta` durante la desconexión. Debe manejar duplicados y orden de mensajes mediante la versión del Shadow para evitar aplicar un estado anterior. Si `get` responde 404, tratar el Shadow como inexistente y publicar solo estados `reported` realmente disponibles; no asumir un comando deseado. Los detalles del manejo de concurrencia y reconexión se implementarán en la fase siguiente.

## Seguridad y datos para conservar

La política real de permisos amplios se usa por indicación docente; puede permitir acceso a recursos innecesarios y ampliar el impacto de una clave comprometida. Su documento exacto no se ha proporcionado. Como alternativa de producción, la política de ejemplo concede `Connect` al client ID exacto, `Publish` solo a `get` y `update`, `Subscribe` a filtros exactos y `Receive` a los tópicos de respuesta exactos. Los ARN usan respectivamente `client`, `topic`, `topicfilter` y `topic`; no incluyen comodines ni permisos de administración. AWS IoT autoriza publicar en `update` por tópico, no restringe el JSON a `reported`: el firmware deberá respetar esa responsabilidad. Para otro Thing se necesitará su propia configuración y permisos.

Para MQTT.fx se requiere un client ID distinto del ESP32 y una identidad autorizada para ese ID y los tópicos de diagnóstico. La plantilla del ESP32 restringe `Connect` a `puerta-mascotas-01`, por lo que no permite conectar con el ID de MQTT.fx; los permisos de la política académica real deben revisarse manualmente. En producción debe usarse un certificado y una política independientes. Véase el [procedimiento pendiente](../README.md#diagnóstico-manual-previsto-con-mqttfx).

Conserva de forma privada: región, ID de cuenta, endpoint ATS, nombre del Thing y client ID, nombre/ID de la política, ID y estado del certificado, certificado del dispositivo, clave privada y CA raíz. La clave privada y el certificado no se deben enviar por chat ni incorporar al repositorio. Las credenciales WiFi también se guardarán localmente y no se incluirán en el código público. Un `.gitignore` evita incorporar archivos no rastreados, pero no elimina secretos ya rastreados; revisar manualmente antes de publicar.

Referencias oficiales: [aprovisionamiento del dispositivo y política](https://docs.aws.amazon.com/iot/latest/developerguide/shadow-provision-cloud.html), [autenticación del servidor y endpoint ATS](https://docs.aws.amazon.com/iot/latest/developerguide/server-authentication.html), [ARN de tópicos y filtros](https://docs.aws.amazon.com/iot/latest/developerguide/topics.html), [documentos del Shadow](https://docs.aws.amazon.com/iot/latest/developerguide/device-shadow-document.html).
