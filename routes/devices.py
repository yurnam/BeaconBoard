"""Device management routes"""
from flask import render_template, request
from models import Device
from . import routes_bp


@routes_bp.route('/devices')
def devices_list():
    """Devices management page"""
    show_ignored = request.args.get('show_ignored', 'false').lower() == 'true'
    unnamed_only = request.args.get('unnamed_only', 'false').lower() == 'true'
    
    query = Device.query
    
    if not show_ignored:
        query = query.filter_by(ignored=False)
    
    if unnamed_only:
        query = query.filter(Device.friendly_name.is_(None))
    
    devices = query.order_by(Device.last_seen.desc()).all()
    
    return render_template('devices.html', 
                         devices=devices,
                         show_ignored=show_ignored,
                         unnamed_only=unnamed_only)
