# BeaconBoard ESP32-S3 BLE Scanner

This directory contains the PlatformIO project for ESP32-S3 BLE scanning stations. These modules scan for BLE devices and send observation data to the BeaconBoard server for triangulation.

## Features

- **BLE-Only Scanning**: Efficient BLE device detection using NimBLE stack
- **WiFi Connectivity**: Connects to BeaconBoard server via WiFi
- **Auto-Registration**: Automatically registers as a station on first boot
- **Batch Upload**: Sends observations in batches every 10 seconds (configurable)
- **Deep Sleep Support**: Optional power-saving mode for battery operation
- **LED Status Indicators**: Visual feedback for WiFi, scanning, and error states
- **OTA Updates**: Remote firmware updates via HTTP
- **Easy Configuration**: Simple config.h file for customization

## Hardware Requirements

- **ESP32-S3** module (any variant):
  - ESP32-S3-DevKitC-1
  - ESP32-S3-WROOM
  - ESP32-S3-MINI
  - Any other ESP32-S3 board
  - **Note**: Code is configured for 4MB flash (compatible with most modules)
- **USB-C cable** for programming and power
- **WiFi network** with internet/LAN access to BeaconBoard server
- **Optional**: External BLE antenna for extended range

## Software Requirements

- [PlatformIO](https://platformio.org/) (recommended) or Arduino IDE
- USB drivers for ESP32-S3 (usually auto-installed)

## Quick Start

### 1. Install PlatformIO

```bash
# Via pip
pip install platformio

# Or via VS Code extension
# Search for "PlatformIO IDE" in VS Code extensions
```

### 2. Configure Your Scanner

Edit `include/config.h` and set your parameters:

```cpp
// WiFi Configuration
#define WIFI_SSID "YourNetworkName"
#define WIFI_PASSWORD "YourPassword"

// BeaconBoard Server
#define SERVER_URL "http://192.168.1.100:5000"  // Your server IP

// Station Info
#define STATION_UUID "esp32_bedroom"            // Unique ID
#define STATION_NAME "ESP32 Bedroom Scanner"   // Display name
```

### 3. Build and Upload

```bash
# Navigate to this directory
cd esp32_scanner

# IMPORTANT: If you previously uploaded code, erase flash first!
# This clears old partition tables that may cause boot loops
pio run --target erase

# Build the project
pio run

# Upload to ESP32-S3 (connect via USB)
pio run --target upload

# Monitor serial output
pio device monitor
```

**Note:** The erase step is critical if you've uploaded code before. It clears the old 8MB partition table that causes the "flash size mismatch" error.

### 4. Verify Operation

Watch the serial monitor output:

```
=================================
BeaconBoard ESP32-S3 BLE Scanner
=================================
Station UUID: esp32_bedroom
Station Name: ESP32 Bedroom Scanner
=================================

[WiFi] Connecting to YourNetwork
[WiFi] Connected!
[WiFi] IP address: 192.168.1.123
[HTTP] Registering station at http://192.168.1.100:5000/api/v1/station/register
[HTTP] Station registered successfully
[BLE] Initializing NimBLE
[BLE] Scanner initialized
[INFO] Setup complete, starting scanning loop
[BLE] Starting scan...
[BLE] Found device: AA:BB:CC:DD:EE:FF, RSSI: -65 dBm
[BLE] Found device: 11:22:33:44:55:66, RSSI: -72 dBm
[BLE] Scan complete. Found 2 devices
[HTTP] Uploading 2 observations
[HTTP] Observations uploaded successfully
```

## Configuration Options

### WiFi Settings

```cpp
#define WIFI_SSID "YourNetworkName"
#define WIFI_PASSWORD "YourPassword"
#define WIFI_TIMEOUT 30000  // Connection timeout (ms)
```

### Server Settings

```cpp
#define SERVER_URL "http://192.168.1.100:5000"
#define HTTP_TIMEOUT 10000   // HTTP request timeout (ms)
#define MAX_RETRIES 3        // Retry attempts
```

### Station Identity

```cpp
#define STATION_UUID "esp32_bedroom"  // Must be unique!
#define STATION_NAME "ESP32 Bedroom Scanner"
#define STATION_DESCRIPTION "BLE scanner in bedroom"
```

### Scanning Parameters

```cpp
#define SCAN_INTERVAL 10000    // Upload every 10 seconds
#define BLE_SCAN_TIME 8        // Scan duration in seconds
#define MAX_OBSERVATIONS 50    // Buffer size before forced upload
```

### Deep Sleep (Battery Mode)

```cpp
#define ENABLE_DEEP_SLEEP false  // Set to true for battery operation
#define SLEEP_DURATION 30        // Sleep seconds between scans
```

When enabled:
- Scanner wakes up, scans for `BLE_SCAN_TIME` seconds
- Uploads observations
- Enters deep sleep for `SLEEP_DURATION` seconds
- Repeats cycle
- **Power consumption**: ~5mA average (vs ~80mA continuous)

### LED Indicators

```cpp
#define LED_PIN 2           // GPIO pin for LED
#define LED_ENABLED true    // Set to false to disable LED
```

LED patterns:
- **Slow blink**: WiFi connecting
- **Solid**: WiFi connected, scanning active
- **3 quick blinks**: Registration successful
- **Fast blink (5x)**: Error occurred

### OTA Updates

```cpp
#define ENABLE_OTA false       // Enable remote updates
#define OTA_PASSWORD "admin"   // Change this!
```

To upload firmware via OTA:

```bash
# After enabling OTA and uploading once via USB
pio run --target upload --upload-port 192.168.1.123
```

## Power Consumption

| Mode | Current | Notes |
|------|---------|-------|
| Active WiFi + BLE scan | ~80mA | Continuous operation |
| WiFi only (idle) | ~60mA | Between scans |
| Deep sleep | <1mA | Wake on timer |
| **Average (deep sleep mode)** | **~5mA** | 8s scan every 30s |

### Battery Life Estimates

With 2000mAh battery:
- **Continuous**: ~25 hours
- **Deep sleep (30s)**: ~400 hours (~16 days)
- **Deep sleep (60s)**: ~600 hours (~25 days)

## Positioning Your Scanner

After deployment:

1. Go to BeaconBoard web UI
2. Navigate to **Stations** page
3. Verify your ESP32 station is listed
4. Go to **Map** page
5. Click **📍 Edit Station Positions**
6. Drag your station to its physical location
7. Click **✓ Done Editing**

## Troubleshooting

### WiFi Won't Connect

1. Check SSID and password in `config.h`
2. Verify 2.4GHz WiFi (ESP32 doesn't support 5GHz)
3. Check WiFi signal strength at installation location
4. Monitor serial output for error messages

### Station Not Registering

1. Verify `SERVER_URL` is correct
2. Check server is running and accessible
3. Ensure firewall allows port 5000 (or your server port)
4. Try accessing server URL in browser from same network
5. Check serial monitor for HTTP error codes
6. **Verify `API_KEY` is set** in config.h (get from BeaconBoard web UI → 🔑 API Keys)

### Flash Size Error / Boot Loop

If you see errors like:
- "Detected size(4096k) smaller than the size in the binary image header(8192k)"
- "assert failed: do_core_init"
- "E (243) esp_core_dump_flash: Core dump flash config is corrupted!"
- Device keeps rebooting continuously

**Root Cause:** Flash configuration mismatch. Your ESP32 has 4MB flash but old partition tables or incompatible flash modes are cached.

**Solution - CRITICAL 3-STEP FIX:**

```bash
# Step 1: ERASE ENTIRE FLASH (clears old partition table)
pio run --target erase

# Step 2: Clean all cached builds
pio run --target clean

# Step 3: Upload fresh build
pio run --target upload
```

**If Step 1 fails or device still reboots:**

```bash
# Manual flash erase with esptool (more reliable)
esptool.py --chip esp32s3 --port /dev/ttyUSB0 erase_flash

# Wait for "Chip erase completed successfully"
# Then upload
pio run --target upload
```

**If STILL failing (rare):**

```bash
# Nuclear option: Delete ALL cached files
rm -rf .pio/

# Erase flash manually
esptool.py --chip esp32s3 --port /dev/ttyUSB0 erase_flash

# Rebuild and upload from scratch
pio run --target upload
```

**Why This Happens:**
- ESP32 caches partition tables in flash memory
- Previous uploads may have used 8MB (default) instead of 4MB
- Changing platformio.ini alone doesn't clear cached data
- **Flash must be erased** to clear old partition tables
- DIO flash mode (now set) is more compatible than QIO mode

**Platform-specific port names:**
- Linux/Mac: `/dev/ttyUSB0` or `/dev/ttyACM0`
- Windows: `COM3`, `COM4`, etc.
- Check with: `pio device list`

**Flash Mode Notes:**
- This project uses **DIO mode** (more compatible)
- QIO mode may cause boot issues on some flash chips
- DIO works with wider variety of ESP32-S3 modules
- Flash frequency set to 80MHz for stability

### No BLE Devices Detected

1. Verify BLE devices are in range (typically 10-30m)
2. Check if BLE devices are advertising (not all do constantly)
3. Try shorter `SLEEP_DURATION` if using deep sleep
4. Consider external antenna for better range

### High Power Consumption

1. Enable `ENABLE_DEEP_SLEEP` for battery operation
2. Increase `SLEEP_DURATION` (trade-off: less frequent updates)
3. Disable LED: `#define LED_ENABLED false`
4. Reduce `BLE_SCAN_TIME` (trade-off: fewer devices detected)

### OTA Upload Fails

1. Ensure ESP32 and computer are on same network
2. Check `OTA_PASSWORD` matches in code and upload command
3. Verify firewall allows OTA port (default 3232)
4. Use IP address instead of hostname

## Serial Commands

The scanner logs all activity to serial at 115200 baud. Connect with:

```bash
pio device monitor

# Or with specific port
pio device monitor -p /dev/ttyUSB0
```

## Building for Different Boards

The default configuration is for ESP32-S3-DevKitC-1. For other boards, edit `platformio.ini`:

```ini
# For ESP32-S3-WROOM
[env:esp32-s3-devkitc-1]
board = esp32-s3-devkitc-1

# For ESP32-S3 generic
[env:esp32s3]
board = esp32s3
```

## Integration with BeaconBoard

The scanner uses the same API endpoints as Raspberry Pi stations:

- `POST /api/v1/station/register` - Register station
- `POST /api/v1/observations/batch` - Upload BLE observations

Data format:
```json
{
  "station_uuid": "esp32_bedroom",
  "observations": [
    {
      "mac": "AA:BB:CC:DD:EE:FF",
      "rssi": -65,
      "protocol": "ble",
      "timestamp": "1638360000"
    }
  ]
}
```

## Development

### VS Code + PlatformIO

1. Open this directory in VS Code
2. Install PlatformIO extension
3. Use bottom toolbar for build/upload/monitor

### Add Custom Libraries

Edit `platformio.ini`:

```ini
lib_deps = 
    h2zero/NimBLE-Arduino@^1.4.1
    bblanchon/ArduinoJson@^6.21.3
    your/library@^version
```

### Debug Output

Increase debug level in `platformio.ini`:

```ini
build_flags = 
    -D CORE_DEBUG_LEVEL=5  # 0=None, 5=Verbose
```

## Performance Tuning

### Maximize Range

```cpp
#define BLE_SCAN_TIME 10      // Longer scan
```

Add external antenna to ESP32-S3

### Maximize Battery Life

```cpp
#define ENABLE_DEEP_SLEEP true
#define SLEEP_DURATION 60     // Scan every 60s
#define BLE_SCAN_TIME 5       // Shorter scan
#define LED_ENABLED false     // Disable LED
```

### Maximize Detection Rate

```cpp
#define ENABLE_DEEP_SLEEP false  // Continuous
#define BLE_SCAN_TIME 8          // Standard scan time
#define SCAN_INTERVAL 5000       // Upload every 5s
```

## Support

For issues or questions:

1. Check serial monitor output for errors
2. Verify configuration in `config.h`
3. Review BeaconBoard server logs
4. Open issue on GitHub repository

## License

Part of the BeaconBoard IoT Device Tracking System.
