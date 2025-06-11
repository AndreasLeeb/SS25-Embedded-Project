"""
Data class to store sensor value thresholds which indicate good/bad plant state
as well as enable/disable automatic pumping
"""

class SensorData:
    def __init__(self, temp=None, light=None, moisture=None, watering_enabled = None,
                 minimum_moisture = None, pumping_time=None):
        self.temp = temp
        self.light = light
        self.moisture = moisture
        self.watering_enabled = watering_enabled
        self.minimum_moisture = minimum_moisture
        self.pumping_time = pumping_time

    def to_dict(self):
        return {
            "temp": self.temp,
            "light": self.light,
            "moisture": self.moisture,
            "watering_enabled": self.watering_enabled,
            "minimum_moisture": self.minimum_moisture,
            "pumping_time": self.pumping_time
        }