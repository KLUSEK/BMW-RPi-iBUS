#!/usr/bin/python

import json
import time
import threading
import mqtt_module.client as MQTT # https://pypi.org/project/paho-mqtt/
									# https://github.com/eclipse/paho.mqtt.python

class MQTTService(object):

	# configuration
	mqtt_client_name = "RPi"
	mqtt_broker = "192.168.2.1"
	mqtt_user = "homeassistant"
	mqtt_passwd = ""
	mqtt_port = 1883
	mqtt_topic = "car/bmw/raspberry"

	def __init__(self):
		self._stop = threading.Event()
		self.connected = False

	def start(self, queue):
		while not self.stopped():
			if not self.connected:
				try:
					self.mqtt = MQTT.Client(self.mqtt_client_name)
					self.mqtt.username_pw_set(self.mqtt_user, password=self.mqtt_passwd)
					self.mqtt.connect(self.mqtt_broker, port=self.mqtt_port)
					self.mqtt.loop_start()

					self.connected = True
				except:
					time.sleep(10)
					continue
			else:
				obc_data = queue.get()
				payload = json.dumps({"mileage": obc_data["mileage"],
									"avg_speed": obc_data["avg_speed"],
									"fuel_consumption_1": obc_data["fuel_1"],
									"fuel_consumption_2": obc_data["fuel_2"],
									"range": obc_data["range"],
									"outside_temp": obc_data["outside"],
									"coolant_temp": obc_data["coolant"],
									"speed_limit": obc_data["limit"]});
				try:
					self.mqtt.publish(self.mqtt_topic, payload=payload, qos=0, retain=False)
				except:
					self.mqtt.reconnect()
					continue

				time.sleep(60)
				continue

		queue.task_done()

	def stop(self):
		self._stop.set()
		self.mqtt.loop_stop(force=False)

	def stopped(self):
		return self._stop.isSet()

	def shutdown(self):
		try:
			self.connected = False
			self.mqtt.disconnect()
		except:
			pass