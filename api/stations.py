"""Station API endpoints"""
from flask import request, jsonify
from datetime import datetime
from models import db, Station
from . import api_bp


@api_bp.route('/station/register', methods=['POST'])
def register_station():
    """Register or update a station"""
    data = request.get_json()
    
    if not data or 'station_uuid' not in data:
        return jsonify({'error': 'station_uuid is required'}), 400
    
    station_uuid = data['station_uuid']
    name = data.get('name', station_uuid)
    description = data.get('description', '')
    
    # Find or create station
    station = Station.query.filter_by(uuid=station_uuid).first()
    
    if station:
        # Update existing station
        station.name = name
        station.description = description
        station.last_seen = datetime.utcnow()
    else:
        # Create new station
        station = Station(
            uuid=station_uuid,
            name=name,
            description=description,
            last_seen=datetime.utcnow(),
            active=True
        )
        db.session.add(station)
    
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'station': station.to_dict()
    }), 200


@api_bp.route('/stations/<int:station_id>/position', methods=['POST'])
def update_station_position(station_id):
    """Update station position on map"""
    data = request.get_json()
    
    if not data or 'x_norm' not in data or 'y_norm' not in data:
        return jsonify({'error': 'x_norm and y_norm are required'}), 400
    
    station = Station.query.get(station_id)
    if not station:
        return jsonify({'error': 'Station not found'}), 404
    
    station.x_norm = float(data['x_norm'])
    station.y_norm = float(data['y_norm'])
    
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'station': station.to_dict()
    }), 200


@api_bp.route('/stations', methods=['GET'])
def get_stations():
    """Get all stations"""
    stations = Station.query.all()
    return jsonify({
        'stations': [s.to_dict() for s in stations]
    }), 200


@api_bp.route('/stations/<int:station_id>', methods=['GET'])
def get_station(station_id):
    """Get a specific station"""
    station = Station.query.get(station_id)
    if not station:
        return jsonify({'error': 'Station not found'}), 404
    
    return jsonify(station.to_dict()), 200


@api_bp.route('/stations/<int:station_id>', methods=['PUT'])
def update_station(station_id):
    """Update station details"""
    station = Station.query.get(station_id)
    if not station:
        return jsonify({'error': 'Station not found'}), 404
    
    data = request.get_json()
    
    if 'name' in data:
        station.name = data['name']
    if 'description' in data:
        station.description = data['description']
    if 'active' in data:
        station.active = bool(data['active'])
    
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'station': station.to_dict()
    }), 200


@api_bp.route('/stations/<int:station_id>', methods=['DELETE'])
def delete_station(station_id):
    """Delete a station"""
    station = Station.query.get(station_id)
    if not station:
        return jsonify({'error': 'Station not found'}), 404
    
    db.session.delete(station)
    db.session.commit()
    
    return jsonify({'status': 'ok'}), 200
