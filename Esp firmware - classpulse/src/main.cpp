#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#define WIFI_SSID      "YOUR_WIFI_SSID"
#define WIFI_PASSWORD  "YOUR_WIFI_PASSWORD"
#define MQTT_BROKER    "192.168.X.X" 
#define MQTT_PORT      1883


#define DEVICE_ID      "ESP32_ClassPulse"
#define TOPIC_STATS    "classpulse/stats"
#define TOPIC_ALERT    "classpulse/alert"

const int PIN_RED    = 25;
const int PIN_GREEN  = 26;
const int PIN_BLUE   = 27;
const int PIN_BUZZER = 18;


const int CH_RED    = 0;
const int CH_GREEN  = 1;
const int CH_BLUE   = 2;
const int CH_BUZZER = 3;

const int PWM_FREQ  = 5000;   
const int PWM_RES   = 8;     
const int BUZZ_RES  = 10;    

int           lastAttention  = -1;
bool          blinkState     = false;
unsigned long lastBlink      = 0;
const int     BLINK_MS       = 700;   

WiFiClient   espClient;
PubSubClient mqttClient(espClient);


void setRGB(int r, int g, int b) {
    ledcWrite(CH_RED,   r);
    ledcWrite(CH_GREEN, g);
    ledcWrite(CH_BLUE,  b);
}

void rgbOff()    { setRGB(0,   0,   0);   }
void rgbGreen()  { setRGB(0,   255, 0);   }
void rgbRed()    { setRGB(255, 0,   0);   }
void rgbBlue()   { setRGB(0,   0,   255); }
void rgbPurple() { setRGB(180, 0,   200); }
void rgbYellow() { setRGB(255, 160, 0);   }
void rgbWhite()  { setRGB(255, 255, 255); }
void rgbCyan()   { setRGB(0,   255, 200); }


void buzzTone(int freq, int durationMs) {
    ledcWriteTone(CH_BUZZER, freq);
    delay(durationMs);
    ledcWriteTone(CH_BUZZER, 0);
}

void buzzOff() {
    ledcWriteTone(CH_BUZZER, 0);
}

void beepGood() {
    buzzTone(1200, 80);
    delay(40);
    buzzTone(1600, 80);
}

void beepWarn() {
    buzzTone(700, 150);
}

void beepAlarm() {
    for (int i = 0; i < 3; i++) {
        buzzTone(400, 200);
        delay(80);
    }
}

void bootMelody() {
    int notes[] = {523, 659, 784, 1047};  // C5 E5 G5 C6
    for (int n : notes) {
        buzzTone(n, 100);
        delay(40);
    }
}


void bootAnimation() {
  
    for (int i = 0; i <= 255; i += 15) {
        setRGB(i, i, i);
        delay(15);
    }
    delay(150);
   
    for (int x : {0, 1, 2}) {
        int r = (x==0)?255:0, g = (x==1)?255:0, b = (x==2)?255:0;
        setRGB(r, g, b);
        delay(200);
    }
    rgbOff();
    delay(100);
}

void flashAlert(const char* level) {
    bool isDanger = (strcmp(level, "danger") == 0);
    int  flashes  = isDanger ? 4 : 2;

    for (int i = 0; i < flashes; i++) {
        rgbPurple();
        delay(120);
        rgbOff();
        delay(80);
    }
    if (isDanger) {
        beepAlarm();
    } else {
        beepWarn();
        delay(50);
        beepWarn();
    }
}


void applyAttention(int attn) {
   
    lastAttention = attn;

    Serial.printf("[ATTN] %d%%\n", attn);

    if (attn >= 70) {
        rgbGreen();
        buzzOff();
        Serial.println("[LED] GREEN — Attentive ✓");

    } else if (attn >= 45) {
       
        Serial.println("[LED] BLUE BLINK — Drifting ⚡");

    } else {
        rgbRed();
        beepWarn();
        Serial.println("[LED] RED — Low attention ✗");
    }
}


void mqttCallback(char* topic, byte* payload, unsigned int len) {
    char msg[len + 1];
    memcpy(msg, payload, len);
    msg[len] = '\0';

    StaticJsonDocument<256> doc;
    if (deserializeJson(doc, msg) != DeserializationError::Ok) {
        Serial.println("[JSON] Parse error");
        return;
    }

    if (strcmp(topic, TOPIC_STATS) == 0) {
        int attn = doc["class_attention"] | -1;
        if (attn >= 0) applyAttention(attn);

    } else if (strcmp(topic, TOPIC_ALERT) == 0) {
        const char* level = doc["level"]   | "warning";
        const char* text  = doc["message"] | "";
        Serial.printf("[ALERT] %s — %s\n", level, text);
        flashAlert(level);
     
        if (lastAttention >= 0) applyAttention(lastAttention);
    }
}

void setupWiFi() {
    rgbYellow();  
    Serial.printf("[WiFi] Connecting to '%s' ", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 40) {
        delay(500);
        Serial.print('.');
        attempts++;
      
        if (attempts % 2 == 0) rgbYellow(); else rgbOff();
    }

    if (WiFi.status() == WL_CONNECTED) {
        rgbCyan();
        Serial.printf("\n[WiFi] ✓ IP: %s\n",
                      WiFi.localIP().toString().c_str());
        buzzTone(1000, 100);
    } else {
        rgbRed();
        Serial.println("\n[WiFi] ✗ Failed — restarting");
        delay(2000);
        ESP.restart();
    }
}

void reconnectMQTT() {
    while (!mqttClient.connected()) {
        rgbYellow();
        Serial.printf("[MQTT] Connecting to %s ... ", MQTT_BROKER);

        if (mqttClient.connect(DEVICE_ID)) {
            Serial.println("OK ✓");
            mqttClient.subscribe(TOPIC_STATS);
            mqttClient.subscribe(TOPIC_ALERT);
         
            rgbCyan(); delay(200); rgbOff(); delay(100);
            rgbCyan(); delay(200); rgbGreen();
            buzzTone(1200, 80); delay(50); buzzTone(1500, 80);
        } else {
            rgbRed();
            Serial.printf("failed (rc=%d) — retry in 5s\n",
                          mqttClient.state());
            delay(5000);
        }
    }
}


void setup() {
    Serial.begin(115200);
    delay(300);

    ledcSetup(CH_RED,    PWM_FREQ, PWM_RES);
    ledcSetup(CH_GREEN,  PWM_FREQ, PWM_RES);
    ledcSetup(CH_BLUE,   PWM_FREQ, PWM_RES);
    ledcSetup(CH_BUZZER, 2000,     BUZZ_RES);

    ledcAttachPin(PIN_RED,    CH_RED);
    ledcAttachPin(PIN_GREEN,  CH_GREEN);
    ledcAttachPin(PIN_BLUE,   CH_BLUE);
    ledcAttachPin(PIN_BUZZER, CH_BUZZER);

    rgbOff();
    buzzOff();

    Serial.println();
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║   ClassPulse                              ║");
    Serial.println("╚═══════════════════════════════════════════╝");

    bootAnimation();
    bootMelody();

    setupWiFi();

    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
    mqttClient.setKeepAlive(60);

    Serial.println("[BOOT] Ready — subscribed to classpulse/#");
    rgbGreen();
}

void loop() {
    if (!mqttClient.connected()) {
        reconnectMQTT();
    }
    mqttClient.loop();

    if (lastAttention >= 45 && lastAttention < 70) {
        unsigned long now = millis();
        if (now - lastBlink >= BLINK_MS) {
            blinkState = !blinkState;
            blinkState ? rgbBlue() : rgbOff();
            lastBlink  = now;
        }
    }
}
