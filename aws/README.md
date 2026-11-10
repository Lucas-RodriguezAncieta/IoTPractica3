# AWS IoT Core — Puerta Inteligente para Mascotas

## 1. Descripción general

Este documento describe la configuración e integración de los servicios de Amazon Web Services (AWS) utilizados en la **Práctica 3: Puerta Inteligente para Mascotas**.

El proyecto permite controlar una puerta automatizada mediante comandos de voz de Amazon Alexa, utilizando un ESP32, un servomotor SG90 y un sensor infrarrojo.

La infraestructura AWS fue configurada inicialmente de forma manual y posteriormente integrada con el firmware del ESP32 y una Skill personalizada de Alexa.

Los servicios utilizados son:

- **AWS IoT Core:** comunicación segura entre el ESP32 y la nube mediante MQTT/TLS.
- **Device Shadow:** almacenamiento y sincronización del estado deseado y reportado del dispositivo.
- **AWS Lambda:** procesamiento de los comandos enviados desde Alexa.
- **Amazon DynamoDB:** almacenamiento persistente de las vinculaciones entre usuarios y dispositivos.
- **AWS IAM:** administración de los permisos de acceso.
- **Amazon CloudWatch:** consulta de registros y diagnóstico de errores de Lambda.

La integración principal fue probada mediante comandos de Alexa, actualizaciones MQTT, consultas del sensor infrarrojo y movimiento físico del servomotor.

## 2. Arquitectura del sistema

El sistema utiliza una arquitectura en la que Alexa se comunica con AWS Lambda, mientras que el ESP32 mantiene una conexión segura con AWS IoT Core.

### 2.1. Control de apertura y cierre

1. El usuario solicita abrir o cerrar la puerta mediante Alexa.
2. Alexa identifica el intent y envía la solicitud a AWS Lambda.
3. Lambda consulta DynamoDB para identificar el Thing vinculado al usuario.
4. Lambda modifica el estado `desired` del Device Shadow.
5. El ESP32 recibe la orden mediante MQTT/TLS.
6. El firmware controla el servomotor SG90.
7. El ESP32 publica el estado actualizado mediante `reported`.

**Flujo:**

Alexa → AWS Lambda → DynamoDB / AWS IoT Core → Device Shadow → ESP32 → SG90.

### 2.2. Consulta del sensor infrarrojo

1. El sensor IR detecta la presencia o ausencia de un objeto.
2. El ESP32 obtiene la lectura del sensor.
3. El firmware actualiza `reported.objectDetected` en el Device Shadow.
4. El usuario consulta el sensor desde Alexa.
5. AWS Lambda lee la última información reportada.
6. Alexa responde según el estado almacenado.

**Flujo:**

Sensor IR → ESP32 → AWS IoT Core → Device Shadow → AWS Lambda → Alexa.

DynamoDB también interviene en las consultas cuando Lambda necesita resolver la vinculación del usuario.

## 3. Configuración de AWS IoT Core

### 3.1. Recursos utilizados

| Parámetro | Configuración |
|---|---|
| Región | `us-east-2` (Ohio) |
| Thing | `puerta-mascotas-01` |
| Client ID principal | `puerta-mascotas-01` |
| Tipo de Shadow | Clásico (sin nombre) |
| Protocolo | MQTT sobre TLS |
| Puerto | `8883` |
| Autenticación del ESP32 | Certificado X.509 |
| Política IoT | `PuertaMascotasIoTPolicy` |
| Versión activa comprobada | 3 |

El Thing `puerta-mascotas-01` representa el dispositivo físico basado en ESP32.

### 3.2. Endpoint ATS

Se utiliza el endpoint de datos ATS de AWS IoT Core correspondiente a la cuenta y región del proyecto.

Su formato es:

`<endpoint-propio>-ats.iot.us-east-2.amazonaws.com`

El endpoint real debe obtenerse desde:

**AWS IoT Core → Settings → Device data endpoint**

Para establecer conexiones MQTT/TLS se utiliza el nombre de host y el puerto 8883.

En AWS Lambda, la variable de entorno `IOT_ENDPOINT` contiene el host sin el prefijo `https://`.

### 3.3. Certificados X.509

Se generó un certificado X.509 para autenticar el ESP32 ante AWS IoT Core.

Se comprobó que el certificado estaba:

- Activo.
- Asociado al Thing `puerta-mascotas-01`.
- Asociado a la política `PuertaMascotasIoTPolicy`.

El ESP32 utiliza el certificado del dispositivo, su clave privada y el certificado raíz correspondiente para establecer la conexión TLS.

**Medidas de seguridad:**

- No publicar claves privadas en GitHub.
- No incluir credenciales WiFi en el repositorio.
- Mantener los certificados en archivos locales protegidos.
- No registrar secretos en capturas de pantalla ni documentación.
- Sustituir o revocar los certificados cuando exista sospecha de exposición.

La asociación administrativa del certificado no demuestra por sí sola la conectividad; esta se comprobó posteriormente mediante la comunicación del ESP32 con AWS IoT Core.

## 4. Device Shadow

El proyecto utiliza el **Device Shadow clásico**, también llamado Shadow sin nombre.

Este recurso conserva una representación del estado del dispositivo en AWS.

### 4.1. Estado desired

El atributo `desired` representa el estado solicitado.

Los comandos utilizados fueron:

- `"open"`: solicitud de apertura.
- `"closed"`: solicitud de cierre.

Ejemplo de apertura:

```json
{
  "state": {
    "desired": {
      "door": "open"
    }
  }
}
```

Ejemplo de cierre:

```json
{
  "state": {
    "desired": {
      "door": "closed"
    }
  }
}
```

### 4.2. Estado reported

El atributo `reported` contiene el estado comunicado por el firmware del ESP32.

| Atributo | Descripción |
|---|---|
| `reported.door` | Estado de puerta informado por el dispositivo |
| `reported.servoAngle` | Ángulo comunicado por el firmware |
| `reported.objectDetected` | Lectura del sensor infrarrojo |

En la configuración utilizada durante las pruebas:

| Estado | Valor de door | Ángulo configurado |
|---|---|---|
| Abierta | `open` | 180° |
| Cerrada | `closed` | 0° |

El atributo `servoAngle` representa la posición comandada o informada por el firmware; no constituye una medición independiente de la posición física.

### 4.3. Estado delta

AWS IoT Core calcula las diferencias entre los estados `desired` y `reported`.

Cuando existe una diferencia, puede generar un documento `delta`.

Por ejemplo, si se solicita cerrar la puerta mientras el último estado reportado es abierto, se genera una diferencia pendiente para `door`.

Después de procesar la orden, el ESP32 actualiza `reported`.

Cuando ambos estados coinciden, deja de existir una diferencia pendiente para ese atributo.

### 4.4. Ejemplo de estado sincronizado

El siguiente documento es un ejemplo ilustrativo del Shadow cuando la puerta está cerrada:

```json
{
  "state": {
    "desired": {
      "door": "closed"
    },
    "reported": {
      "door": "closed",
      "servoAngle": 0,
      "objectDetected": false
    }
  }
}
```

El valor de `objectDetected` depende de la lectura real del sensor y no está determinado por la posición de la puerta.

Durante las pruebas se observaron estados sincronizados de apertura y cierre.

## 5. Tópicos MQTT

El firmware se comunica con AWS IoT Core utilizando los tópicos reservados del Device Shadow.

| Tópico | Operación | Finalidad |
|---|---|---|
| `$aws/things/puerta-mascotas-01/shadow/get` | Publicar | Solicitar el Shadow |
| `$aws/things/puerta-mascotas-01/shadow/get/accepted` | Recibir | Obtener el documento solicitado |
| `$aws/things/puerta-mascotas-01/shadow/get/rejected` | Recibir | Conocer errores de consulta |
| `$aws/things/puerta-mascotas-01/shadow/update` | Publicar | Actualizar el Shadow |
| `$aws/things/puerta-mascotas-01/shadow/update/delta` | Recibir | Detectar diferencias de estado |
| `$aws/things/puerta-mascotas-01/shadow/update/accepted` | Recibir | Confirmar actualizaciones aceptadas |
| `$aws/things/puerta-mascotas-01/shadow/update/rejected` | Recibir | Conocer actualizaciones rechazadas |

Estos tópicos se consideraron en la configuración de permisos del dispositivo.

Para una implementación robusta es importante recuperar el estado al reconectar, restaurar las suscripciones, comprobar los errores y evitar aplicar mensajes obsoletos mediante el manejo de versiones del Shadow.

Las pruebas realizadas demostraron la sincronización básica, pero no constituyen una validación exhaustiva de todos los escenarios de reconexión y concurrencia.

## 6. Política AWS IoT y seguridad

### 6.1. Política configurada

Se utiliza la política:

`PuertaMascotasIoTPolicy`

Durante el desarrollo se detectaron errores en los ARN de los recursos autorizados, que fueron corregidos para utilizar la cuenta AWS correspondiente.

Se confirmó la versión 3 como versión activa durante las pruebas.

### 6.2. Permisos utilizados

| Permiso | Función |
|---|---|
| `iot:Connect` | Autorizar la conexión MQTT |
| `iot:Publish` | Publicar solicitudes y actualizaciones |
| `iot:Subscribe` | Suscribirse a filtros de tópicos |
| `iot:Receive` | Recibir mensajes MQTT |

La política fue configurada para autorizar los recursos necesarios del Thing.

Se incluyeron los siguientes identificadores de cliente MQTT:

- `puerta-mascotas-01`
- `mqttfx-puerta-mascotas-01`

El segundo identificador se contempló para pruebas con un cliente MQTT externo.

Los permisos de publicación se limitaron a los tópicos de consulta y actualización del Shadow. Las suscripciones y recepciones se limitaron a las respuestas y notificaciones necesarias.

### 6.3. ARN utilizados

AWS IoT diferencia los recursos asociados con las distintas operaciones:

- `client/`: conexión MQTT.
- `topic/`: publicación y recepción.
- `topicfilter/`: suscripción.

Se recomienda mantener permisos de mínimo privilegio y evitar autorizaciones generales innecesarias.

### 6.4. Plantilla de política

El archivo `iot-policy.example.json` contiene una plantilla de política con los marcadores:

- `<REGION>`
- `<ACCOUNT_ID>`

Estos valores deben reemplazarse antes de utilizar la plantilla en otra cuenta.

La plantilla se conserva como referencia y **no debe confundirse con una exportación exacta de la versión activa de `PuertaMascotasIoTPolicy`**.

## 7. Amazon DynamoDB

Se utiliza DynamoDB para almacenar las vinculaciones entre los usuarios de Alexa y los dispositivos IoT.

### 7.1. Tabla utilizada

`puerta_mascotas_usuarios`

| Atributo | Tipo | Descripción |
|---|---|---|
| `userId` | String | Clave de partición |
| `thingName` | String | Nombre del Thing vinculado |

La tabla permite mantener la asociación de cada usuario con su dispositivo.

### 7.2. Operaciones realizadas

AWS Lambda utiliza DynamoDB para:

1. Registrar la vinculación inicial de un usuario.
2. Consultar el Thing vinculado.
3. Gestionar solicitudes de cambio de dispositivo.
4. Eliminar vinculaciones.

Se comprobó la eliminación de un registro al ejecutar la desvinculación desde Alexa y posteriormente se realizó una nueva vinculación.

La desvinculación no elimina el Thing ni su certificado de AWS IoT Core.

## 8. AWS Lambda e IAM

### 8.1. Función Lambda

La función utilizada es:

`puerta_mascotas_alexa`

La función procesa las solicitudes de Alexa y utiliza Boto3 para comunicarse con DynamoDB y AWS IoT Core.

Las variables de entorno configuradas incluyen:

| Variable | Propósito |
|---|---|
| `TABLE_NAME` | Nombre de la tabla DynamoDB |
| `THING_NAME` | Thing asociado al código configurado |
| `PAIRING_CODE` | Código de vinculación |
| `IOT_ENDPOINT` | Endpoint ATS de AWS IoT Core |

Durante las pruebas se ajustó el tiempo de espera de Lambda a 7 segundos para evitar errores de timeout en determinadas invocaciones.

El código fuente se conserva en:

`../lambda/lambda_function.py`

### 8.2. Rol IAM

Se utiliza el rol:

`PuertaMascotasLambdaRole`

Este rol contiene los permisos necesarios para que Lambda acceda a los recursos del proyecto.

Entre las configuraciones utilizadas se encuentran:

- `AWSLambdaBasicExecutionRole`: permisos básicos de registro en CloudWatch.
- `PuertaMascotasLambdaRolePolicy`: política personalizada de acceso a los recursos correspondientes.

Los permisos permiten realizar las operaciones necesarias sobre DynamoDB y Device Shadow.

### 8.3. Amazon CloudWatch

CloudWatch se utilizó para consultar los registros de ejecución de Lambda y diagnosticar errores.

Durante el desarrollo se identificaron problemas relacionados con el endpoint de AWS IoT y el tiempo máximo de ejecución.

## 9. Integración con Alexa

Se desarrolló una Skill personalizada con el nombre de invocación:

`puerta de mascotas`

El modelo de interacción utiliza español de México (`es-MX`).

Se implementaron siete intents personalizados:

1. `VincularThingIntent`
2. `AbrirPuertaIntent`
3. `CerrarPuertaIntent`
4. `ConsultarEstadoIntent`
5. `ConsultarSensorIntent`
6. `DesvincularThingIntent`
7. `CambiarThingIntent`

Los intents de vinculación y cambio utilizan el slot `codigo`, de tipo `AMAZON.FOUR_DIGIT_NUMBER`.

El modelo de interacción se encuentra en:

`../alexa/modelo_interaccion_es-MX.json`

El código de procesamiento de los intents se encuentra en:

`../lambda/lambda_function.py`

## 10. Pruebas de integración realizadas

### 10.1. Prueba de publicación MQTT

Desde el cliente de prueba MQTT de AWS IoT Core se utilizó el tópico:

`$aws/things/puerta-mascotas-01/shadow/update`

Se publicaron solicitudes para modificar `desired.door` a `"open"` y `"closed"`.

**Resultado:** se observaron actualizaciones y sincronización de los estados `desired` y `reported`.

### 10.2. Prueba de apertura mediante Alexa

Se envió una orden de apertura desde Alexa Developer Console.

**Resultado:** la solicitud fue procesada por AWS Lambda y se comprobó el movimiento físico del SG90 mediante el integrante encargado del hardware.

### 10.3. Prueba de cierre mediante Alexa

Se envió una orden de cierre desde Alexa.

**Resultado:** el ESP32 informó el estado de cierre y se confirmó el movimiento físico del servomotor.

### 10.4. Consulta de estado

Se ejecutó el intent `ConsultarEstadoIntent`.

**Resultado:** Alexa comunicó el último estado reportado de la puerta a partir de la información almacenada en el Device Shadow.

### 10.5. Consulta del sensor infrarrojo

Se ejecutó el intent `ConsultarSensorIntent`.

Se comprobaron respuestas correspondientes a detección y ausencia de detección.

Cuando `reported.objectDetected` fue `true`, Alexa respondió que el sensor había detectado un objeto cerca de la puerta.

**Resultado:** se comprobó la consulta de la lectura del sensor mediante Alexa y AWS IoT Core.

### 10.6. Vinculación y desvinculación

Se probó la vinculación de un usuario con el Thing utilizando un código de cuatro dígitos.

Posteriormente se ejecutó la desvinculación y se verificó la eliminación del registro de DynamoDB.

Finalmente se realizó una nueva vinculación.

**Resultado:** se comprobó la persistencia y administración de la asociación entre usuario y dispositivo.

### 10.7. Cambio de dispositivo

Se probó la solicitud de cambiar al mismo Thing que ya estaba vinculado.

**Resultado:** el sistema identificó que el dispositivo ya estaba asociado al usuario.

No se realizó una prueba completa de sustitución por un segundo dispositivo físico.

## 11. Problemas encontrados y soluciones

| Problema | Solución aplicada |
|---|---|
| Endpoint incorrecto en Lambda | Se configuró el endpoint ATS real |
| Errores en ARN de la política IoT | Se corrigieron los identificadores de cuenta y recursos |
| Fallos iniciales de conexión MQTT | Se revisaron los permisos y la configuración de conexión |
| Timeout de Lambda | Se incrementó el tiempo de espera a 7 segundos |
| Diferencias entre desired y reported | Se revisó la sincronización del Device Shadow |
| Confusión de algunos comandos de Alexa | Se ajustaron las frases de ejemplo y se reconstruyó el modelo |

Estas correcciones permitieron completar las pruebas principales de integración.

## 12. Limitaciones y aspectos pendientes

Aunque se comprobó el funcionamiento de los componentes principales, existen aspectos que requieren pruebas adicionales:

- Medición sistemática de la latencia de extremo a extremo.
- Evaluación prolongada de estabilidad y disponibilidad.
- Pruebas de desconexión y reconexión prolongadas del ESP32.
- Evaluación del manejo de mensajes duplicados y versiones del Shadow.
- Prueba de cambio efectivo hacia un segundo Thing.
- Verificación independiente de la posición física del servomotor mediante un sensor de realimentación.

Estas pruebas no se consideran completadas en la presente documentación.

## 13. Archivos relacionados

| Archivo | Contenido |
|---|---|
| `aws/README.md` | Configuración e integración de servicios AWS |
| `aws/iot-policy.example.json` | Plantilla de política IoT |
| `lambda/lambda_function.py` | Código del backend de Alexa |
| `lambda/README.md` | Documentación de AWS Lambda |
| `alexa/modelo_interaccion_es-MX.json` | Modelo de interacción de Alexa |
| `alexa/README.md` | Documentación de Alexa |
| `docs/informe.md` | Informe técnico del proyecto |

Las evidencias gráficas deben conservarse en la carpeta `evidencias/`, evitando mostrar claves, certificados privados o información sensible.

## 14. Referencias oficiales

- [AWS IoT Core — Device Shadows](https://docs.aws.amazon.com/iot/latest/developerguide/iot-device-shadows.html)
- [AWS IoT Core — Documentos del Shadow](https://docs.aws.amazon.com/iot/latest/developerguide/device-shadow-document.html)
- [AWS IoT Core — Autenticación del servidor](https://docs.aws.amazon.com/iot/latest/developerguide/server-authentication.html)
- [AWS IoT Core — Tópicos MQTT](https://docs.aws.amazon.com/iot/latest/developerguide/topics.html)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/)

## 15. Conclusión

Se implementó una infraestructura basada en AWS que permite conectar un prototipo físico con una interfaz de control por voz.

AWS IoT Core proporciona la comunicación MQTT/TLS con el ESP32, mientras que el Device Shadow mantiene los estados deseados y reportados del dispositivo.

AWS Lambda procesa las solicitudes de Alexa y DynamoDB administra las vinculaciones de usuarios.

Las pruebas realizadas permitieron comprobar el envío de órdenes de apertura y cierre, el movimiento físico del servomotor SG90 y la consulta del sensor infrarrojo mediante Alexa.

El proyecto demuestra la integración funcional de un dispositivo IoT con servicios de nube y una interfaz de voz, manteniendo separados los componentes de hardware, procesamiento, almacenamiento y comunicación.