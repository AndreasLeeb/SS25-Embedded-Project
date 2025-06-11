"""
Receiving sensor data from the PI zero and starting motors / pump accordingly
Based on subscriber.py provided in the exercise classes
"""

import paho.mqtt.client as mqtt
import logging
import board
import time
import json
import traceback
import threading
import queue
import RPi.GPIO as GPIO
from gpiozero import LED
from adafruit_servokit import ServoKit

import publisher
from SensorData import SensorData

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# MQTT Configuration
MQTT_HOST = "raspberrypizero"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 5
# sensor topics: for receiving sensor data from PI Zero
# actor topics: to activate / deactivate pump and shading
# config topics: sending config data to web interface or receiving it
MQTT_TOPIC = ["sensor/light", "sensor/temperature", "sensor/moisture",
              "actor/shade", "actor/pump",
              "config/plantHealth/temperatureLowerBound/get", "config/plantHealth/temperatureLowerBound/set",
              "config/plantHealth/temperatureUpperBound/get", "config/plantHealth/temperatureUpperBound/set",
              "config/plantHealth/moistureLowerBound/get", "config/plantHealth/moistureLowerBound/set",
              "config/plantHealth/moistureUpperBound/get", "config/plantHealth/moistureUpperBound/set",
              "config/plantHealth/lightLowerBound/get", "config/plantHealth/lightLowerBound/set",
              "config/plantHealth/lightUpperBound/get", "config/plantHealth/lightUpperBound/set",
              "config/watering/enabled/get", "config/watering/enabled/set",
              "config/watering/minimumMoisture/get", "config/watering/minimumMoisture/set",
              "config/watering/pumpingTime/get", "config/watering/pumpingTime/set", ]
SUBSCRIBED_TOPICS = {}
TEMP_RANGE = [18, 25]
red_led = LED(27)
green_led = LED(6)
kit = ServoKit(channels=16)

# dictionary to keep track of plant state
plant_state = {
    "temp": True,
    "moisture": True
}

publishing_queue = queue.SimpleQueue() # thread save
watering_timeout = False
loaded_data = {}
json_filename = 'sensor_data.json'

# loading sensor data bounds from json file
try:
    with open(json_filename, 'r') as f:
        loaded_data = json.load(f)
    print(f"Successfully loaded data from {json_filename}: {loaded_data}")
except FileNotFoundError:
    print(f"Error: The file '{json_filename}' was not found.")
except json.JSONDecodeError as e:
    print(f"Error decoding JSON from {json_filename}: {e}")
except IOError as e:
    print(f"Error reading file {json_filename}: {e}")

sensor_data = SensorData(**loaded_data)


# Define on_connect event Handler
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to MQTT Broker successfully")
        if MQTT_TOPIC:
            for t in MQTT_TOPIC:
                mid = 1
                if len(SUBSCRIBED_TOPICS) > 0:
                    mid = max(list(SUBSCRIBED_TOPICS.keys())) + 1
                SUBSCRIBED_TOPICS[mid] = t
                client.subscribe(t, qos=0)
        else:
            logging.warning("MQTT_TOPIC is empty. Subscription skipped.")
    else:
        logging.error(f"Failed to connect, return code {rc}")


# Define on_subscribe event Handler
def on_subscribe(client, userdata, mid, granted_qos):
    logging.info(f"SUBACK received for MID: {mid}, subscribed to topic {SUBSCRIBED_TOPICS[mid]}")


# Define on_publish event Handler
def on_publish(client, userdata, mid):
    logging.info("Message Published successfully")


# Define on_message event Handler
def on_message(client, userdata, msg):
    global watering_timeout
    print(f"Received Message: {msg.payload.decode()} from Topic: {msg.topic}")
    data = msg.payload.decode()
    topic = msg.topic
    # update plant state and activate pump based on sensor data
    if "sensor" in topic:
        if "temperature" in topic:
            plant_state["temp"] = sensor_data.temp[0] <= float(data) <= sensor_data.temp[1]
        elif "moisture" in topic:
            plant_state["moisture"] = sensor_data.moisture[0] <= float(data) <= sensor_data.moisture[1]
            if sensor_data.watering_enabled and float(data) < sensor_data.minimum_moisture and not watering_timeout:
                start_pump()
                watering_timeout = True
        update_plant_state()
    elif topic == "actor/shade":
        if data == "0":
            unshade()
        else:
            shade()
    elif topic == "actor/pump":
        seconds = float(data)
        start_pump(seconds)
    elif "config" in topic:
        if "set" in topic:
            if "temperatureLowerBound" in topic:
                sensor_data.temp[0] = float(data)
            elif "temperatureUpperBound" in topic:
                sensor_data.temp[1] = float(data)
            elif "moistureLowerBound" in topic:
                sensor_data.moisture[0] = float(data)
            elif "moistureUpperBound" in topic:
                sensor_data.moisture[1] = float(data)
            elif "lightLowerBound" in topic:
                sensor_data.light[0] = float(data)
            elif "lightUpperBound" in topic:
                sensor_data.light[1] = float(data)
            elif "watering/enabled" in topic:
                sensor_data.watering_enabled = True if data == 'True' else False
            elif "watering/minimumMoisture" in topic:
                sensor_data.minimum_moisture = float(data)
            elif "watering/pumpingTime" in topic:
                sensor_data.pumping_time = float(data)
            update_sensor_data()
        else:
            msg = None
            if "temperatureLowerBound" in topic:
                msg = sensor_data.temp[0]
            elif "temperatureUpperBound" in topic:
                msg = sensor_data.temp[1]
            elif "moistureLowerBound" in topic:
                msg = sensor_data.moisture[0]
            elif "moistureUpperBound" in topic:
                msg = sensor_data.moisture[1]
            elif "lightLowerBound" in topic:
                msg = sensor_data.light[0]
            elif "lightUpperBound" in topic:
                msg = sensor_data.light[1]
            elif "watering/enabled" in topic:
                msg = sensor_data.watering_enabled
            elif "watering/minimumMoisture" in topic:
                msg = sensor_data.minimum_moisture
            elif "watering/pumpingTime" in topic:
                msg = sensor_data.pumping_time
            topic = topic[:-4]
            send_data(topic, msg)

# update LEDs indicating plant state
def update_plant_state():
    if plant_state["temp"] and plant_state["moisture"]:
        red_led.off()
        green_led.on()
    else:
        green_led.off()
        red_led.on()

# add data to publish to queue, this activates the loop in the publisher thread
def send_data(topic, msg):
    if topic is not None and msg is not None:
        publishing_queue.put({"topic": topic, "msg": msg})
    else:
        logging.warning("MQTT_TOPIC or MQTT_MSG is empty, skipping publish")

# rotate motor such that cardboard covers plant
def shade():
    kit.continuous_servo[0].throttle = 0.9
    time.sleep(0.5)
    kit.continuous_servo[0].throttle = 0.1

# reset motor to original position
def unshade():
    kit.continuous_servo[0].throttle = -0.3
    time.sleep(0.5)
    kit.continuous_servo[0].throttle = 0.1

# starts the water pump for the specified amount of time in seconds
def start_pump(seconds=sensor_data.pumping_time):
    ctrl = 26
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(ctrl, GPIO.OUT)
    GPIO.output(ctrl, GPIO.HIGH)
    time.sleep(seconds)
    GPIO.output(ctrl, GPIO.LOW)
    GPIO.cleanup()

# Serialize new sensor thresholds and other states to json file
def update_sensor_data():
    try:
        with open(json_filename, 'w') as f:
            json.dump(sensor_data.to_dict(), f, indent=4)  # indent for pretty printing
        print(f"SensorData successfully serialized to {json_filename}")
    except IOError as e:
        print(f"Error writing to file {json_filename}: {e}")


# Initialize MQTT Client
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
update_plant_state()


# Function to be run in a separate thread for publishing
def publisher_thread_function():
    global mqttc

    print("Publisher thread started...")
    while True:
        item = publishing_queue.get()
        topic = item["topic"]
        msg = item["msg"]
        try:
            # client.publish() is thread-safe
            result, mid = mqttc.publish(topic, msg)
            if result == mqtt.MQTT_ERR_SUCCESS:
                print(f"Publisher thread: Published '{msg}' to topic '{topic}' with mid {mid}")
            else:
                print(f"Publisher thread: Error publishing message: {result}")
        except Exception as e:
            print(f"Publisher thread: An error occurred during publish: {e}")


# Register Event Handlers
mqttc.on_connect = on_connect
mqttc.on_subscribe = on_subscribe
mqttc.on_message = on_message
mqttc.on_publish = on_publish

try:
    # Connect to MQTT Broker
    mqttc.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)

    publisher_thread = threading.Thread(target=publisher_thread_function)
    publisher_thread.daemon = True
    publisher_thread.start()
    print("Publisher thread initiated.")

    # Start the network loop
    mqttc.loop_forever()

except KeyboardInterrupt:
    print("KeyboardInterrupt detected. Stopping application.")
except Exception:
    traceback.print_exc()
finally:
    # Signal the publisher thread to stop
    publisher_thread.join(timeout=5)  # Wait for the publisher thread to finish
    if publisher_thread.is_alive():
        print("Warning: Publisher thread did not terminate gracefully.")
    mqttc.disconnect()  # Disconnect from the broker
    print("Disconnected from MQTT broker.")
