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

echo "Installing system dependencies..."
apt update
apt install -y python3 python3-pip git build-essential libpcap-dev libusb-1.0-0-dev libnetfilter-queue-dev

echo "Installing Python packages..."
pip3 install requests

echo ""
echo "======================================"
echo "Installing Bettercap..."
echo "======================================"
echo ""

# Check if bettercap is already installed
if command -v bettercap &> /dev/null; then
    echo "Bettercap is already installed ($(bettercap -version 2>&1 | head -n1))"
    read -p "Do you want to reinstall/update it? (y/N): " REINSTALL
    if [[ ! "$REINSTALL" =~ ^[Yy]$ ]]; then
        echo "Skipping Bettercap installation."
        SKIP_BETTERCAP=1
    fi
fi

if [ -z "$SKIP_BETTERCAP" ]; then
    # Install Go if not installed
    if ! command -v go &> /dev/null; then
        echo "Installing Go programming language..."
        GO_VERSION="1.21.5"
        GO_ARCH="arm64"
        
        # Detect architecture
        ARCH=$(uname -m)
        if [[ "$ARCH" == "armv7l" ]] || [[ "$ARCH" == "armv6l" ]]; then
            GO_ARCH="armv6l"
        elif [[ "$ARCH" == "aarch64" ]]; then
            GO_ARCH="arm64"
        fi
        
        wget https://go.dev/dl/go${GO_VERSION}.linux-${GO_ARCH}.tar.gz -O /tmp/go.tar.gz
        rm -rf /usr/local/go
        tar -C /usr/local -xzf /tmp/go.tar.gz
        rm /tmp/go.tar.gz
        
        # Add Go to PATH
        export PATH=$PATH:/usr/local/go/bin
        echo 'export PATH=$PATH:/usr/local/go/bin' >> /etc/profile
        echo "Go installed successfully"
    else
        echo "Go is already installed ($(go version))"
        export PATH=$PATH:/usr/local/go/bin
    fi
    
    # Install Bettercap from source
    echo "Building and installing Bettercap from source..."
    TEMP_DIR=$(mktemp -d)
    cd $TEMP_DIR
    git clone https://github.com/bettercap/bettercap.git
    cd bettercap
    make build
    make install
    cd /
    rm -rf $TEMP_DIR
    
    echo "Bettercap installed successfully"
    bettercap -version
fi

echo ""
echo "======================================"
echo "Configuring Bettercap Service..."
echo "======================================"
echo ""

# Create Bettercap systemd service
cat > /etc/systemd/system/bettercap.service <<'EOF'
[Unit]
Description=Bettercap Network Monitoring
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/bettercap -caplet beaconboard
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "Bettercap service created"

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
echo "Enabling and starting services..."
systemctl daemon-reload

# Start Bettercap first
systemctl enable bettercap
systemctl restart bettercap

# Wait a moment for Bettercap to start
sleep 3

# Start BeaconBoard agent
systemctl enable beaconboard-agent
systemctl restart beaconboard-agent

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Services Status:"
echo "  Bettercap:  $(systemctl is-active bettercap)"
echo "  Agent:      $(systemctl is-active beaconboard-agent)"
echo ""
echo "Check service status with:"
echo "  sudo systemctl status bettercap"
echo "  sudo systemctl status beaconboard-agent"
echo ""
echo "View logs with:"
echo "  sudo journalctl -u bettercap -f"
echo "  sudo journalctl -u beaconboard-agent -f"
echo ""
echo "Test Bettercap API:"
echo "  curl -u user:$BETTERCAP_PASS http://localhost:8081/api/session/wifi"
echo ""
echo "Configuration file: /etc/beaconboard/config.json"
echo "Agent directory: $INSTALL_DIR"
echo "Bettercap caplet: /usr/local/share/bettercap/caplets/beaconboard.cap"
echo ""
echo "IMPORTANT: If WiFi scanning doesn't work, make sure:"
echo "  1. Your WiFi adapter supports monitor mode"
echo "  2. NetworkManager is disabled on the WiFi interface"
echo "  3. The interface is not being used by wpa_supplicant"
echo ""
