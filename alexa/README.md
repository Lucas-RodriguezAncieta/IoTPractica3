# Alexa — Puerta Inteligente para Mascotas

## 1. Descripción

Se desarrolló una Skill personalizada de Amazon Alexa denominada **Puerta Inteligente para Mascotas**, que permite controlar una puerta automatizada y consultar su estado mediante comandos de voz.

La Skill utiliza AWS Lambda como backend, DynamoDB para administrar la vinculación entre usuarios y dispositivos, y AWS IoT Core para comunicarse con el ESP32 a través del Device Shadow.

## 2. Configuración de la Skill

| Parámetro | Configuración |
|---|---|
| Plataforma | Alexa Developer Console |
| Tipo | Custom Skill |
| Idioma | Español (México), es-MX |
| Nombre de invocación | puerta de mascotas |
| Backend | AWS Lambda |
| Función Lambda | `puerta_mascotas_alexa` |
| Región del backend | `us-east-2` |

El modelo de interacción se encuentra en `modelo_interaccion_es-MX.json`.

## 3. Intents implementados

### VincularThingIntent

Permite asociar un dispositivo IoT con el usuario de Alexa mediante un código de vinculación.

Lambda verifica el código y guarda la asociación en DynamoDB.

**Ejemplo:**

"Dile a puerta de mascotas que conecte mi puerta con el código cuatro ocho dos siete".

### AbrirPuertaIntent

Solicita la apertura de la puerta.

AWS Lambda actualiza el estado `desired.door` del Device Shadow con el valor `"open"`.

**Ejemplo:**

"Dile a puerta de mascotas que abra la puerta".

### CerrarPuertaIntent

Solicita el cierre de la puerta mediante la actualización de `desired.door` a `"closed"`.

**Ejemplo:**

"Dile a puerta de mascotas que cierre la puerta".

### ConsultarEstadoIntent

Permite conocer el último estado informado por el ESP32.

Lambda consulta `reported.door` y diferencia una orden pendiente de un estado confirmado por el dispositivo.

**Ejemplo:**

"Dile a puerta de mascotas que consulte el estado de la puerta".

### ConsultarSensorIntent

Permite consultar la última detección del sensor infrarrojo conectado al ESP32.

Lambda lee el atributo `reported.objectDetected` del Device Shadow y Alexa comunica el resultado al usuario.

**Ejemplo:**

"Dile a puerta de mascotas que consulte el sensor".

### DesvincularThingIntent

Elimina la asociación entre el usuario de Alexa y su dispositivo almacenada en DynamoDB.

Esta operación no elimina el Thing de AWS IoT Core.

**Ejemplo:**

"Dile a puerta de mascotas que desvincule mi puerta".

### CambiarThingIntent

Recibe una solicitud para cambiar la vinculación del dispositivo.

Durante las pruebas se comprobó que el sistema identifica cuando el código corresponde al Thing que ya está vinculado. No se realizó una prueba de sustitución por otro dispositivo físico.

**Ejemplo:**

"Dile a puerta de mascotas que cambie mi puerta con el código cuatro ocho dos siete".

## 4. Modelo de interacción

El archivo `modelo_interaccion_es-MX.json` contiene la configuración exportada de Alexa Developer Console, incluyendo:

- Nombre de invocación.
- Intents personalizados y los intents integrados de Amazon.
- Frases de ejemplo (sample utterances).
- Slots y tipos de datos utilizados.

Los nombres y tipos exactos de los slots deben consultarse en el archivo JSON exportado.

### Intents y slots configurados

El modelo de interacción contiene siete intents personalizados y cuatro intents integrados de Amazon:

**Intents personalizados:**
- `AbrirPuertaIntent`
- `CerrarPuertaIntent`
- `ConsultarEstadoIntent`
- `ConsultarSensorIntent`
- `VincularThingIntent`
- `CambiarThingIntent`
- `DesvincularThingIntent`

**Intents integrados:**
- `AMAZON.CancelIntent`
- `AMAZON.HelpIntent`
- `AMAZON.StopIntent`
- `AMAZON.NavigateHomeIntent`

Los intents `VincularThingIntent` y `CambiarThingIntent` utilizan el slot `codigo`, configurado con el tipo integrado `AMAZON.FOUR_DIGIT_NUMBER`.

Este slot permite a Alexa interpretar un código de cuatro dígitos, que posteriormente es procesado por AWS Lambda para gestionar la vinculación del dispositivo.

El nombre de invocación configurado es `puerta de mascotas` y el idioma es español de México (`es-MX`).

## 5. Arquitectura de comunicación

### Control de la puerta

1. El usuario expresa un comando de voz.
2. Alexa identifica el intent correspondiente.
3. Alexa envía una solicitud a AWS Lambda.
4. Lambda valida la vinculación del usuario mediante DynamoDB.
5. Lambda actualiza el Device Shadow de AWS IoT Core.
6. El ESP32 recibe la orden por MQTT/TLS y controla el servomotor.
7. El ESP32 reporta el estado actualizado al Shadow.

### Consulta del sensor

1. El sensor infrarrojo detecta o deja de detectar un objeto.
2. El ESP32 publica la lectura en `reported.objectDetected`.
3. El usuario solicita una consulta mediante Alexa.
4. AWS Lambda obtiene la última lectura del Shadow.
5. Alexa comunica el estado detectado.

## 6. Pruebas realizadas

Se utilizó la sección Test de Alexa Developer Console para verificar los comandos personalizados.

Se comprobaron los siguientes comportamientos:

- Vinculación del usuario mediante código.
- Apertura y cierre de la puerta.
- Consulta del estado de la puerta.
- Consulta del sensor con y sin detección.
- Desvinculación y posterior vinculación.
- Reconocimiento de una solicitud de cambio al dispositivo ya vinculado.

También se verificó en AWS IoT Core que el ESP32 sincronizaba el estado del Device Shadow. El integrante encargado del hardware confirmó el movimiento físico del servomotor SG90.

## 7. Dificultades y soluciones

Durante la implementación se presentaron dificultades en el reconocimiento de algunos comandos.

Alexa confundía inicialmente algunas expresiones correspondientes a apertura, cierre, vinculación y cambio de dispositivo.

Para corregir este comportamiento se agregaron y ajustaron frases de ejemplo en los intents, se reconstruyó el modelo de interacción y se repitieron las pruebas.

## 8. Evidencias

Las capturas de pantalla de las pruebas deben conservarse en la carpeta `evidencias/` del repositorio.

Se recomienda incluir el modelo de interacción, las respuestas de Alexa, el estado del Device Shadow y las pruebas físicas realizadas.

## 9. Conclusión

La integración de Alexa permite controlar y consultar la puerta inteligente mediante lenguaje natural, utilizando servicios administrados de AWS.

Las pruebas comprobaron la comunicación principal entre Alexa, Lambda, DynamoDB, AWS IoT Core y ESP32, incluyendo órdenes de movimiento y consultas del sensor infrarrojo.