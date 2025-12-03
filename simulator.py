"""Simulation mode for testing with mock stations and devices"""
import random
import time
import threading
import requests
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SimulationWorker:
    """Background worker that generates mock observation data from test stations"""
    
    # Test station configurations
    TEST_STATIONS = [
        {
            'uuid': 'sim_station_1',
            'name': 'Test Station 1',
            'description': 'Simulated station in bedroom',
            'x_norm': 0.25,
            'y_norm': 0.25
        },
        {
            'uuid': 'sim_station_2',
            'name': 'Test Station 2',
            'description': 'Simulated station in kitchen',
            'x_norm': 0.75,
            'y_norm': 0.25
        },
        {
            'uuid': 'sim_station_3',
            'name': 'Test Station 3',
            'description': 'Simulated station in living room',
            'x_norm': 0.5,
            'y_norm': 0.75
        }
    ]
    
    # Mock devices that move around
    MOCK_DEVICES = [
        {'mac': 'SIM:AA:BB:CC:DD:01', 'protocol': 'wifi', 'x': 0.3, 'y': 0.3, 'vx': 0.01, 'vy': 0.01},
        {'mac': 'SIM:AA:BB:CC:DD:02', 'protocol': 'wifi', 'x': 0.7, 'y': 0.3, 'vx': -0.01, 'vy': 0.01},
        {'mac': 'SIM:11:22:33:44:01', 'protocol': 'ble', 'x': 0.5, 'y': 0.5, 'vx': 0.01, 'vy': -0.01},
        {'mac': 'SIM:11:22:33:44:02', 'protocol': 'ble', 'x': 0.4, 'y': 0.6, 'vx': -0.01, 'vy': -0.01},
    ]
    
    def __init__(self, app, interval_seconds=2):
        """Initialize the simulation worker
        
        Args:
            app: Flask application instance
            interval_seconds: How often to generate observations (default 2 seconds)
        """
        self.app = app
        self.interval = interval_seconds
        self.enabled = False
        self.thread = None
        self.stop_event = threading.Event()
        self.server_url = None
        
        # Device positions for simulation
        self.device_positions = [d.copy() for d in self.MOCK_DEVICES]
        
    def start(self, server_url='http://127.0.0.1:5000'):
        """Start the simulation worker"""
        if self.thread and self.thread.is_alive():
            logger.warning("Simulation worker already running")
            return
            
        self.server_url = server_url
        self.stop_event.clear()
        self.enabled = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Simulation worker started")
        
    def stop(self):
        """Stop the simulation worker"""
        self.enabled = False
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Simulation worker stopped")
        
    def _run(self):
        """Main worker loop"""
        # First, register all test stations
        self._register_stations()
        
        # Then generate observations in a loop
        while not self.stop_event.is_set():
            try:
                if self.enabled:
                    self._generate_observations()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Error in simulation worker: {e}")
                time.sleep(self.interval)
                
    def _register_stations(self):
        """Register all test stations with the server"""
        for station in self.TEST_STATIONS:
            try:
                response = requests.post(
                    f"{self.server_url}/api/v1/station/register",
                    json={
                        'station_uuid': station['uuid'],
                        'name': station['name'],
                        'description': station['description']
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    logger.info(f"Registered test station: {station['name']}")
                    
                    # Also set the station position
                    station_data = response.json().get('station', {})
                    station_id = station_data.get('id')
                    if station_id:
                        pos_response = requests.post(
                            f"{self.server_url}/api/v1/stations/{station_id}/position",
                            json={
                                'x_norm': station['x_norm'],
                                'y_norm': station['y_norm']
                            },
                            timeout=5
                        )
                        if pos_response.status_code == 200:
                            logger.info(f"Set position for test station: {station['name']}")
                else:
                    logger.error(f"Failed to register station {station['name']}: {response.status_code}")
            except Exception as e:
                logger.error(f"Error registering station {station['name']}: {e}")
                
    def _generate_observations(self):
        """Generate mock observations from all stations"""
        # Update device positions (simulate movement)
        self._update_device_positions()
        
        # Generate observations from each station
        for station in self.TEST_STATIONS:
            observations = []
            
            for device in self.device_positions:
                # Calculate distance from station to device
                dx = device['x'] - station['x_norm']
                dy = device['y'] - station['y_norm']
                distance = (dx**2 + dy**2) ** 0.5
                
                # Convert distance to RSSI (inverse of triangulation)
                # Using path loss model: RSSI = TxPower - 10*n*log10(distance)
                # Assume TxPower = -30, n = 2
                if distance < 0.01:
                    distance = 0.01  # Avoid log(0)
                    
                rssi = -30 - (10 * 2 * (distance * 100) ** 0.5)  # Scale distance by 100
                rssi = int(rssi + random.uniform(-5, 5))  # Add noise
                
                # Clamp RSSI to realistic range
                rssi = max(-100, min(-20, rssi))
                
                # Add observation
                observations.append({
                    'device_mac': device['mac'],
                    'timestamp': int(time.time()),
                    'rssi': rssi,
                    'protocol': device['protocol'],
                    'channel': random.randint(1, 11) if device['protocol'] == 'wifi' else None,
                    'ssid': 'SimulatedWiFi' if device['protocol'] == 'wifi' else None
                })
            
            # Send batch to server
            try:
                response = requests.post(
                    f"{self.server_url}/api/v1/observations/batch",
                    json={
                        'station_uuid': station['uuid'],
                        'observations': observations
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    logger.debug(f"Sent {len(observations)} observations from {station['name']}")
                else:
                    logger.error(f"Failed to send observations from {station['name']}: {response.status_code}")
            except Exception as e:
                logger.error(f"Error sending observations from {station['name']}: {e}")
                
    def _update_device_positions(self):
        """Update mock device positions to simulate movement"""
        for device in self.device_positions:
            # Update position
            device['x'] += device['vx']
            device['y'] += device['vy']
            
            # Bounce off walls (0-1 normalized space)
            if device['x'] <= 0 or device['x'] >= 1:
                device['vx'] *= -1
                device['x'] = max(0, min(1, device['x']))
            if device['y'] <= 0 or device['y'] >= 1:
                device['vy'] *= -1
                device['y'] = max(0, min(1, device['y']))
            
            # Add random jitter to velocity
            device['vx'] += random.uniform(-0.002, 0.002)
            device['vy'] += random.uniform(-0.002, 0.002)
            
            # Clamp velocity
            max_vel = 0.02
            device['vx'] = max(-max_vel, min(max_vel, device['vx']))
            device['vy'] = max(-max_vel, min(max_vel, device['vy']))


# Global simulation worker instance
simulation_worker = None


def get_simulation_worker(app=None):
    """Get or create the global simulation worker"""
    global simulation_worker
    if simulation_worker is None and app is not None:
        simulation_worker = SimulationWorker(app)
    return simulation_worker
