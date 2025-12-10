"""Station management routes"""
from flask import render_template, request, jsonify
from models import db, Station
from auth import login_required_web
from . import routes_bp
# Import the reboot_requests dict from API module
from api.stations import reboot_requests


@routes_bp.route('/stations')
@login_required_web
def stations_list():
    """Stations management page"""
    stations = Station.query.order_by(Station.created_at.desc()).all()
    return render_template('stations.html', stations=stations)


@routes_bp.route('/stations/<int:station_id>/position', methods=['POST'])
@login_required_web
def update_station_position(station_id):
    """Update station position on map (web route with login auth)"""
    data = request.get_json()
    
    if not data or 'x_norm' not in data or 'y_norm' not in data:
        return jsonify({'error': 'x_norm and y_norm are required'}), 400
    
    station = Station.query.get(station_id)
    if not station:
        return jsonify({'error': 'Station not found'}), 404
    
    try:
        station.x_norm = float(data['x_norm'])
        station.y_norm = float(data['y_norm'])
        db.session.commit()
        
        return jsonify({
            'status': 'ok',
            'station': station.to_dict()
        }), 200
    except (ValueError, TypeError) as e:
        return jsonify({'error': 'Invalid coordinate values'}), 400


@routes_bp.route('/stations/reboot-all', methods=['POST'])
@login_required_web
def reboot_all_stations():
    """Request all stations to reboot"""
    stations = Station.query.filter_by(active=True).all()
    
    if not stations:
        return jsonify({'error': 'No active stations found'}), 404
    
    # Set reboot flag for all active stations
    for station in stations:
        reboot_requests[station.uuid] = True
    
    return jsonify({
        'status': 'ok',
        'message': f'Reboot requested for {len(stations)} station(s)',
        'stations': [s.uuid for s in stations]
    }), 200
