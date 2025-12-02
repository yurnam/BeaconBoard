"""Background workers for triangulation and webhooks"""
import threading
import time
import requests
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List
from models import db, Device, Station, Observation, Webhook
from triangulation import rssi_to_distance, trilaterate_2d, smooth_position, normalize_distance


class TriangulationWorker:
    """Background worker for device position triangulation"""
    
    def __init__(self, app, socketio, interval_seconds=2):
        self.app = app
        self.socketio = socketio
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the triangulation worker thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("Triangulation worker started")
    
    def stop(self):
        """Stop the triangulation worker thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Triangulation worker stopped")
    
    def _run(self):
        """Main worker loop"""
        while self.running:
            try:
                with self.app.app_context():
                    self._process_positions()
                time.sleep(self.interval_seconds)
            except Exception as e:
                print(f"Triangulation worker error: {e}")
                time.sleep(self.interval_seconds)
    
    def _process_positions(self):
        """Process device positions using triangulation"""
        # Get observation window from config
        window_seconds = self.app.config.get('OBSERVATION_WINDOW_SECONDS', 10)
        min_stations = self.app.config.get('MIN_STATIONS_FOR_TRIANGULATION', 3)
        smoothing_factor = self.app.config.get('RSSI_SMOOTHING_FACTOR', 0.3)
        
        cutoff_time = datetime.utcnow() - timedelta(seconds=window_seconds)
        
        # Get all non-ignored devices seen recently
        recent_devices = Device.query.filter(
            Device.last_seen >= cutoff_time,
            Device.ignored == False
        ).all()
        
        device_positions = []
        
        for device in recent_devices:
            # Get recent observations for this device
            observations = Observation.query.filter(
                Observation.device_mac == device.mac,
                Observation.timestamp >= cutoff_time
            ).all()
            
            if not observations:
                continue
            
            # Group by station and average RSSI
            station_rssi = {}
            for obs in observations:
                if obs.station_uuid not in station_rssi:
                    station_rssi[obs.station_uuid] = []
                station_rssi[obs.station_uuid].append(obs.rssi)
            
            # Average RSSI per station
            station_avg_rssi = {
                station_uuid: sum(rssi_list) / len(rssi_list)
                for station_uuid, rssi_list in station_rssi.items()
            }
            
            # Get station positions
            station_positions = []
            distances = []
            
            for station_uuid, avg_rssi in station_avg_rssi.items():
                station = Station.query.filter_by(uuid=station_uuid).first()
                if station and station.x_norm is not None and station.y_norm is not None:
                    station_positions.append((station.x_norm, station.y_norm))
                    # Convert RSSI to distance and normalize
                    distance_meters = rssi_to_distance(int(avg_rssi))
                    distance_norm = normalize_distance(distance_meters, map_scale=20.0)
                    distances.append(distance_norm)
            
            # Need at least min_stations for triangulation
            if len(station_positions) >= min_stations:
                position = trilaterate_2d(station_positions, distances)
                
                if position:
                    # Apply smoothing if device had a previous position
                    if device.last_x_norm is not None and device.last_y_norm is not None:
                        current = (device.last_x_norm, device.last_y_norm)
                        position = smooth_position(current, position, smoothing_factor)
                    
                    # Update device position
                    device.last_x_norm = position[0]
                    device.last_y_norm = position[1]
                    
                    # Add to broadcast list
                    device_positions.append(device.to_dict())
        
        # Commit all position updates
        db.session.commit()
        
        # Broadcast positions via SocketIO
        if device_positions and self.socketio:
            self.socketio.emit('device_positions', {
                'timestamp': datetime.utcnow().isoformat(),
                'devices': device_positions
            })


class WebhookWorker:
    """Background worker for webhook notifications"""
    
    def __init__(self, app, new_devices_queue):
        self.app = app
        self.new_devices_queue = new_devices_queue
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the webhook worker thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("Webhook worker started")
    
    def stop(self):
        """Stop the webhook worker thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Webhook worker stopped")
    
    def _run(self):
        """Main worker loop"""
        while self.running:
            try:
                # Get new device from queue (with timeout to allow stopping)
                device_data = self.new_devices_queue.get(timeout=1)
                
                with self.app.app_context():
                    self._send_new_device_webhooks(device_data)
                
            except Exception as e:
                if str(e) != '':  # Ignore empty queue timeout
                    print(f"Webhook worker error: {e}")
    
    def _send_new_device_webhooks(self, device_data):
        """Send webhooks for new device detection"""
        # Get all enabled webhooks for this event type
        webhooks = Webhook.query.filter_by(
            enabled=True,
            event_type='device_first_seen'
        ).all()
        
        for webhook in webhooks:
            payload = {
                'event': 'device_first_seen',
                'mac': device_data['mac'],
                'first_seen': device_data['first_seen'].isoformat() if isinstance(device_data['first_seen'], datetime) else device_data['first_seen'],
                'protocol': device_data['protocol'],
                'station_first_seen': device_data['station_uuid']
            }
            
            send_webhook(webhook, payload)


def send_webhook(webhook: Webhook, payload: Dict) -> bool:
    """
    Send a webhook HTTP POST request.
    
    Args:
        webhook: Webhook configuration
        payload: Data to send
    
    Returns:
        True if successful, False otherwise
    """
    try:
        headers = {'Content-Type': 'application/json'}
        
        # Add HMAC signature if secret is configured
        if webhook.secret:
            payload_bytes = json.dumps(payload).encode('utf-8')
            signature = hmac.new(
                webhook.secret.encode('utf-8'),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            headers['X-Signature'] = f'sha256={signature}'
        
        response = requests.post(
            webhook.url,
            json=payload,
            headers=headers,
            timeout=5
        )
        
        return response.status_code < 400
        
    except Exception as e:
        print(f"Webhook send error ({webhook.name}): {e}")
        return False
