import torch

CAMERA_INDEX = 0

POSE_MODEL = 'yolov8n-pose.pt'
OBJ_MODEL  = 'yolov8n.pt'

DEVICE = '0' if torch.cuda.is_available() else 'cpu'

CONF_THRESHOLD      = 0.45
YOLO_CONF           = 0.35
BRIDGE_COUNT_THRESH = 4
ATTENTION_THRESHOLD = 60
ALERT_COOLDOWN      = 30
LOG_INTERVAL        = 5
TIMELINE_MAXLEN     = 60
STREAM_FPS_CAP      = 0.033

MQTT_BROKER   = 'localhost'
MQTT_PORT     = 1883
TOPIC_STATS   = 'classpulse/stats'
TOPIC_ALERT   = 'classpulse/alert'

FLASK_HOST  = '0.0.0.0'
FLASK_PORT  = 5000
SECRET_KEY  = 'classpulse-secret-2024'

COLORS = {
    'ATTENTIVE':  (57,  255,  20),
    'DISTRACTED': (0,   215, 255),
    'SLEEPING':   (0,    50, 255),
    'PHONE':      (20,   80, 255),
}
