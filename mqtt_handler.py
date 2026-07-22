import json
import paho.mqtt.client as mqtt
from config import MQTT_BROKER, MQTT_PORT, TOPIC_STATS, TOPIC_ALERT


class MQTTPublisher:

    def __init__(self):
        self._client    = mqtt.Client()
        self._connected = False
        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):
        self._connected = (rc == 0)
        if rc == 0:
            print('[MQTT] ✓ Connected to broker')
        else:
            print(f'[MQTT] ✗ Connection failed (rc={rc})')

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        if rc != 0:
            print('[MQTT] Disconnected unexpectedly')

    def connect(self):
        try:
            self._client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            self._client.loop_start()
        except Exception as e:
            print(f'[MQTT] Could not connect: {e}  (running without MQTT)')

    def disconnect(self):
        self._client.loop_stop()
        self._client.disconnect()

    @property
    def connected(self) -> bool:
        return self._connected

    def publish_stats(self, stats: dict):
        if not self._connected:
            return
        payload = {
            'class_attention': stats.get('class_attention',  0),
            'total_students':  stats.get('total_students',   0),
            'attentive':       stats.get('attentive_count',  0),
            'distracted':      stats.get('distracted_count', 0),
            'sleeping':        stats.get('sleeping_count',   0),
            'phone':           stats.get('phone_count',      0),
        }
        self._client.publish(TOPIC_STATS, json.dumps(payload), qos=0)

    def publish_alert(self, message: str, level: str = 'warning'):
        if not self._connected:
            return
        self._client.publish(TOPIC_ALERT, json.dumps({
            'message': message,
            'level':   level,
        }), qos=1)
