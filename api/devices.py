"""Device API endpoints"""
from flask import request, jsonify
from models import db, Device
from . import api_bp


@api_bp.route('/devices', methods=['GET'])
def get_devices():
    """Get all devices with optional filters"""
    show_ignored = request.args.get('show_ignored', 'true').lower() == 'true'
    unnamed_only = request.args.get('unnamed_only', 'false').lower() == 'true'
    search = request.args.get('search', '')
    
    query = Device.query
    
    if not show_ignored:
        query = query.filter_by(ignored=False)
    
    if unnamed_only:
        query = query.filter(Device.friendly_name.is_(None))
    
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            db.or_(
                Device.mac.like(search_pattern),
                Device.friendly_name.like(search_pattern)
            )
        )
    
    devices = query.order_by(Device.last_seen.desc()).all()
    
    return jsonify({
        'devices': [d.to_dict() for d in devices]
    }), 200


@api_bp.route('/devices/<int:device_id>', methods=['GET'])
def get_device(device_id):
    """Get a specific device"""
    device = Device.query.get(device_id)
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    return jsonify(device.to_dict()), 200


@api_bp.route('/devices/<int:device_id>', methods=['PUT'])
def update_device(device_id):
    """Update device details"""
    device = Device.query.get(device_id)
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    data = request.get_json()
    
    if 'friendly_name' in data:
        device.friendly_name = data['friendly_name']
    if 'icon' in data:
        device.icon = data['icon']
    if 'color' in data:
        device.color = data['color']
    if 'ignored' in data:
        device.ignored = bool(data['ignored'])
    
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'device': device.to_dict()
    }), 200


@api_bp.route('/devices/<int:device_id>', methods=['DELETE'])
def delete_device(device_id):
    """Delete a device"""
    device = Device.query.get(device_id)
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    db.session.delete(device)
    db.session.commit()
    
    return jsonify({'status': 'ok'}), 200
