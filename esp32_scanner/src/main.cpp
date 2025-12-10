#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <NimBLEDevice.h>
#include <ArduinoJson.h>
#include <vector>

#if ENABLE_OTA
#include <ArduinoOTA.h>
#endif

#include "config.h"

// Structure to store BLE observation
struct Observation {
    String mac;
    int rssi;
    unsigned long timestamp;
};

// Global variables
std::vector<Observation> observations;
bool stationRegistered = false;
unsigned long lastUpload = 0;
NimBLEScan* pBLEScan;

// LED control
void setLED(bool state) {
    #if LED_ENABLED
    digitalWrite(LED_PIN, state ? HIGH : LOW);
    #endif
}

void blinkLED(int times, int delayMs = 100) {
    #if LED_ENABLED
    for (int i = 0; i < times; i++) {
        digitalWrite(LED_PIN, HIGH);
        delay(delayMs);
        digitalWrite(LED_PIN, LOW);
        delay(delayMs);
    }
    #endif
}

// WiFi connection
bool connectWiFi() {
    Serial.println("[WiFi] Connecting to " + String(WIFI_SSID));
    
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    unsigned long startTime = millis();
    while (WiFi.status() != WL_CONNECTED) {
        if (millis() - startTime > WIFI_TIMEOUT) {
            Serial.println("[WiFi] Connection timeout!");
            return false;
        }
        
        // Blink LED while connecting
        blinkLED(1, 250);
        delay(250);
    }
    
    Serial.println("[WiFi] Connected!");
    Serial.println("[WiFi] IP address: " + WiFi.localIP().toString());
    setLED(true);
    return true;
}

// Register station with BeaconBoard server
bool registerStation() {
    if (!WiFi.isConnected()) {
        Serial.println("[HTTP] WiFi not connected");
        return false;
    }
    
    HTTPClient http;
    String url = String(SERVER_URL) + "/api/v1/station/register";
    
    Serial.println("[HTTP] Registering station at " + url);
    
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-Key", API_KEY);  // Add API key authentication
    http.setTimeout(HTTP_TIMEOUT);
    
    // Create JSON payload
    StaticJsonDocument<256> doc;
    doc["station_uuid"] = STATION_UUID;  // Fixed: was 'uuid', should be 'station_uuid'
    doc["name"] = STATION_NAME;
    doc["description"] = STATION_DESCRIPTION;
    
    String payload;
    serializeJson(doc, payload);
    
    int retries = 0;
    while (retries < MAX_RETRIES) {
        int httpCode = http.POST(payload);
        
        if (httpCode == 200 || httpCode == 201) {
            Serial.println("[HTTP] Station registered successfully");
            http.end();
            blinkLED(3, 100);
            return true;
        } else if (httpCode > 0) {
            Serial.printf("[HTTP] Registration failed, code: %d\n", httpCode);
            String response = http.getString();
            Serial.println("[HTTP] Response: " + response);
        } else {
            Serial.printf("[HTTP] Connection failed: %s\n", http.errorToString(httpCode).c_str());
        }
        
        retries++;
        if (retries < MAX_RETRIES) {
            Serial.printf("[HTTP] Retrying in %d seconds...\n", RETRY_DELAY / 1000);
            delay(RETRY_DELAY);
        }
    }
    
    http.end();
    blinkLED(5, 50); // Fast blink indicates error
    return false;
}

// BLE Scan Callback
class MyAdvertisedDeviceCallbacks: public NimBLEAdvertisedDeviceCallbacks {
    void onResult(NimBLEAdvertisedDevice* advertisedDevice) {
        // Create observation
        Observation obs;
        obs.mac = advertisedDevice->getAddress().toString().c_str();
        obs.rssi = advertisedDevice->getRSSI();
        obs.timestamp = millis();
        
        // Convert MAC to uppercase and standardize format
        obs.mac.toUpperCase();
        
        // Add to observations list
        observations.push_back(obs);
        
        Serial.printf("[BLE] Found device: %s, RSSI: %d dBm\n", 
                     obs.mac.c_str(), obs.rssi);
        
        // Prevent buffer overflow
        if (observations.size() >= MAX_OBSERVATIONS) {
            Serial.println("[BLE] Observation buffer full, triggering upload");
        }
    }
};

// Initialize BLE scanner
void initBLE() {
    Serial.println("[BLE] Initializing NimBLE");
    
    NimBLEDevice::init("");
    pBLEScan = NimBLEDevice::getScan();
    pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks(), false);
    pBLEScan->setActiveScan(true); // Active scan uses more power but gets more data
    pBLEScan->setInterval(100);
    pBLEScan->setWindow(99);
    
    Serial.println("[BLE] Scanner initialized");
}

// Upload observations to server
bool uploadObservations() {
    if (observations.empty()) {
        Serial.println("[HTTP] No observations to upload");
        return true;
    }
    
    if (!WiFi.isConnected()) {
        Serial.println("[HTTP] WiFi not connected");
        return false;
    }
    
    HTTPClient http;
    String url = String(SERVER_URL) + "/api/v1/observations/batch";
    
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-Key", API_KEY);  // Add API key authentication
    http.setTimeout(HTTP_TIMEOUT);
    
    // Create JSON payload
    DynamicJsonDocument doc(8192);
    doc["station_uuid"] = STATION_UUID;
    JsonArray obsArray = doc.createNestedArray("observations");
    
    for (const auto& obs : observations) {
        JsonObject obsObj = obsArray.createNestedObject();
        obsObj["device_mac"] = obs.mac;  // Fixed: API expects 'device_mac' not 'mac'
        obsObj["rssi"] = obs.rssi;
        obsObj["protocol"] = "ble";
        // Convert timestamp to ISO format
        unsigned long seconds = obs.timestamp / 1000;
        char timestamp[32];
        sprintf(timestamp, "%lu", seconds);
        obsObj["timestamp"] = timestamp;
    }
    
    String payload;
    serializeJson(doc, payload);
    
    Serial.printf("[HTTP] Uploading %d observations\n", observations.size());
    
    int httpCode = http.POST(payload);
    
    bool success = false;
    if (httpCode == 200 || httpCode == 201) {
        Serial.println("[HTTP] Observations uploaded successfully");
        observations.clear(); // Clear observations after successful upload
        success = true;
    } else if (httpCode > 0) {
        Serial.printf("[HTTP] Upload failed, code: %d\n", httpCode);
        String response = http.getString();
        Serial.println("[HTTP] Response: " + response);
    } else {
        Serial.printf("[HTTP] Connection failed: %s\n", http.errorToString(httpCode).c_str());
    }
    
    http.end();
    return success;
}

// Perform BLE scan
void performScan() {
    Serial.println("[BLE] Starting scan...");
    
    // Start scanning
    NimBLEScanResults results = pBLEScan->start(BLE_SCAN_TIME, false);
    
    Serial.printf("[BLE] Scan complete. Found %d devices\n", results.getCount());
    
    // Clear scan results to free memory
    pBLEScan->clearResults();
}

#if ENABLE_OTA
void setupOTA() {
    Serial.println("[OTA] Setting up OTA updates");
    
    ArduinoOTA.setHostname(STATION_UUID);
    ArduinoOTA.setPassword(OTA_PASSWORD);
    
    ArduinoOTA.onStart([]() {
        String type = (ArduinoOTA.getCommand() == U_FLASH) ? "sketch" : "filesystem";
        Serial.println("[OTA] Start updating " + type);
        blinkLED(10, 50);
    });
    
    ArduinoOTA.onEnd([]() {
        Serial.println("\n[OTA] Update complete");
        blinkLED(3, 200);
    });
    
    ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
        Serial.printf("[OTA] Progress: %u%%\r", (progress / (total / 100)));
    });
    
    ArduinoOTA.onError([](ota_error_t error) {
        Serial.printf("[OTA] Error[%u]: ", error);
        if (error == OTA_AUTH_ERROR) Serial.println("Auth Failed");
        else if (error == OTA_BEGIN_ERROR) Serial.println("Begin Failed");
        else if (error == OTA_CONNECT_ERROR) Serial.println("Connect Failed");
        else if (error == OTA_RECEIVE_ERROR) Serial.println("Receive Failed");
        else if (error == OTA_END_ERROR) Serial.println("End Failed");
        blinkLED(10, 50);
    });
    
    ArduinoOTA.begin();
    Serial.println("[OTA] OTA ready");
}
#endif

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("\n\n=================================");
    Serial.println("BeaconBoard ESP32-S3 BLE Scanner");
    Serial.println("=================================");
    Serial.printf("Station UUID: %s\n", STATION_UUID);
    Serial.printf("Station Name: %s\n", STATION_NAME);
    Serial.println("=================================\n");
    
    // Setup LED
    #if LED_ENABLED
    pinMode(LED_PIN, OUTPUT);
    setLED(false);
    #endif
    
    // Connect to WiFi
    if (!connectWiFi()) {
        Serial.println("[ERROR] WiFi connection failed. Restarting in 10 seconds...");
        delay(10000);
        ESP.restart();
    }
    
    #if ENABLE_OTA
    setupOTA();
    #endif
    
    // Register station
    stationRegistered = registerStation();
    if (!stationRegistered) {
        Serial.println("[WARN] Station registration failed, will retry later");
    }
    
    // Initialize BLE
    initBLE();
    
    Serial.println("[INFO] Setup complete, starting scanning loop");
}

void loop() {
    // Handle OTA updates
    #if ENABLE_OTA
    ArduinoOTA.handle();
    #endif
    
    // Check WiFi connection
    if (!WiFi.isConnected()) {
        Serial.println("[WiFi] Connection lost, reconnecting...");
        setLED(false);
        if (!connectWiFi()) {
            Serial.println("[ERROR] WiFi reconnection failed. Restarting...");
            delay(5000);
            ESP.restart();
        }
    }
    
    // Register station if not already registered
    if (!stationRegistered) {
        stationRegistered = registerStation();
    }
    
    // Perform BLE scan
    performScan();
    
    // Check if it's time to upload or buffer is full
    unsigned long now = millis();
    bool shouldUpload = (now - lastUpload >= SCAN_INTERVAL) || 
                       (observations.size() >= MAX_OBSERVATIONS);
    
    if (shouldUpload && !observations.empty()) {
        if (uploadObservations()) {
            lastUpload = now;
        } else {
            Serial.println("[WARN] Upload failed, will retry on next cycle");
            // Don't clear observations on failure, will retry
        }
    }
    
    #if ENABLE_DEEP_SLEEP
    // Enter deep sleep to save power
    Serial.printf("[SLEEP] Entering deep sleep for %d seconds\n", SLEEP_DURATION);
    esp_sleep_enable_timer_wakeup(SLEEP_DURATION * 1000000ULL);
    esp_deep_sleep_start();
    #else
    // Small delay to prevent tight loop
    delay(100);
    #endif
}
