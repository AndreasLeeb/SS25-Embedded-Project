from flask import Flask, render_template, request, jsonify
from flask_bootstrap import Bootstrap
from flask_mqtt import Mqtt
from paho.mqtt.client import MQTT_ERR_SUCCESS

from SensorData import *
from ConfigData import *

TOPIC_MOISTURE = 'sensor/moisture'
TOPIC_TEMPERATURE = 'sensor/temperature'
TOPIC_LIGHT = 'sensor/light'

TOPIC_ACTOR_SHADE = 'actor/shade'
TOPIC_ACTOR_PUMP = 'actor/pump'

TOPIC_WATERING_ENABLED = 'config/watering/enabled'
TOPIC_WATERING_MIN_MOIST = 'config/watering/minimumMoisture'
TOPIC_WATERING_PUMP_TIME  = 'config/watering/pumpingTime'
TOPIC_HEALTH_MIN_TEMP = 'config/plantHealth/temperatureLowerBound'
TOPIC_HEALTH_MAX_TEMP = 'config/plantHealth/temperatureUpperBound'
TOPIC_HEALTH_MIN_MOIST = 'config/plantHealth/moistureLowerBound'
TOPIC_HEALTH_MAX_MOIST = 'config/plantHealth/moistureUpperBound'
GET_CONFIG = '/get'
SET_CONFIG = '/set'
CONFIG_TOPICS = [TOPIC_WATERING_ENABLED, TOPIC_WATERING_MIN_MOIST, TOPIC_WATERING_PUMP_TIME, TOPIC_HEALTH_MIN_TEMP, TOPIC_HEALTH_MAX_TEMP, TOPIC_HEALTH_MIN_MOIST, TOPIC_HEALTH_MAX_MOIST]
CONFIG_TOPIC_MAPPING = {
    "wateringEnabled": TOPIC_WATERING_ENABLED,
    "wateringMinimumMoisture": TOPIC_WATERING_MIN_MOIST,
    "wateringPumpingTime": TOPIC_WATERING_PUMP_TIME,
    "plantHealthMinimumTemperature": TOPIC_HEALTH_MIN_TEMP,
    "plantHealthMaximumTemperature": TOPIC_HEALTH_MAX_TEMP,
    "plantHealthMinimumMoisture": TOPIC_HEALTH_MIN_MOIST,
    "plantHealthMaximumMoisture": TOPIC_HEALTH_MAX_MOIST
}

app = Flask(__name__)
Bootstrap(app)
app.config['MQTT_BROKER_URL'] = 'raspberrypizero.local'
#app.config['MQTT_BROKER_URL'] = 'localhost'
app.config['MQTT_BROKER_PORT'] = 1883  # default port for non-tls connection
app.config['MQTT_USERNAME'] = ''  # set the username here if you need authentication for the broker
app.config['MQTT_PASSWORD'] = ''  # set the password here if the broker demands authentication
app.config['MQTT_KEEPALIVE'] = 5  # set the time interval for sending a ping to the broker to 5 seconds
app.config['MQTT_TLS_ENABLED'] = False  # set TLS to disabled for testing purposes
mqtt = Mqtt(app)

sensor_data = SensorData()
config_data = ConfigData()
shade_state = False


@app.route('/')
def view():  # put application's code here
    return render_template('view.html')

@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    print('connected to MQTT broker')
    mqtt.subscribe(TOPIC_MOISTURE)
    mqtt.subscribe(TOPIC_TEMPERATURE)
    mqtt.subscribe(TOPIC_LIGHT)
    for topic in CONFIG_TOPICS:
        mqtt.subscribe(topic)
    fetch_config_data()

def fetch_config_data():
    print(CONFIG_TOPICS)
    for topic in CONFIG_TOPICS:
        print(topic + GET_CONFIG)
        mqtt.publish(topic + GET_CONFIG)

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    print('topic', message.topic, message.payload.decode())
    if message.topic == TOPIC_MOISTURE:
        sensor_data.moisture = float(message.payload.decode())
    elif message.topic == TOPIC_TEMPERATURE:
        sensor_data.temperature = float(message.payload.decode())
    elif message.topic == TOPIC_LIGHT:
        sensor_data.light = float(message.payload.decode())
    elif message.topic == TOPIC_WATERING_ENABLED:
        config_data.wateringEnabled = message.payload.decode() == '1'
    elif message.topic == TOPIC_WATERING_MIN_MOIST:
        config_data.wateringMinimumMoisture = float(message.payload.decode())
    elif message.topic == TOPIC_WATERING_PUMP_TIME:
        config_data.wateringPumpingTime = float(message.payload.decode())
    elif message.topic == TOPIC_HEALTH_MIN_TEMP:
        config_data.plantHealthMinimumTemperature = float(message.payload.decode())
    elif message.topic == TOPIC_HEALTH_MAX_TEMP:
        config_data.plantHealthMaximumTemperature = float(message.payload.decode())
    elif message.topic == TOPIC_HEALTH_MIN_MOIST:
        config_data.plantHealthMinimumMoisture = float(message.payload.decode())
    elif message.topic == TOPIC_HEALTH_MAX_MOIST:
        config_data.plantHealthMaximumMoisture = float(message.payload.decode())

@app.route('/api/sensorData')
def sensor_data():
    return sensor_data.__dict__

@app.route('/api/configData', methods=['GET'])
def get_config_data():
    print(config_data.__dict__)
    return config_data.__dict__

@app.route('/api/configData', methods=['PATCH'])
def update_config_data():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    for key, value in data.items():
        if hasattr(config_data, key):
            setattr(config_data, key, value)
            mqtt.publish(CONFIG_TOPIC_MAPPING[key] + SET_CONFIG, value)
        else:
            return jsonify({"error": f"Invalid field: {key}"}), 400
    return config_data.__dict__

@app.route('/api/shade', methods=['POST'])
def trigger_shade():
    global shade_state
    print('shading' if not shade_state else 'unshading')
    new_state = '1' if not shade_state else '0'
    (status, _) = mqtt.publish(TOPIC_ACTOR_SHADE, new_state)
    if status == MQTT_ERR_SUCCESS:
        shade_state = not shade_state
        return new_state
    else:
        return None

@app.route('/api/manualPump', methods=['POST'])
def trigger_pump():
    print("pump for", config_data.wateringPumpingTime)
    mqtt.publish(TOPIC_ACTOR_PUMP, config_data.wateringPumpingTime)
    return ""

if __name__ == '__main__':
    app.run()
