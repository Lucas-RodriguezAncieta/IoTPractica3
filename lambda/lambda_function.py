# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import ask_sdk_core.utils as ask_utils

import os
import json
import boto3
from botocore.exceptions import ClientError

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        speak_output = "Bienvenido, puedes decir hola o ayuda. Qué quieres probar?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class HelloWorldIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("HelloWorldIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Hola bola!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Me puedes decir hola, te ayudo en algo más?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        speech = "Hmm, I'm not sure. You can say Hello or Help. What would you like to do?"
        reprompt = "I didn't catch that. What can I help you with?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )



class VincularThingIntentHandler(AbstractRequestHandler):

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name(
            "VincularThingIntent"
        )(handler_input)

    def handle(self, handler_input):
        rb = handler_input.response_builder

        valor = ask_utils.get_slot_value(
            handler_input, "codigo"
        )

        codigo = "".join(
            c for c in (valor or "") if c.isdigit()
        )

        if not codigo or codigo != os.environ.get("PAIRING_CODE"):
            return rb.speak(
                "El código no es válido. Intenta nuevamente."
            ).response

        session = handler_input.request_envelope.session

        user_id = (
            session.user.user_id
            if session and session.user else None
        )

        if not user_id:
            return rb.speak(
                "No pude identificar al usuario de Alexa."
            ).response

        thing_name = os.environ["THING_NAME"]

        try:
            iot = boto3.client("iot")

            iot.describe_thing(
                thingName=thing_name
            )

            tabla = boto3.resource("dynamodb").Table(
                os.environ["TABLE_NAME"]
            )

            tabla.put_item(
                Item={
                    "userId": user_id,
                    "thingName": thing_name
                },
                ConditionExpression="attribute_not_exists(userId)"
            )

        except ClientError as error:
            if error.response["Error"]["Code"] == \
                    "ConditionalCheckFailedException":
                return rb.speak(
                    "Ya tienes una puerta vinculada. "
                    "Usa la opción cambiar dispositivo."
                ).response

            logger.exception("Error al vincular el Thing")

            return rb.speak(
                "No pude vincular la puerta. "
                "Revisa la configuración de AWS."
            ).response

        return rb.speak(
            "Tu puerta de mascotas quedó vinculada correctamente."
        ).response



class AbrirPuertaIntentHandler(AbstractRequestHandler):

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name(
            "AbrirPuertaIntent"
        )(handler_input)

    def handle(self, handler_input):
        rb = handler_input.response_builder

        session = handler_input.request_envelope.session
        user_id = (
            session.user.user_id
            if session and session.user else None
        )

        if not user_id:
            return rb.speak(
                "No pude identificar tu cuenta de Alexa."
            ).response

        try:
            # 1. Buscar el Thing vinculado en DynamoDB
            tabla = boto3.resource("dynamodb").Table(
                os.environ["TABLE_NAME"]
            )

            resultado = tabla.get_item(
                Key={"userId": user_id},
                ConsistentRead=True
            )

            item = resultado.get("Item")

            if not item or not item.get("thingName"):
                return rb.speak(
                    "Primero debes vincular tu puerta de mascotas."
                ).response

            thing_name = item["thingName"]

            # 2. Conectar con AWS IoT Data
            endpoint = os.environ["IOT_ENDPOINT"]

            iot_data = boto3.client(
                "iot-data",
                endpoint_url="https://" + endpoint
            )

            # 3. Solicitar abrir la puerta
            mensaje = {
                "state": {
                    "desired": {
                        "door": "open"
                    }
                }
            }

            iot_data.update_thing_shadow(
                thingName=thing_name,
                payload=json.dumps(mensaje).encode("utf-8")
            )

            return rb.speak(
                "He enviado la orden para abrir "
                "la puerta de tu mascota."
            ).response

        except (ClientError, KeyError, ValueError):
            logger.exception("Error al solicitar apertura")
            return rb.speak(
                "Ocurrió un problema al enviar "
                "la orden de apertura."
            ).response



class CerrarPuertaIntentHandler(AbstractRequestHandler):

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name(
            "CerrarPuertaIntent"
        )(handler_input)

    def handle(self, handler_input):
        rb = handler_input.response_builder

        session = handler_input.request_envelope.session
        user_id = (
            session.user.user_id
            if session and session.user else None
        )

        if not user_id:
            return rb.speak(
                "No pude identificar tu cuenta de Alexa."
            ).response

        try:
            tabla = boto3.resource("dynamodb").Table(
                os.environ["TABLE_NAME"]
            )

            resultado = tabla.get_item(
                Key={"userId": user_id},
                ConsistentRead=True
            )

            item = resultado.get("Item")

            if not item or not item.get("thingName"):
                return rb.speak(
                    "Primero debes vincular tu puerta de mascotas."
                ).response

            thing_name = item["thingName"]

            iot_data = boto3.client(
                "iot-data",
                endpoint_url="https://" + os.environ["IOT_ENDPOINT"]
            )

            mensaje = {
                "state": {
                    "desired": {
                        "door": "closed"
                    }
                }
            }

            iot_data.update_thing_shadow(
                thingName=thing_name,
                payload=json.dumps(mensaje).encode("utf-8")
            )

            return rb.speak(
                "He enviado la orden para cerrar "
                "la puerta de tu mascota."
            ).response

        except (ClientError, KeyError, ValueError):
            logger.exception("Error al solicitar cierre")
            return rb.speak(
                "Ocurrió un problema al enviar "
                "la orden de cierre."
            ).response


class ConsultarEstadoIntentHandler(AbstractRequestHandler):

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name(
            "ConsultarEstadoIntent"
        )(handler_input)

    def handle(self, handler_input):
        rb = handler_input.response_builder

        session = handler_input.request_envelope.session
        user_id = (
            session.user.user_id
            if session and session.user else None
        )

        if not user_id:
            return rb.speak(
                "No pude identificar tu cuenta de Alexa."
            ).response

        try:
            tabla = boto3.resource("dynamodb").Table(
                os.environ["TABLE_NAME"]
            )

            resultado = tabla.get_item(
                Key={"userId": user_id}
            )

            item = resultado.get("Item")

            if not item or not item.get("thingName"):
                return rb.speak(
                    "Primero debes vincular tu puerta."
                ).response

            iot_data = boto3.client(
                "iot-data",
                endpoint_url="https://" + os.environ["IOT_ENDPOINT"]
            )

            respuesta = iot_data.get_thing_shadow(
                thingName=item["thingName"]
            )

            documento = json.loads(
                respuesta["payload"].read()
            )

            state = documento.get("state", {})
            desired = state.get("desired", {}).get("door")
            reported = state.get("reported", {}).get("door")

            estados = {
                "open": "abierta",
                "closed": "cerrada"
            }

            if reported in estados:
                mensaje = (
                    "El último estado reportado por el "
                    "dispositivo es puerta " + estados[reported] + "."
                )

                if desired in estados and desired != reported:
                    mensaje += (
                        " Hay una orden pendiente para "
                        "dejarla " + estados[desired] + "."
                    )

            elif desired in estados:
                mensaje = (
                    "Se ha solicitado dejar la puerta "
                    + estados[desired] +
                    ", pero el dispositivo todavía "
                    "no ha confirmado su estado."
                )

            else:
                mensaje = (
                    "Todavía no tengo información "
                    "sobre el estado de la puerta."
                )

            return rb.speak(mensaje).response

        except (ClientError, KeyError, ValueError):
            logger.exception("Error al consultar estado")
            return rb.speak(
                "No pude consultar el estado de la puerta."
            ).response



class ConsultarSensorIntentHandler(AbstractRequestHandler):

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name(
            "ConsultarSensorIntent"
        )(handler_input)

    def handle(self, handler_input):
        rb = handler_input.response_builder

        session = handler_input.request_envelope.session
        user_id = (
            session.user.user_id
            if session and session.user else None
        )

        if not user_id:
            return rb.speak(
                "No pude identificar tu cuenta de Alexa."
            ).response

        try:
            tabla = boto3.resource("dynamodb").Table(
                os.environ["TABLE_NAME"]
            )

            resultado = tabla.get_item(
                Key={"userId": user_id}
            )

            item = resultado.get("Item")

            if not item or not item.get("thingName"):
                return rb.speak(
                    "Primero debes vincular tu puerta."
                ).response

            iot_data = boto3.client(
                "iot-data",
                endpoint_url="https://" + os.environ["IOT_ENDPOINT"]
            )

            respuesta = iot_data.get_thing_shadow(
                thingName=item["thingName"]
            )

            documento = json.loads(
                respuesta["payload"].read()
            )

            reported = documento.get(
                "state", {}
            ).get("reported", {})

            deteccion = reported.get("objectDetected")

            if deteccion is True:
                mensaje = (
                    "La última lectura del sensor "
                    "infrarrojo indica que detectó "
                    "un objeto cerca de la puerta."
                )

            elif deteccion is False:
                mensaje = (
                    "La última lectura del sensor "
                    "infrarrojo indica que no "
                    "detectó ningún objeto."
                )

            else:
                mensaje = (
                    "El sensor infrarrojo todavía "
                    "no ha reportado información."
                )

            return rb.speak(mensaje).response

        except (ClientError, KeyError, ValueError):
            logger.exception("Error al consultar sensor")

            return rb.speak(
                "No pude consultar el sensor infrarrojo."
            ).response


class DesvincularThingIntentHandler(AbstractRequestHandler):

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name(
            "DesvincularThingIntent"
        )(handler_input)

    def handle(self, handler_input):
        rb = handler_input.response_builder

        session = handler_input.request_envelope.session
        user_id = (
            session.user.user_id
            if session and session.user else None
        )

        if not user_id:
            return rb.speak(
                "No pude identificar tu cuenta de Alexa."
            ).response

        try:
            tabla = boto3.resource("dynamodb").Table(
                os.environ["TABLE_NAME"]
            )

            resultado = tabla.get_item(
                Key={"userId": user_id}
            )

            if "Item" not in resultado:
                return rb.speak(
                    "No tienes ninguna puerta vinculada."
                ).response

            tabla.delete_item(
                Key={"userId": user_id}
            )

            return rb.speak(
                "Tu puerta de mascotas ha sido "
                "desvinculada correctamente."
            ).response

        except (ClientError, KeyError):
            logger.exception("Error al desvincular Thing")

            return rb.speak(
                "No pude desvincular tu puerta."
            ).response


class CambiarThingIntentHandler(AbstractRequestHandler):

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name(
            "CambiarThingIntent"
        )(handler_input)

    def handle(self, handler_input):
        rb = handler_input.response_builder

        session = handler_input.request_envelope.session
        user_id = (
            session.user.user_id
            if session and session.user else None
        )

        if not user_id:
            return rb.speak(
                "No pude identificar tu cuenta de Alexa."
            ).response

        valor = ask_utils.get_slot_value(
            handler_input, "codigo"
        )

        codigo = "".join(
            c for c in (valor or "") if c.isdigit()
        )

        # Dispositivos autorizados para la demostración
        dispositivos = {
            os.environ["PAIRING_CODE"]: os.environ["THING_NAME"]
        }

        nuevo_thing = dispositivos.get(codigo)

        if not nuevo_thing:
            return rb.speak(
                "El código del dispositivo no es válido."
            ).response

        try:
            tabla = boto3.resource("dynamodb").Table(
                os.environ["TABLE_NAME"]
            )

            resultado = tabla.get_item(
                Key={"userId": user_id},
                ConsistentRead=True
            )

            actual = resultado.get("Item")

            if not actual:
                return rb.speak(
                    "Primero debes vincular una puerta."
                ).response

            if actual.get("thingName") == nuevo_thing:
                return rb.speak(
                    "Ese dispositivo ya está vinculado "
                    "a tu cuenta. No necesitas cambiarlo."
                ).response

            iot = boto3.client("iot")
            iot.describe_thing(thingName=nuevo_thing)

            tabla.put_item(
                Item={
                    "userId": user_id,
                    "thingName": nuevo_thing
                },
                ConditionExpression="attribute_exists(userId)"
            )

            return rb.speak(
                "Tu puerta vinculada se ha cambiado "
                "correctamente."
            ).response

        except ClientError:
            logger.exception("Error al cambiar Thing")

            return rb.speak(
                "No pude cambiar el dispositivo vinculado."
            ).response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(HelloWorldIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(VincularThingIntentHandler())
sb.add_request_handler(AbrirPuertaIntentHandler())
sb.add_request_handler(CerrarPuertaIntentHandler())
sb.add_request_handler(ConsultarEstadoIntentHandler())
sb.add_request_handler(ConsultarSensorIntentHandler())
sb.add_request_handler(DesvincularThingIntentHandler())
sb.add_request_handler(CambiarThingIntentHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
