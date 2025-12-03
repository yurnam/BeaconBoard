#!/bin/bash
# BeaconBoard Pi Agent Setup Script
# Run this script on your Raspberry Pi to set up the agent

set -e

echo "======================================"
echo "BeaconBoard Pi Agent Setup"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
USER_HOME=$(eval echo ~$ACTUAL_USER)

echo "Installing dependencies..."
apt update
apt install -y python3 python3-pip

echo "Installing Python packages..."
pip3 install requests

echo "Creating configuration directory..."
mkdir -p /etc/beaconboard

# Create config if it doesn't exist
if [ ! -f /etc/beaconboard/config.json ]; then
    echo "Creating default configuration..."
    read -p "Enter station UUID (e.g., bedroom, kitchen): " STATION_UUID
    read -p "Enter station name: " STATION_NAME
    read -p "Enter BeaconBoard server URL (e.g., http://192.168.1.100:5000): " SERVER_URL
    read -p "Enter WiFi interface (default: wlan0): " WIFI_IF
    WIFI_IF=${WIFI_IF:-wlan0}
    read -p "Enter BLE interface (default: hci0): " BLE_IF
    BLE_IF=${BLE_IF:-hci0}
    read -p "Enter Bettercap API password (default: pass): " BETTERCAP_PASS
    BETTERCAP_PASS=${BETTERCAP_PASS:-pass}
    
    cat > /etc/beaconboard/config.json <<EOF
{
  "station_uuid": "$STATION_UUID",
  "name": "$STATION_NAME",
  "description": "Raspberry Pi scanning station",
  "server_url": "$SERVER_URL",
  "wifi_interface": "$WIFI_IF",
  "ble_interface": "$BLE_IF",
  "bettercap_url": "http://localhost:8081",
  "bettercap_user": "user",
  "bettercap_pass": "$BETTERCAP_PASS",
  "batch_interval_sec": 1,
  "max_batch_size": 200
}
EOF
    chmod 600 /etc/beaconboard/config.json
    echo "Configuration created at /etc/beaconboard/config.json"
else
    echo "Configuration already exists at /etc/beaconboard/config.json"
fi

echo ""
echo "Installing Bettercap caplet..."
mkdir -p /usr/local/share/bettercap/caplets
cp beaconboard.cap /usr/local/share/bettercap/caplets/

# Update caplet with configured password
sed -i "s/set api.rest.password pass/set api.rest.password $BETTERCAP_PASS/" /usr/local/share/bettercap/caplets/beaconboard.cap
sed -i "s/set wifi.interface wlan0/set wifi.interface $WIFI_IF/" /usr/local/share/bettercap/caplets/beaconboard.cap
sed -i "s/set ble.device hci0/set ble.device $BLE_IF/" /usr/local/share/bettercap/caplets/beaconboard.cap

echo ""
echo "Installing agent files..."
INSTALL_DIR="$USER_HOME/beaconboard"
mkdir -p $INSTALL_DIR
cp agent.py $INSTALL_DIR/
chown -R $ACTUAL_USER:$ACTUAL_USER $INSTALL_DIR

echo ""
echo "Creating systemd service..."
cat > /etc/systemd/system/beaconboard-agent.service <<EOF
[Unit]
Description=BeaconBoard Pi Agent
After=network.target bettercap.service
Requires=bettercap.service

[Service]
Type=simple
User=$ACTUAL_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/agent.py /etc/beaconboard/config.json
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "Enabling and starting service..."
systemctl daemon-reload
systemctl enable beaconboard-agent
systemctl start beaconboard-agent

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Agent is now running. Check status with:"
echo "  sudo systemctl status beaconboard-agent"
echo ""
echo "View logs with:"
echo "  sudo journalctl -u beaconboard-agent -f"
echo ""
echo "IMPORTANT: Make sure Bettercap is installed and running!"
echo "  sudo systemctl status bettercap"
echo ""
echo "Configuration file: /etc/beaconboard/config.json"
echo "Agent directory: $INSTALL_DIR"
echo ""
