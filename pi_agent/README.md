# BeaconBoard Pi Agent

Raspberry Pi client agent for scanning WiFi and BLE devices using Bettercap.

## Quick Setup (Automated)

The easiest way to set up the agent is using the automated setup script:

```bash
# Copy agent files to your Raspberry Pi
scp -r pi_agent/ pi@raspberry-pi:~/

# SSH to your Pi
ssh pi@raspberry-pi

# Run the setup script
cd ~/pi_agent
sudo ./setup.sh
```

The setup script will:
- ✅ Install all system dependencies
- ✅ **Automatically install Bettercap** (including Go if needed)
- ✅ Configure Bettercap with the beaconboard caplet
- ✅ Create systemd services for both Bettercap and the agent
- ✅ Set up configuration file with your station details
- ✅ Start everything automatically

**That's it!** Your station will be scanning and sending data to the server.

## Manual Installation (Advanced)

If you prefer to install Bettercap manually or already have it installed:

### Install Bettercap Manually

```bash
# Install dependencies
sudo apt update
sudo apt install -y build-essential libpcap-dev libusb-1.0-0-dev libnetfilter-queue-dev

# Install Go (if not already installed)
wget https://go.dev/dl/go1.21.5.linux-arm64.tar.gz
sudo tar -C /usr/local -xzf go1.21.5.linux-arm64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc

# Install Bettercap from source
git clone https://github.com/bettercap/bettercap.git
cd bettercap
make build
sudo make install
```

### Configure Bettercap Caplet

The `beaconboard.cap` caplet is included and will be installed automatically by `setup.sh`.

For manual setup, create `/usr/local/share/bettercap/caplets/beaconboard.cap`:

```
# BeaconBoard Bettercap Caplet
# Enables WiFi and BLE scanning with API access

# Enable API server
set api.rest.address 0.0.0.0
set api.rest.port 8081
set api.rest.username user
set api.rest.password pass
api.rest on

# WiFi scanning
set wifi.interface wlan0
wifi.recon on

# BLE scanning
set ble.device hci0
ble.recon on

# Keep running
events.ignore endpoint
events.ignore wifi.client.probe
```

See the included `beaconboard.cap` file for the complete configuration.

## What Gets Installed

When you run `sudo ./setup.sh`, the following components are installed and configured:

### System Packages
- Python 3 and pip
- Git, build tools, libpcap, libusb, libnetfilter-queue
- Go programming language (if not already installed)

### Bettercap
- Built from source and installed to `/usr/local/bin/bettercap`
- Systemd service created at `/etc/systemd/system/bettercap.service`
- Caplet installed at `/usr/local/share/bettercap/caplets/beaconboard.cap`
- Configured to start automatically on boot

### BeaconBoard Agent
- Agent script installed at `~/beaconboard/agent.py`
- Configuration file at `/etc/beaconboard/config.json`
- Systemd service created at `/etc/systemd/system/beaconboard-agent.service`
- Configured to start automatically on boot

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
  "bettercap_url": "http://localhost:8081",
  "bettercap_user": "user",
  "bettercap_pass": "pass",
  "batch_interval_sec": 1,
  "max_batch_size": 200
}
```

**Configuration Parameters:**
- `station_uuid`: Unique identifier for this station (e.g., "bedroom", "kitchen")
- `name`: Human-readable name for display
- `description`: Optional description
- `server_url`: URL of your BeaconBoard server
- `wifi_interface`: WiFi interface (usually wlan0 or wlan1)
- `ble_interface`: Bluetooth interface (usually hci0)
- `bettercap_url`: URL of Bettercap API (default: http://localhost:8081)
- `bettercap_user`: Bettercap API username (set in caplet)
- `bettercap_pass`: Bettercap API password (set in caplet)
- `batch_interval_sec`: How often to upload observations (default: 1 second)
- `max_batch_size`: Maximum observations per batch (default: 200)

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

## How It Works

The agent communicates with Bettercap via its REST API to get WiFi and BLE scanning data:

### WiFi Scanning
- Bettercap runs in WiFi reconnaissance mode
- Agent queries `/api/session/wifi` endpoint
- Extracts MAC addresses, RSSI, channels, and SSIDs
- Captures both access points (APs) and client devices

### BLE Scanning
- Bettercap runs in BLE reconnaissance mode
- Agent queries `/api/session/ble` endpoint
- Extracts MAC addresses and RSSI values
- Detects BLE beacons, peripherals, and advertisements

### Data Flow
1. Bettercap continuously scans for WiFi/BLE devices
2. Agent polls Bettercap API every `batch_interval_sec` seconds
3. Agent formats observations and batches them
4. Agent uploads batches to BeaconBoard server
5. Server performs triangulation and updates device positions

## Troubleshooting

### Check Bettercap Status
```bash
sudo systemctl status bettercap
sudo journalctl -u bettercap -f
```

### Test Bettercap API
```bash
curl -u user:pass http://localhost:8081/api/session/wifi
curl -u user:pass http://localhost:8081/api/session/ble
```

### Monitor Agent
```bash
# If running manually
python3 agent.py config.json

# If running as service
sudo journalctl -u beaconboard-agent -f
```

### Common Issues

**WiFi interface not found:**
- Check available interfaces: `ip link show`
- May need to use `wlan1` or other interface name
- Ensure WiFi adapter supports monitor mode

**BLE not working:**
- Check Bluetooth status: `sudo systemctl status bluetooth`
- Check BLE interface: `hciconfig`
- May need to enable: `sudo hciconfig hci0 up`

**Connection refused to Bettercap:**
- Check Bettercap is running: `sudo systemctl status bettercap`
- Verify port 8081 is open: `sudo netstat -tulpn | grep 8081`
- Check firewall rules

**No observations being uploaded:**
- Verify server URL in config is correct
- Check network connectivity to server
- Look for errors in agent logs

## Logs

When running as service, view logs with:
```bash
sudo journalctl -u beaconboard-agent -f
```
