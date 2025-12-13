#ifndef CONFIG_H
#define CONFIG_H

// WiFi Configuration
#define WIFI_SSID "YourNetworkName"
#define WIFI_PASSWORD "YourPassword"

// BeaconBoard Server Configuration
#define SERVER_URL "http://192.168.1.100:5000"  // Change to your server IP/hostname
#define API_KEY "YOUR_API_KEY_HERE"             // Get from BeaconBoard web interface (🔑 API Keys page)

// Station Configuration
#define STATION_UUID "esp32_bedroom"            // Unique identifier for this scanner
#define STATION_NAME "ESP32 Bedroom Scanner"   // Human-readable name
#define STATION_DESCRIPTION "BLE scanner in bedroom"

// Scanning Configuration
#define SCAN_INTERVAL 10000     // Upload observations every 10 seconds (ms)
#define BLE_SCAN_TIME 8         // BLE scan duration in seconds
#define MAX_OBSERVATIONS 50     // Maximum observations to buffer before upload

// Deep Sleep Configuration (for battery operation)
#define ENABLE_DEEP_SLEEP false // Set to true for battery-powered deployment
#define SLEEP_DURATION 30       // Seconds to sleep between scan cycles

// LED Configuration
#define LED_PIN 2              // Built-in LED pin (GPIO 2 on most ESP32-S3)
#define LED_ENABLED true       // Set to false to disable LED

// OTA Update Configuration
#define ENABLE_OTA false       // Set to true to enable Over-The-Air updates
#define OTA_PASSWORD "admin"   // Password for OTA updates (change this!)

// Advanced Settings
#define WIFI_TIMEOUT 30000     // WiFi connection timeout (ms)
#define HTTP_TIMEOUT 10000     // HTTP request timeout (ms)
#define RETRY_DELAY 5000       // Delay between retry attempts (ms)
#define MAX_RETRIES 3          // Maximum retry attempts for HTTP requests

#endif
