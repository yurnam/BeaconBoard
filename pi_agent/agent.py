"""
BeaconBoard Pi Agent

This script runs on Raspberry Pi stations to scan for WiFi and BLE devices
and send observations to the BeaconBoard server.
"""

import json
import time
import requests
import sys
import os
from datetime import datetime
from typing import List, Dict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pi_agent')


class Config:
    """Configuration manager"""
    
    def __init__(self, config_path='/etc/beaconboard/config.json'):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_path}")
            # Return default config
            return {
                'station_uuid': 'pi_station_1',
                'server_url': 'http://localhost:5000',
                'wifi_interface': 'wlan0',
                'ble_interface': 'hci0',
                'batch_interval_sec': 1,
                'max_batch_size': 200
            }
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file: {e}")
            sys.exit(1)
    
    def get(self, key, default=None):
        """Get config value"""
        return self.config.get(key, default)


class BeaconBoardClient:
    """Client for communicating with BeaconBoard server"""
    
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def register_station(self, station_uuid: str, name: str, description: str = '') -> bool:
        """Register this station with the server"""
        url = f"{self.server_url}/api/v1/station/register"
        
        try:
            response = self.session.post(url, json={
                'station_uuid': station_uuid,
                'name': name,
                'description': description
            }, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Station registered: {station_uuid}")
                return True
            else:
                logger.error(f"Failed to register station: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Error registering station: {e}")
            return False
    
    def upload_observations(self, station_uuid: str, observations: List[Dict]) -> bool:
        """Upload a batch of observations to the server"""
        url = f"{self.server_url}/api/v1/observations/batch"
        
        try:
            response = self.session.post(url, json={
                'station_uuid': station_uuid,
                'observations': observations
            }, timeout=10)
            
            if response.status_code == 200:
                logger.debug(f"Uploaded {len(observations)} observations")
                return True
            else:
                logger.error(f"Failed to upload observations: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Error uploading observations: {e}")
            return False


class WiFiScanner:
    """WiFi device scanner using Bettercap API"""
    
    def __init__(self, interface: str, bettercap_url: str = 'http://localhost:8081', 
                 bettercap_user: str = 'user', bettercap_pass: str = 'pass'):
        self.interface = interface
        self.bettercap_url = bettercap_url.rstrip('/')
        self.bettercap_auth = (bettercap_user, bettercap_pass)
        self.session = requests.Session()
        logger.info(f"WiFi scanner initialized on {interface} using Bettercap at {bettercap_url}")
    
    def scan(self, duration: float) -> List[Dict]:
        """
        Scan for WiFi devices using Bettercap API
        
        Returns list of observations with format:
        {
            'device_mac': 'AA:BB:CC:DD:EE:FF',
            'timestamp': 1733142980,
            'rssi': -68,
            'protocol': 'wifi',
            'channel': 6,
            'ssid': 'MyWiFi'
        }
        """
        logger.debug(f"Scanning WiFi for {duration} seconds using Bettercap...")
        time.sleep(duration)
        
        observations = []
        
        try:
            # Get WiFi access points from Bettercap
            response = self.session.get(
                f"{self.bettercap_url}/api/session/wifi",
                auth=self.bettercap_auth,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Process access points
                if 'aps' in data:
                    for ap in data['aps'].values():
                        mac = ap.get('mac', '').upper()
                        if not mac:
                            continue
                        
                        # Get the latest RSSI value
                        rssi = ap.get('rssi', -100)
                        
                        observations.append({
                            'device_mac': mac,
                            'timestamp': int(time.time()),
                            'rssi': rssi,
                            'protocol': 'wifi',
                            'channel': ap.get('channel', 0),
                            'ssid': ap.get('hostname', ap.get('alias', ''))
                        })
                
                # Process WiFi clients (stations)
                if 'clients' in data:
                    for client in data['clients'].values():
                        mac = client.get('mac', '').upper()
                        if not mac:
                            continue
                        
                        rssi = client.get('rssi', -100)
                        
                        observations.append({
                            'device_mac': mac,
                            'timestamp': int(time.time()),
                            'rssi': rssi,
                            'protocol': 'wifi',
                            'channel': client.get('channel', 0),
                            'ssid': ''
                        })
                
                logger.debug(f"Found {len(observations)} WiFi devices")
            else:
                logger.warning(f"Bettercap API returned status {response.status_code}")
                
        except requests.RequestException as e:
            logger.error(f"Error communicating with Bettercap API: {e}")
        except Exception as e:
            logger.error(f"Error parsing Bettercap data: {e}")
        
        return observations


class BLEScanner:
    """BLE device scanner using Bettercap API"""
    
    def __init__(self, interface: str, bettercap_url: str = 'http://localhost:8081',
                 bettercap_user: str = 'user', bettercap_pass: str = 'pass'):
        self.interface = interface
        self.bettercap_url = bettercap_url.rstrip('/')
        self.bettercap_auth = (bettercap_user, bettercap_pass)
        self.session = requests.Session()
        logger.info(f"BLE scanner initialized on {interface} using Bettercap at {bettercap_url}")
    
    def scan(self, duration: float) -> List[Dict]:
        """
        Scan for BLE devices using Bettercap API
        
        Returns list of observations with format:
        {
            'device_mac': '11:22:33:44:55:66',
            'timestamp': 1733142981,
            'rssi': -72,
            'protocol': 'ble'
        }
        """
        logger.debug(f"Scanning BLE for {duration} seconds using Bettercap...")
        time.sleep(duration)
        
        observations = []
        
        try:
            # Get BLE devices from Bettercap
            response = self.session.get(
                f"{self.bettercap_url}/api/session/ble",
                auth=self.bettercap_auth,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Process BLE devices
                if 'devices' in data:
                    for device in data['devices'].values():
                        mac = device.get('mac', '').upper()
                        if not mac:
                            continue
                        
                        # Get the latest RSSI value
                        rssi = device.get('rssi', -100)
                        
                        observations.append({
                            'device_mac': mac,
                            'timestamp': int(time.time()),
                            'rssi': rssi,
                            'protocol': 'ble'
                        })
                
                logger.debug(f"Found {len(observations)} BLE devices")
            else:
                logger.warning(f"Bettercap BLE API returned status {response.status_code}")
                
        except requests.RequestException as e:
            logger.error(f"Error communicating with Bettercap BLE API: {e}")
        except Exception as e:
            logger.error(f"Error parsing Bettercap BLE data: {e}")
        
        return observations


class Agent:
    """Main agent coordinating scanning and uploading"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = BeaconBoardClient(config.get('server_url'))
        
        # Get Bettercap connection details
        bettercap_url = config.get('bettercap_url', 'http://localhost:8081')
        bettercap_user = config.get('bettercap_user', 'user')
        bettercap_pass = config.get('bettercap_pass', 'pass')
        
        self.wifi_scanner = WiFiScanner(
            config.get('wifi_interface'),
            bettercap_url,
            bettercap_user,
            bettercap_pass
        )
        self.ble_scanner = BLEScanner(
            config.get('ble_interface'),
            bettercap_url,
            bettercap_user,
            bettercap_pass
        )
        self.running = False
    
    def start(self):
        """Start the agent"""
        logger.info("Starting BeaconBoard Pi Agent")
        
        # Register with server
        station_uuid = self.config.get('station_uuid')
        name = self.config.get('name', station_uuid)
        description = self.config.get('description', 'Raspberry Pi scanning station')
        
        if not self.client.register_station(station_uuid, name, description):
            logger.warning("Failed to register station, but continuing anyway...")
        
        # Start main loop
        self.running = True
        self.run_loop()
    
    def stop(self):
        """Stop the agent"""
        logger.info("Stopping BeaconBoard Pi Agent")
        self.running = False
    
    def run_loop(self):
        """Main scanning and uploading loop"""
        batch_interval = self.config.get('batch_interval_sec', 1)
        max_batch_size = self.config.get('max_batch_size', 200)
        
        while self.running:
            try:
                # Collect observations
                observations = []
                
                # Scan WiFi and BLE in parallel (simplified for now)
                wifi_obs = self.wifi_scanner.scan(batch_interval / 2)
                ble_obs = self.ble_scanner.scan(batch_interval / 2)
                
                observations.extend(wifi_obs)
                observations.extend(ble_obs)
                
                # Limit batch size
                if len(observations) > max_batch_size:
                    observations = observations[:max_batch_size]
                
                # Upload to server
                if observations:
                    logger.info(f"Uploading {len(observations)} observations")
                    self.client.upload_observations(
                        self.config.get('station_uuid'),
                        observations
                    )
                else:
                    logger.debug("No observations to upload")
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(5)  # Wait before retrying


def main():
    """Main entry point"""
    # Check for config file path argument
    config_path = sys.argv[1] if len(sys.argv) > 1 else '/etc/beaconboard/config.json'
    
    # If config doesn't exist and we're in development, create example
    if not os.path.exists(config_path):
        if config_path == '/etc/beaconboard/config.json':
            # Try local config
            config_path = 'config.json'
            if not os.path.exists(config_path):
                logger.info("Creating example config.json")
                example_config = {
                    'station_uuid': 'pi_station_test',
                    'name': 'Test Station',
                    'description': 'Development test station',
                    'server_url': 'http://localhost:5000',
                    'wifi_interface': 'wlan0',
                    'ble_interface': 'hci0',
                    'bettercap_url': 'http://localhost:8081',
                    'bettercap_user': 'user',
                    'bettercap_pass': 'pass',
                    'batch_interval_sec': 5,
                    'max_batch_size': 200
                }
                with open(config_path, 'w') as f:
                    json.dump(example_config, f, indent=2)
    
    # Load config and start agent
    config = Config(config_path)
    agent = Agent(config)
    
    try:
        agent.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        agent.stop()


if __name__ == '__main__':
    main()
