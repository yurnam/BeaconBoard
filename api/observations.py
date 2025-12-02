"""Observations API endpoints"""
from flask import request, jsonify
from datetime import datetime
from models import db, Station, Device, Observation
from . import api_bp
import queue

# Queue for new devices (for webhook notifications)
new_devices_queue = queue.Queue()


@api_bp.route('/observations/batch', methods=['POST'])
def upload_observations():
    """Upload a batch of observations from a station"""
    data = request.get_json()
    
    if not data or 'station_uuid' not in data or 'observations' not in data:
        return jsonify({'error': 'station_uuid and observations are required'}), 400
    
    station_uuid = data['station_uuid']
    observations_data = data['observations']
    
    # Ensure station exists and update last_seen
    station = Station.query.filter_by(uuid=station_uuid).first()
    if not station:
        return jsonify({'error': 'Station not registered'}), 404
    
    station.last_seen = datetime.utcnow()
    
    # Process each observation
    for obs_data in observations_data:
        device_mac = obs_data.get('device_mac')
        if not device_mac:
            continue
        
        # Parse timestamp
        timestamp = obs_data.get('timestamp')
        if isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()
        
        # Find or create device
        device = Device.query.filter_by(mac=device_mac).first()
        is_new_device = False
        
        if not device:
            is_new_device = True
            device = Device(
                mac=device_mac,
                first_seen=timestamp,
                last_seen=timestamp,
                protocol=obs_data.get('protocol', 'wifi')
            )
            db.session.add(device)
            db.session.flush()  # Get the device ID
        else:
            # Update last_seen (both should be timezone-naive UTC)
            if device.last_seen is None or timestamp > device.last_seen:
                device.last_seen = timestamp
            
            # Update protocol if needed
            if obs_data.get('protocol') and device.protocol != obs_data['protocol']:
                if device.protocol == 'wifi' and obs_data['protocol'] == 'ble':
                    device.protocol = 'both'
                elif device.protocol == 'ble' and obs_data['protocol'] == 'wifi':
                    device.protocol = 'both'
        
        # Create observation
        observation = Observation(
            device_mac=device_mac,
            station_uuid=station_uuid,
            timestamp=timestamp,
            rssi=obs_data.get('rssi', -100),
            protocol=obs_data.get('protocol', 'wifi'),
            channel=obs_data.get('channel'),
            ssid=obs_data.get('ssid')
        )
        db.session.add(observation)
        
        # Queue new device for webhook notification
        if is_new_device:
            new_devices_queue.put({
                'device_id': device.id,
                'mac': device.mac,
                'first_seen': device.first_seen,
                'protocol': device.protocol,
                'station_uuid': station_uuid
            })
    
    db.session.commit()
    
    return jsonify({'status': 'ok'}), 200


@api_bp.route('/observations', methods=['GET'])
def get_observations():
    """Get recent observations (for debugging)"""
    limit = request.args.get('limit', 100, type=int)
    device_mac = request.args.get('device_mac')
    station_uuid = request.args.get('station_uuid')
    
    query = Observation.query
    
    if device_mac:
        query = query.filter_by(device_mac=device_mac)
    if station_uuid:
        query = query.filter_by(station_uuid=station_uuid)
    
    observations = query.order_by(Observation.timestamp.desc()).limit(limit).all()
    
    return jsonify({
        'observations': [o.to_dict() for o in observations]
    }), 200
