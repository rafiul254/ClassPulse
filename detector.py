import cv2
import time
import threading
import numpy as np
from collections import deque
from datetime import datetime
from ultralytics import YOLO

from attention import AttentionEngine
from config import (
    CAMERA_INDEX, POSE_MODEL, OBJ_MODEL, DEVICE,
    YOLO_CONF, ATTENTION_THRESHOLD, ALERT_COOLDOWN,
    LOG_INTERVAL, TIMELINE_MAXLEN, STREAM_FPS_CAP,
)


class Detector:

    def __init__(self):
        print('[ClassPulse] Loading YOLOv8 models...')
        self.pose_model = YOLO(POSE_MODEL)
        self.obj_model  = YOLO(OBJ_MODEL)
        print(f'[ClassPulse] Models ready  |  Device: {DEVICE}')

        self.engine = AttentionEngine()
        self.cap    = None

        self._lock    = threading.Lock()
        self._running = False
        self._thread  = None

        self._db   = None
        self._mqtt = None

        self._session_id  = None
        self._last_log_t  = 0.0
        self._last_alert_t = 0.0

        self._frame     = None
        self._blank     = self._make_blank()
        self._timeline  = deque(maxlen=TIMELINE_MAXLEN)
        self._alerts    = deque(maxlen=20)
        self._stats: dict = self._empty_stats()

    @staticmethod
    def _make_blank() -> np.ndarray:
        img = np.zeros((480, 640, 3), np.uint8)
        cv2.putText(img, 'ClassPulse — Starting...', (120, 230),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 215, 255), 2, cv2.LINE_AA)
        cv2.putText(img, 'Point camera at the classroom', (130, 270),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 100, 140), 1, cv2.LINE_AA)
        return img

    @staticmethod
    def _empty_stats() -> dict:
        return {
            'students':         [],
            'class_attention':  0,
            'total_students':   0,
            'attentive_count':  0,
            'distracted_count': 0,
            'sleeping_count':   0,
            'phone_count':      0,
            'alerts':           [],
            'timeline':         [],
            'fps':              0.0,
            'session_active':   False,
            'mqtt_connected':   False,
        }

    def set_db(self, db):
        self._db = db

    def set_mqtt(self, mqtt_pub):
        self._mqtt = mqtt_pub

    def set_session(self, session_id):
        with self._lock:
            self._session_id = session_id
            self._timeline.clear()
            self._alerts.clear()
            self._last_log_t   = 0.0
            self._last_alert_t = 0.0
        print(f'[ClassPulse] Session → {session_id}')

    def get_session_id(self):
        with self._lock:
            return self._session_id

    def start(self):
        self.cap = cv2.VideoCapture(CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print('[ClassPulse] Detection thread started')

    def stop(self):
        self._running = False
        if self.cap:
            self.cap.release()
        print('[ClassPulse] Detection thread stopped')


    def _loop(self):
        prev_t = time.time()

        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            try:
                pose_res = self.pose_model.track(
                    frame,
                    persist=True,
                    verbose=False,
                    device=DEVICE,
                    conf=YOLO_CONF,
                )
                obj_res = self.obj_model(
                    frame,
                    verbose=False,
                    device=DEVICE,
                    classes=[67],
                    conf=0.40,
                )
            except Exception as e:
                print(f'[YOLO] Error: {e}')
                time.sleep(0.1)
                continue


            students, annotated = self.engine.process(frame, pose_res, obj_res)

            n          = len(students)
            attentive  = sum(1 for s in students if s['state'] == 'ATTENTIVE')
            distracted = sum(1 for s in students if s['state'] == 'DISTRACTED')
            sleeping   = sum(1 for s in students if s['state'] == 'SLEEPING')
            phones     = sum(1 for s in students if s['state'] == 'PHONE')
            class_attn = int(np.mean([s['score'] for s in students])) if students else 0

            now_t = time.time()
            fps   = round(1.0 / max(now_t - prev_t, 1e-6), 1)
            prev_t = now_t

            self._timeline.append({
                'time':      datetime.now().strftime('%H:%M:%S'),
                'attention': class_attn,
            })

            if n > 0 and class_attn < ATTENTION_THRESHOLD:
                if now_t - self._last_alert_t > ALERT_COOLDOWN:
                    level = 'danger' if class_attn < 35 else 'warning'
                    msg   = (f'Class attention dropped to {class_attn}% — '
                             f'{sleeping} sleeping, {distracted} distracted, '
                             f'{phones} on phone')
                    self._alerts.appendleft({
                        'time':    datetime.now().strftime('%H:%M:%S'),
                        'message': msg,
                        'level':   level,
                    })
                    self._last_alert_t = now_t

                    if self._db and self._session_id:
                        self._db.log_alert(self._session_id, msg, level)
                    if self._mqtt:
                        self._mqtt.publish_alert(msg, level)

            if now_t - self._last_log_t >= LOG_INTERVAL:
                current_stats = {
                    'total_students':   n,
                    'attentive_count':  attentive,
                    'distracted_count': distracted,
                    'sleeping_count':   sleeping,
                    'phone_count':      phones,
                    'class_attention':  class_attn,
                }
                if self._db and self._session_id:
                    self._db.log_stats(self._session_id, current_stats)
                if self._mqtt:
                    self._mqtt.publish_stats(current_stats)
                self._last_log_t = now_t

            with self._lock:
                self._frame = annotated
                self._stats = {
                    'students':         students,
                    'class_attention':  class_attn,
                    'total_students':   n,
                    'attentive_count':  attentive,
                    'distracted_count': distracted,
                    'sleeping_count':   sleeping,
                    'phone_count':      phones,
                    'alerts':           list(self._alerts),
                    'timeline':         list(self._timeline)[-30:],
                    'fps':              fps,
                    'session_active':   self._session_id is not None,
                    'mqtt_connected':   self._mqtt.connected if self._mqtt else False,
                }

    def get_stats(self) -> dict:
        with self._lock:
            return dict(self._stats)

    def gen_frames(self):

        while True:
            with self._lock:
                frame = (self._frame.copy()
                         if self._frame is not None
                         else self._blank.copy())

            ok, buf = cv2.imencode(
                '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75]
            )
            if ok:
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n'
                    + buf.tobytes()
                    + b'\r\n'
                )
            time.sleep(STREAM_FPS_CAP)
