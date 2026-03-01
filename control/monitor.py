import ssl
import time
from datetime import datetime, timedelta

import schedule
from django.conf import settings
from django.db.models import Avg
from paho.mqtt import client as mqtt

from receiver.models import Data, Measurement

# Creamos el cliente global con la versión de API correcta para Paho 2.0+
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, settings.MQTT_USER_PUB)


def analyze_data():
    """
    Consulta datos de la última hora y envía alertas/comandos.
    """
    data = Data.objects.filter(base_time__gte=datetime.now() - timedelta(hours=1))
    aggregation = (
        data.annotate(check_value=Avg("avg_value"))
        .select_related("station", "measurement")
        .values(
            "check_value",
            "station__user__username",
            "measurement__name",
            "measurement__max_value",
            "measurement__min_value",
            "station__location__city__name",
            "station__location__state__name",
            "station__location__country__name",
        )
    )

    alerts = 0
    for item in aggregation:
        variable = item["measurement__name"]
        max_val = item["measurement__max_value"] or 0
        min_val = item["measurement__min_value"] or 0
        avg_value = item["check_value"]

        topic = "{}/{}/{}/{}/in".format(
            item["station__location__country__name"],
            item["station__location__state__name"],
            item["station__location__city__name"],
            item["station__user__username"],
        )

        # --- LÓGICA EXISTENTE (Alertas de rango) ---
        if avg_value > max_val or avg_value < min_val:
            message = "ALERT {} {} {}".format(variable, min_val, max_val)
            client.publish(topic, message)
            alerts += 1

        # --- NUEVO EVENTO (RETO PREGUNTA 1) ---
        # Condición: Consulta a DB (ya hecha en aggregation) + Regla específica
        if variable.lower() == "temperatura" and avg_value > 30.0:
            # Acción: Enviar comando al actuador
            command_msg = "ACTUATOR_COMMAND SET_FAN_ON"
            print(
                f"!!! EVENTO CRÍTICO: Promedio {avg_value}°C. Enviando comando a actuador en {topic}"
            )
            client.publish(topic, command_msg)

    print(
        len(aggregation),
        "dispositivos revisados.",
        alerts,
        "alertas de rango enviadas.",
    )


def on_connect(client, userdata, flags, rc):
    print("Conectado al broker MQTT con código:", mqtt.connack_string(rc))


def on_disconnect(client, userdata, rc):
    print("Desconectado. Intentando reconectar...")
    try:
        client.reconnect()
    except Exception as e:
        print("Error al reconectar:", e)


def setup_mqtt():
    """
    Configura el cliente MQTT global.
    """
    print(
        "Iniciando cliente MQTT en {}:{}".format(settings.MQTT_HOST, settings.MQTT_PORT)
    )
    global client
    try:
        # IMPORTANTE: No volvemos a instanciar el cliente aquí para no perder la versión de la API
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect

        if settings.MQTT_USE_TLS:
            client.tls_set(
                ca_certs=settings.CA_CRT_PATH,
                tls_version=ssl.PROTOCOL_TLSv1_2,
                cert_reqs=ssl.CERT_NONE,
            )

        client.username_pw_set(settings.MQTT_USER_PUB, settings.MQTT_PASSWORD_PUB)
        client.connect(settings.MQTT_HOST, settings.MQTT_PORT)
        client.loop_start()  # Iniciamos el loop para que procese callbacks en segundo plano

    except Exception as e:
        print("Error en la conexión MQTT:", e)


def start_cron():
    """
    Inicia el ciclo de monitoreo.
    """
    print("Iniciando cron cada 5 minutos...")
    schedule.every(5).minutes.do(analyze_data)

    # Ejecutamos una vez al inicio para probar
    analyze_data()

    while True:
        schedule.run_pending()
        time.sleep(1)
