# BeaconBoard Pi Agent

Raspberry Pi client agent for scanning WiFi and BLE devices.

## Installation

1. Copy this directory to your Raspberry Pi
2. Install dependencies:
   ```bash
   pip3 install requests
   ```

## Configuration

Create `/etc/beaconboard/config.json`:

```json
{
  "station_uuid": "garden_north",
  "name": "Garden North Station",
  "description": "Pi at north side of garden",
  "server_url": "http://your-server-ip:5000",
  "wifi_interface": "wlan0",
  "ble_interface": "hci0",
  "batch_interval_sec": 1,
  "max_batch_size": 200
}
```

Or run with a local config file:
```bash
python3 agent.py config.json
```

## Running

### Manual
```bash
python3 agent.py
```

### As systemd service

Create `/etc/systemd/system/beaconboard-agent.service`:

```ini
[Unit]
Description=BeaconBoard Pi Agent
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/beaconboard
ExecStart=/usr/bin/python3 /home/pi/beaconboard/agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable beaconboard-agent
sudo systemctl start beaconboard-agent
sudo systemctl status beaconboard-agent
```

## WiFi/BLE Scanning

The current implementation uses stub scanners that generate random test data.

To implement real scanning:

### WiFi
- Use `tcpdump` with monitor mode or `scapy` to capture WiFi frames
- Extract MAC addresses and RSSI from captured packets

### BLE
- Use BlueZ with `hcitool` or Python `bleak` library
- Scan for BLE advertisements and extract MAC and RSSI

## Logs

When running as service, view logs with:
```bash
sudo journalctl -u beaconboard-agent -f
```
