"""Main routes (dashboard, etc.)"""
from flask import render_template
from datetime import datetime, timedelta
from models import db, Station, Device, Observation
from . import routes_bp


@routes_bp.route('/')
def index():
    """Dashboard page"""
    # Get statistics
    total_stations = Station.query.count()
    active_stations = Station.query.filter_by(active=True).count()
    total_devices = Device.query.count()
    ignored_devices = Device.query.filter_by(ignored=True).count()
    
    # Recently seen devices (last 5 minutes)
    recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
    recent_devices = Device.query.filter(
        Device.last_seen >= recent_cutoff,
        Device.ignored == False
    ).order_by(Device.last_seen.desc()).limit(10).all()
    
    return render_template('dashboard.html',
                         total_stations=total_stations,
                         active_stations=active_stations,
                         total_devices=total_devices,
                         ignored_devices=ignored_devices,
                         recent_devices=recent_devices)
