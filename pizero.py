"""
Reading sensor-data and publishing it via MQTT to Raspberry PI 4
Based on publisher.py file provided in the exercise classes
"""

import paho.mqtt.client as mqtt
import logging
import time
from envirophat import analog
from envirophat import light
import traceback

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# MQTT Configuration
MQTT_HOST = "raspberrypizero"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 5

# Define on_connect event Handler
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to MQTT Broker successfully")
    else:
        logging.error(f"Failed to connect, return code {rc}")

# Define on_publish event Handler
def on_publish(client, userdata, mid):
    logging.info("Message Published successfully")

def read_temperature():
    millivolts = analog.read(1) * 1000
    return (millivolts - 500) / 10

def read_moisture():
    return analog.read(0)

def read_light():
    return light.light()

# Initialize MQTT Client
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

# Register Event Handlers
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish

try:
    # Connect to MQTT Broker
    mqttc.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)

    # Start MQTT loop to handle callbacks
    mqttc.loop_start()

    while True:
        light_val = read_light()
        temperature_val = read_temperature()
        moisture_val = read_moisture()
        data = [["light", light_val], ["temperature", temperature_val], ["moisture", moisture_val]]
        for d in data:
            MQTT_TOPIC = "sensor/" + d[0]
            MQTT_MSG = d[1]
            # Ensure Topic and Message are valid before publishing
            if MQTT_TOPIC is not None and MQTT_MSG is not None:
                mqttc.publish(MQTT_TOPIC, MQTT_MSG)
            else:
                logging.warning("MQTT_TOPIC or MQTT_MSG is empty, skipping publish")

        # Give some time for message to be sent before disconnecting
        time.sleep(2.0)
except KeyboardInterrupt:
    mqttc.loop_stop()
    mqttc.disconnect()
    pass
except Exception:
    logging.error(traceback.format_exc())
