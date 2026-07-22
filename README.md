<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:00d4ff,100:8b5cf6&height=200&section=header&text=ClassPulse&fontSize=60&fontColor=ffffff&fontAlignY=38&desc=Real-Time%20Classroom%20Attention%20Monitoring%20System&descAlignY=58&descSize=18" width="100%"/>

<br/>

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Pose-FF6B35?style=for-the-badge&logo=yolo&logoColor=white)](https://ultralytics.com)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![ESP32](https://img.shields.io/badge/ESP32-PlatformIO-E7352C?style=for-the-badge&logo=espressif&logoColor=white)](https://platformio.org)
[![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-660066?style=for-the-badge&logo=eclipsemosquitto&logoColor=white)](https://mosquitto.org)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-00d4ff?style=for-the-badge)](LICENSE)

<br/>

> **ClassPulse** is an AI-powered real-time classroom attention monitoring system that uses **YOLOv8 Pose Estimation** to analyze student engagement levels — detecting attentive, distracted, sleeping, and phone-using students — and delivers instant feedback through a **live web dashboard** and **ESP32 IoT hardware alerts**.

<br/>

<img src="https://img.shields.io/badge/status-active-00d4ff?style=flat-square"/>
<img src="https://img.shields.io/badge/models-YOLOv8n--pose%20%7C%20YOLOv8n-8b5cf6?style=flat-square"/>
<img src="https://img.shields.io/badge/IoT-ESP32%20%2B%20RGB%20LED%20%2B%20Buzzer-E7352C?style=flat-square"/>

</div>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Hardware Requirements](#-hardware-requirements)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Configuration](#-configuration)
- [How It Works](#-how-it-works)
- [Dashboard Preview](#-dashboard-preview)
- [MQTT Topics](#-mqtt-topics)
- [ESP32 Behaviour](#-esp32-behaviour)
- [Attention Scoring](#-attention-scoring)
- [Contributing](#-contributing)
- [Author](#-author)

---

## 🎯 Overview

ClassPulse addresses a real problem in modern education — **teachers have no scalable way to know if students are actually paying attention** during a lecture. This system uses a single webcam, AI pose estimation, and IoT hardware to give teachers instant, data-driven attention feedback without any wearables or student-side hardware.

**What makes it different:**

- No special student hardware — just a camera
- Works with any laptop webcam (no GPU required, GPU supported)
- Real-time per-student attention scoring using head pose geometry
- Physical IoT feedback — RGB LED + buzzer on teacher's desk
- Session reports with exportable CSV data

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧠 **YOLOv8 Pose** | 17-point skeleton detection per student |
| 📐 **Head Pose Estimation** | Yaw + pitch angle from facial keypoints |
| 👁️ **Eye State Detection** | Closed-eye streak detection for sleeping |
| 📱 **Phone Detection** | YOLOv8n COCO detects cell phones near students |
| 📊 **Live Dashboard** | Flask + Chart.js with MJPEG stream + SSE updates |
| 🔴 **IoT Alerts** | ESP32 → RGB LED colours + passive buzzer tones |
| 🗄️ **Session Logging** | SQLite stores every scan with timestamps |
| 📄 **Report Generation** | Per-session HTML report + CSV export |
| 📡 **MQTT Integration** | Mosquitto broker bridges Python ↔ ESP32 |
| 🎯 **Persistent Tracking** | YOLOv8 `.track()` gives each student a stable ID |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ClassPulse System                        │
│                                                                 │
│  [Laptop Camera]                                                │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────┐                               │
│  │     detector.py (Thread)    │                               │
│  │  YOLOv8-pose  ──────────── 17 keypoints per student        │
│  │  YOLOv8n      ──────────── phone detection (class 67)      │
│  │  attention.py ──────────── head pose + eye state → score   │
│  └──────────────┬──────────────┘                               │
│                 │                                               │
│          ┌──────┴──────┐                                        │
│          ▼             ▼                                        │
│     database.py    mqtt_handler.py                              │
│     (SQLite)       (Mosquitto)                                  │
│          │             │                                        │
│          └──────┬───────┘                                       │
│                 ▼                                               │
│            app.py (Flask)                                       │
│       ┌─────────────────────┐                                  │
│       │  /video_feed MJPEG  │ ──► Browser Dashboard            │
│       │  /stream  SSE       │ ──► Live Chart.js updates        │
│       │  /report  HTML      │ ──► Session report + CSV         │
│       └─────────────────────┘                                  │
│                 │                                               │
│          MQTT broker                                            │
│                 │                                               │
│          ┌──────▼──────┐                                        │
│          │   ESP32     │                                        │
│          │  RGB LED    │ Green / Blue blink / Red / Purple     │
│          │  Buzzer     │ Tones based on attention level        │
│          └─────────────┘                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

**Python Backend**

| Library | Version | Purpose |
|---|---|---|
| `ultralytics` | ≥8.0 | YOLOv8 pose + object detection |
| `opencv-python` | ≥4.8 | Camera capture + frame annotation |
| `flask` | ≥3.0 | Web server, MJPEG stream, SSE, REST API |
| `paho-mqtt` | ≥1.6 | MQTT publisher to ESP32 |
| `numpy` | ≥1.24 | Keypoint geometry calculations |
| `pandas` | ≥2.0 | Session data processing |
| `torch` | ≥2.0 | YOLOv8 backend (CUDA or CPU) |

**Frontend**

| Tool | Purpose |
|---|---|
| `Chart.js 4.4` | Real-time timeline + donut charts |
| `Vanilla JS` | SSE listener, session controls |
| `CSS Variables` | Dark cyberpunk design system |

**Embedded / IoT**

| Tool | Purpose |
|---|---|
| `ESP32` | WiFi-enabled microcontroller |
| `PlatformIO` | ESP32 build + upload |
| `PubSubClient` | MQTT subscriber on ESP32 |
| `ArduinoJson` | JSON parsing on ESP32 |
| `Mosquitto` | MQTT broker (localhost) |

---

## 🔌 Hardware Requirements

| Component | Qty | Notes |
|---|---|---|
| ESP32 Dev Board | 1 | Any variant |
| RGB LED (4-pin) | 1 | Common Cathode preferred |
| 220Ω Resistors | 3 | One per R/G/B pin |
| Passive Buzzer | 1 | 2-pin, needs PWM signal |
| Breadboard | 1 | Half-size or larger |
| Jumper Wires | ~15 | Male-to-male |
| USB Cable | 1 | For ESP32 power + flashing |
| Laptop + Webcam | 1 | Built-in camera works |

**Wiring — RGB LED (Common Cathode):**

```
ESP32 GPIO 25  →  220Ω  →  LED Red pin   (Pin 1)
ESP32 GPIO 26  →  220Ω  →  LED Green pin (Pin 3)
ESP32 GPIO 27  →  220Ω  →  LED Blue pin  (Pin 4)
LED Common GND (Pin 2, longest leg)  →  GND rail
```

**Wiring — Passive Buzzer:**

```
ESP32 GPIO 18  →  Buzzer + leg
GND rail       →  Buzzer − leg
```

> ⚠️ **How to wire resistors:** GPIO pin → resistor leg 1 → resistor leg 2 → LED colour pin. The resistor sits between the ESP32 and the LED on the breadboard row.

---

## 📁 Project Structure

```
ClassPulse/
│
├── 📄 app.py                         # Flask entry point — run this
├── 📄 detector.py                    # YOLOv8 background detection thread
├── 📄 attention.py                   # Head pose + eye state → attention score
├── 📄 database.py                    # SQLite session & log manager
├── 📄 mqtt_handler.py                # MQTT publisher (stats + alerts)
├── 📄 config.py                      # All settings in one place
├── 📄 requirements.txt
│
├── 📁 templates/
│   ├── index.html                    # Live dashboard UI
│   └── report.html                   # Session report with charts
│
├── 📁 static/
│   ├── css/style.css                 # Dark cyberpunk design system
│   └── js/dashboard.js              # SSE listener + Chart.js updates
│
├── 📁 esp32/
│   └── platformio_project/
│       ├── platformio.ini            # Board config + auto-install libs
│       └── src/main.cpp              # ESP32 firmware (RGB + buzzer)
│
├── 📁 sessions/                      # Auto-created — SQLite DB lives here
├── 📁 reports/                       # Auto-created — exported CSVs
│
├── 📄 .gitignore
└── 📄 README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js (for Node-RED, optional)
- [Mosquitto MQTT Broker](https://mosquitto.org/download/)
- VS Code + PlatformIO extension
- PyCharm Community (recommended for Python)

---

### 1. Clone the Repository

```bash
git clone https://github.com/rafiul254/ClassPulse.git
cd ClassPulse
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

> YOLOv8 models (`yolov8n-pose.pt` and `yolov8n.pt`) download automatically on first run (~20 MB total).

### 3. Configure Mosquitto

Open `C:\Program Files\mosquitto\mosquitto.conf` and add:

```
listener 1883
allow_anonymous true
```

Restart the Mosquitto service.

### 4. Configure the Project

Edit `config.py`:

```python
CAMERA_INDEX = 0          # 0 = built-in laptop camera
DEVICE       = '0'        # '0' = GPU  |  'cpu' = CPU only
MQTT_BROKER  = 'localhost'
```

### 5. Flash the ESP32

Open `esp32/platformio_project/` in VS Code, edit `src/main.cpp`:

```cpp
#define WIFI_SSID      "YourWiFiName"
#define WIFI_PASSWORD  "YourWiFiPassword"
#define MQTT_BROKER    "192.168.X.X"   // your PC's local IP (ipconfig)
```

Then: **✓ Build → → Upload → 🔌 Serial Monitor (115200)**

### 6. Run ClassPulse

```bash
python app.py
```

Open browser: **http://localhost:5000**

---

## ⚙️ Configuration

All settings live in `config.py`:

```python
# Detection tuning
CONF_THRESHOLD      = 0.50   # keypoint confidence gate
YAW_DISTRACTED_DEG  = 25     # head turn angle → DISTRACTED
YAW_AWAY_DEG        = 50     # head turn angle → fully sideways
PITCH_SLEEPING_DEG  = 30     # chin drop angle → SLEEPING
EAR_CLOSED_FRAMES   = 8      # consecutive closed-eye frames → SLEEPING

# Alert thresholds
ATTENTION_THRESHOLD = 60     # class avg below this → alert fires
ALERT_COOLDOWN      = 30     # seconds between repeat alerts
LOG_INTERVAL        = 5      # seconds between SQLite writes
```

---

## 🧠 How It Works

### Attention Scoring Algorithm

Each detected student gets a score from **0 to 100** based on:

```
Step 1 — Camera quality gate
  If best face keypoint confidence < 22% → score 10, state UNCERTAIN

Step 2 — Head yaw (left-right rotation)
  |yaw| < 25°  → +45 pts  (facing camera)
  |yaw| < 50°  → +20 pts  (slightly turned)
  |yaw| ≥ 50°  →  +0 pts  (fully sideways)

Step 3 — Head pitch (up-down tilt)
  pitch < -30° → cap score at 12 (head dropped / sleeping)

Step 4 — Eye state
  Eyes open    → +20 pts
  Eyes closed  → no bonus
  Closed ≥ 8 consecutive frames → cap at 12 (SLEEPING)

Step 5 — Confidence scaling
  avg_face_conf maps [0.35 → 1.0] to scale [0.5 → 1.0]
  Low-light camera = score scaled down automatically

Step 6 — Phone penalty
  Phone detected near person → hard cap score at 25
```

### State Classification

| Score | State | Condition Override |
|---|---|---|
| 65–100 | 🟢 ATTENTIVE | — |
| 30–64 | 🟡 DISTRACTED | or \|yaw\| > 50° |
| 0–29 | 🔴 SLEEPING | or pitch < -30° or eye streak ≥ 8 |
| any | 📱 PHONE | phone detected nearby |
| any | ⚪ UNCERTAIN | camera too dark |

---

## 📊 Dashboard Preview

**Live Dashboard** — `http://localhost:5000`
- Left panel: annotated live camera feed (MJPEG stream)
- Right panel: class attention gauge, per-student rows, breakdown counts
- Bottom: 5-minute attention timeline chart + alert log

**Session Report** — `http://localhost:5000/report/<id>`
- KPI cards: avg attention, data points, time attentive %, time struggling %
- Full timeline chart with alert threshold line
- State distribution donut chart
- Alert log table
- CSV export button

---

## 📡 MQTT Topics

| Topic | Direction | Payload |
|---|---|---|
| `classpulse/stats` | Python → ESP32 | `{"class_attention": 72, "total_students": 5, "attentive": 3, ...}` |
| `classpulse/alert` | Python → ESP32 | `{"level": "danger", "message": "Attention dropped to 28%"}` |

**Test without Python running:**

```bash
# Simulate good attention
mosquitto_pub -h localhost -t "classpulse/stats" -m "{\"class_attention\":85}"

# Simulate danger alert
mosquitto_pub -h localhost -t "classpulse/alert" -m "{\"level\":\"danger\",\"message\":\"Test\"}"
```

---

## 💡 ESP32 Behaviour

| Attention % | RGB LED | Buzzer |
|---|---|---|
| Boot | White sweep → R → G → B | Ascending C-E-G-C melody |
| WiFi connecting | Yellow blink | — |
| MQTT connected | Cyan double flash | Double beep |
| ≥ 70% | 🟢 Solid Green | Silent |
| 45–69% | 🔵 Slow Blue blink | Silent |
| < 45% | 🔴 Solid Red | Single warn beep |
| Alert warning | 💜 Purple flash ×2 | Double warn beep |
| Alert danger | 💜 Purple flash ×4 | Triple alarm |

---

## 🔧 Troubleshooting

| Problem | Fix |
|---|---|
| Camera not found | Change `CAMERA_INDEX = 1` in `config.py` |
| YOLO too slow | Set `DEVICE = 'cpu'` or use `yolov8n-pose` (already nano) |
| MQTT not connecting | Check Mosquitto is running, verify broker IP |
| ESP32 won't connect to WiFi | Ensure 2.4 GHz network (ESP32 doesn't support 5 GHz) |
| Score always high (dark room) | Lower `MIN_FACE_CONF = 0.35` in `attention.py` |
| Too many false SLEEPING | Increase `EAR_CLOSED_FRAMES = 12` in `attention.py` |
| RGB LED wrong colour | Check Common Cathode vs Anode — swap logic if needed |

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first.

```bash
git checkout -b feature/your-feature
git commit -m "feat: add your feature"
git push origin feature/your-feature
```

---

## 👨‍💻 Author

<div align="center">

**Rafiul Islam**

B.Sc. in IoT & Robotics Engineering — University of Frontier Technology, Bangladesh


[![YouTube](https://img.shields.io/badge/@PinToCloud-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://youtube.com/@PinToCloud)
[![GitHub](https://img.shields.io/badge/rafiul254-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/rafiul254)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/rafiul-islam-25sep92004)

</div>

---

<div align="center">

**Built with 💜 using YOLOv8 + OpenCv + Flask + ESP32**

*If this project helped you, consider giving it a ⭐*

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:8b5cf6,100:00d4ff&height=100&section=footer" width="100%"/>

</div>
