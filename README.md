# BeaconBoard - IoT Device Tracking System

BeaconBoard is a home surveillance system that uses multiple IoT devices (Raspberry Pi stations) to track WiFi and BLE devices using triangulation and display them on an interactive map.

## Features

- **Multiple Scanning Stations**: Deploy Raspberry Pi devices around your property to scan for WiFi and BLE devices
- **Live Device Tracking**: Real-time triangulation to estimate device positions on a floor plan
- **Interactive Map View**: Upload custom floor plans and see devices moving in real-time
- **Device Management**: Name devices, assign icons and colors, ignore unwanted devices
- **Webhook Notifications**: Get notified when new devices are detected
- **Web Dashboard**: Modern web interface to monitor and manage your system

## Architecture

### Components

1. **Server (Flask Application)**
   - RESTful API for stations and observations
   - Database (SQLite/PostgreSQL) for storing data
   - Triangulation engine for position estimation
   - WebSocket support for live updates
   - Webhook system for event notifications

2. **Client Agents (Raspberry Pi)**
   - WiFi/BLE scanning capabilities
   - Batch upload of observations to server
   - Auto-registration with server
   - Systemd service for persistent operation

## Installation

### Server Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd BeaconBoard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

4. **Run the server**
   ```bash
   python app.py
   ```

   The server will start on `http://0.0.0.0:5000`

### Client Agent Setup (Raspberry Pi)

See [pi_agent/README.md](pi_agent/README.md) for detailed instructions.

Quick start:
```bash
cd pi_agent
pip3 install requests
python3 agent.py
```

## Configuration

### Server Configuration

Edit `config.py` or set environment variables:

- `SECRET_KEY`: Flask secret key for sessions
- `DATABASE_URL`: Database connection URL
- `OBSERVATION_WINDOW_SECONDS`: Time window for triangulation (default: 10)
- `TRIANGULATION_INTERVAL_SECONDS`: How often to run triangulation (default: 2)
- `MIN_STATIONS_FOR_TRIANGULATION`: Minimum stations needed (default: 3)

### Client Configuration

Create `/etc/beaconboard/config.json` on each Raspberry Pi:

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

## Usage

### 1. Upload a Map

1. Navigate to **Settings** in the web interface
2. Upload a floor plan image (PNG, JPG, etc.)
3. Activate the map

### 2. Position Stations

1. Go to the **Map** view
2. Click "Edit Station Positions"
3. Drag station markers to their physical locations on the map
4. Click "Save Positions"

### 3. Manage Devices

1. Go to **Devices** page
2. Assign friendly names to recognized devices
3. Choose icons (phone, laptop, car, etc.)
4. Set custom colors for each device
5. Mark unwanted devices as "ignored"

### 4. Monitor Live

1. Visit the **Map** page to see devices in real-time
2. View the **Dashboard** for statistics and recent activity

## API Documentation

### Station Registration

```http
POST /api/v1/station/register
Content-Type: application/json

{
  "station_uuid": "garden_north",
  "name": "Garden North",
  "description": "North side of garden"
}
```

### Upload Observations

```http
POST /api/v1/observations/batch
Content-Type: application/json

{
  "station_uuid": "garden_north",
  "observations": [
    {
      "device_mac": "AA:BB:CC:DD:EE:FF",
      "timestamp": 1733142980,
      "rssi": -68,
      "protocol": "wifi",
      "channel": 6,
      "ssid": "MyWiFi"
    }
  ]
}
```

### Update Station Position

```http
POST /api/v1/stations/<id>/position
Content-Type: application/json

{
  "x_norm": 0.42,
  "y_norm": 0.73
}
```

See the code for complete API documentation.

## Triangulation

BeaconBoard uses a combination of techniques to estimate device positions:

1. **RSSI to Distance Conversion**: Path-loss model to convert signal strength to distance
2. **2D Trilateration**: Uses distances from 3+ stations to calculate position
3. **Position Smoothing**: Exponential moving average to reduce jitter
4. **Normalized Coordinates**: All positions are stored as 0-1 values relative to map size

## Webhooks

Configure webhooks to receive notifications when events occur:

- **device_first_seen**: Triggered when a new device is detected
- HMAC signing supported for security

Example webhook payload:
```json
{
  "event": "device_first_seen",
  "mac": "AA:BB:CC:DD:EE:FF",
  "first_seen": "2025-12-02T12:34:56Z",
  "protocol": "wifi",
  "station_first_seen": "garden_north"
}
```

## Development

### Project Structure

```
BeaconBoard/
├── app.py                 # Main Flask application
├── config.py             # Configuration
├── models.py             # Database models
├── triangulation.py      # Triangulation algorithms
├── workers.py            # Background workers
├── api/                  # API endpoints
│   ├── stations.py
│   ├── observations.py
│   ├── devices.py
│   └── webhooks.py
├── routes/               # Web UI routes
│   ├── main.py
│   ├── stations.py
│   ├── devices.py
│   └── maps.py
├── templates/            # HTML templates
├── static/               # CSS, JavaScript
└── pi_agent/            # Raspberry Pi client
    ├── agent.py
    └── README.md
```

### Running in Development

```bash
export FLASK_ENV=development
python app.py
```

### Running in Production

Use a production WSGI server:

```bash
pip install gunicorn
gunicorn -w 4 -k eventlet -b 0.0.0.0:5000 app:app
```

## Contributing

Contributions are welcome! Areas for improvement:

- Real WiFi/BLE scanning implementation in Pi agent
- More sophisticated triangulation algorithms
- Multi-floor support
- Historical tracking and heatmaps
- Mobile app
- Docker containerization

## License

MIT License - See LICENSE file for details

## Security Considerations

- Change the default `SECRET_KEY` in production
- Use HTTPS for server communication
- Implement authentication for web interface
- Use webhook HMAC signatures
- Regularly update dependencies
- Follow privacy regulations when tracking devices

## Troubleshooting

### Server won't start

- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify database is accessible
- Check logs for specific errors

### Stations not appearing

- Verify station agent is running on Raspberry Pi
- Check network connectivity between Pi and server
- Review Pi agent logs for errors

### No device positions

- Ensure at least 3 stations have reported observations for the device
- Verify stations have positions set on the map
- Check triangulation worker is running

### Map not displaying

- Verify map image was uploaded successfully
- Check file permissions in `uploads/maps/` directory
- Ensure map is activated in settings

## Support

For issues and questions, please open a GitHub issue.
