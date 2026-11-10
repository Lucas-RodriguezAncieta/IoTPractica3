# AWS Lambda — Puerta Inteligente para Mascotas

## 1. Descripción

AWS Lambda implementa el backend de la Skill de Alexa **Puerta Inteligente para Mascotas**.

La función `puerta_mascotas_alexa`, desarrollada en Python 3.11, procesa los comandos de voz recibidos desde Alexa Developer Console, consulta la vinculación del usuario en Amazon DynamoDB y se comunica con AWS IoT Core mediante Boto3.

La comunicación con el ESP32 se realiza mediante el Device Shadow clásico del Thing `puerta-mascotas-01`.

## 2. Arquitectura

**Control de puerta:**

Alexa → AWS Lambda → DynamoDB → AWS IoT Core → Device Shadow → ESP32 → Servomotor SG90.

**Consulta de sensores y estados:**

Sensor IR / ESP32 → AWS IoT Core → Device Shadow → AWS Lambda → Alexa.

DynamoDB almacena la relación entre cada usuario de Alexa y su dispositivo vinculado.

## 3. Configuración de Lambda

| Parámetro | Valor |
|---|---|
| Función | `puerta_mascotas_alexa` |
| Runtime | Python 3.11 |
| Región | `us-east-2` |
| Handler | `lambda_function.lambda_handler` |
| Tiempo de espera configurado | 7 segundos |
| Base de datos | DynamoDB |
| Comunicación con AWS | Boto3 |
| Procesamiento de Alexa | ASK SDK for Python |

### Variables de entorno

- `TABLE_NAME`: nombre de la tabla de DynamoDB.
- `THING_NAME`: nombre del Thing asociado al código de vinculación.
- `PAIRING_CODE`: código utilizado para vincular el dispositivo.
- `IOT_ENDPOINT`: endpoint ATS de AWS IoT Core, sin `https://`.

Las variables se configuran en AWS Lambda. No se deben almacenar credenciales privadas dentro del repositorio.

## 4. Handlers implementados

### VincularThingIntentHandler

Obtiene el identificador del usuario de Alexa, valida el código de vinculación y registra en DynamoDB la asociación entre `userId` y `thingName`.

### AbrirPuertaIntentHandler

Consulta el Thing vinculado al usuario y actualiza el Device Shadow clásico con `desired.door = "open"`.

### CerrarPuertaIntentHandler

Actualiza el estado deseado del dispositivo mediante `desired.door = "closed"`.

### ConsultarEstadoIntentHandler

Consulta el Device Shadow para obtener el último estado reportado mediante `reported.door`.

Distingue entre el estado solicitado (`desired`) y el estado comunicado por el dispositivo (`reported`).

### ConsultarSensorIntentHandler

Consulta `reported.objectDetected` para determinar si el sensor infrarrojo detectó un objeto.

- `true`: objeto detectado.
- `false`: ningún objeto detectado.
- Atributo ausente: no hay información reportada.

### DesvincularThingIntentHandler

Elimina de DynamoDB la vinculación existente entre el usuario de Alexa y su Thing.

La operación no elimina el dispositivo de AWS IoT Core.

### CambiarThingIntentHandler

Permite solicitar el cambio a otro Thing autorizado mediante un código de vinculación.

Durante las pruebas se validó el caso en que el usuario solicita cambiar al mismo dispositivo que ya tiene vinculado. La sustitución real por un segundo Thing no fue probada.

## 5. Integración con DynamoDB

Se utiliza la tabla `puerta_mascotas_usuarios`.

La clave de partición es `userId`, de tipo cadena.

Cada registro contiene el atributo `thingName`, utilizado para identificar el dispositivo asociado al usuario.

Lambda utiliza DynamoDB para vincular, consultar, cambiar o eliminar asociaciones.

## 6. Integración con AWS IoT Core

Se utiliza el Thing `puerta-mascotas-01` y su Device Shadow clásico.

Los comandos de apertura y cierre modifican el estado `desired`.

El ESP32 recibe los cambios por MQTT/TLS y publica su estado en `reported`.

Los atributos principales son:

| Atributo | Descripción |
|---|---|
| `desired.door` | Apertura o cierre solicitado |
| `reported.door` | Estado informado por el ESP32 |
| `reported.servoAngle` | Ángulo comunicado por el firmware |
| `reported.objectDetected` | Última detección del sensor IR |

Lambda utiliza las operaciones `update_thing_shadow` y `get_thing_shadow` para enviar órdenes y consultar información del dispositivo.

## 7. Permisos y seguridad

La función utiliza un rol de ejecución IAM para acceder a los servicios necesarios.

El rol debe disponer de los permisos apropiados para consultar y modificar la tabla DynamoDB, leer y actualizar el Device Shadow, y registrar eventos en CloudWatch.

Los certificados X.509 y las claves privadas pertenecen a la conexión MQTT/TLS del ESP32, no deben incluirse en este código.

## 8. Pruebas realizadas

Se comprobaron los siguientes casos mediante Alexa Developer Console y AWS:

1. Vinculación del usuario con el código configurado.
2. Envío de una orden de apertura al Device Shadow.
3. Envío de una orden de cierre al Device Shadow.
4. Consulta del estado reportado de la puerta.
5. Consulta del sensor infrarrojo sin detección.
6. Consulta del sensor infrarrojo con detección.
7. Desvinculación del usuario y comprobación de la eliminación del elemento en DynamoDB.
8. Nueva vinculación del mismo usuario.
9. Solicitud de cambio al Thing que ya estaba vinculado.

También se observó la sincronización de `desired.door` y `reported.door` en AWS IoT Core, y se confirmó con el integrante responsable del hardware el movimiento del servomotor SG90.

No se registraron mediciones suficientes para afirmar resultados cuantitativos de latencia, disponibilidad o tasa de éxito.

## 9. Diagnóstico

Durante las pruebas iniciales se presentaron problemas que se corrigieron:

- Endpoint ATS incorrecto en la configuración de Lambda.
- Tiempo de espera insuficiente para algunas ejecuciones.
- Confusión entre intents de apertura y cierre en el modelo de interacción de Alexa.
- Confusión entre los intents de vinculación y cambio de dispositivo.

Se utilizó Amazon CloudWatch para identificar errores durante la ejecución de Lambda y comprobar sus causas.

## 10. Archivos

- `lambda_function.py`: código de la función y handlers de Alexa.
- `README.md`: documentación de la implementación.

El código se desplegó en AWS Lambda mediante la consola y paquetes ZIP con las dependencias necesarias.

Para reproducir el despliegue deben incluirse las dependencias compatibles con el runtime seleccionado y configurar los recursos AWS correspondientes.

## 11. Conclusión

La integración de AWS Lambda permite que Alexa controle y consulte de forma remota una puerta inteligente basada en ESP32.

DynamoDB mantiene las vinculaciones de los usuarios, mientras que Device Shadow permite almacenar órdenes y estados incluso cuando el dispositivo no está conectado.

Las pruebas realizadas comprobaron el funcionamiento de los comandos y consultas principales, así como la comunicación entre Alexa, AWS IoT Core y el prototipo físico.