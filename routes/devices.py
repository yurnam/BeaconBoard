"""Device management routes"""
from flask import render_template, request
from datetime import datetime, timedelta
from models import Device
from . import routes_bp


@routes_bp.route('/devices')
def devices_list():
    """Devices management page"""
    show_ignored = request.args.get('show_ignored', 'false').lower() == 'true'
    unnamed_only = request.args.get('unnamed_only', 'false').lower() == 'true'
    
    # Get config value for inactive timeout (default 5 minutes = 300 seconds)
    from flask import current_app
    inactive_timeout = current_app.config.get('DEVICE_INACTIVE_TIMEOUT_SECONDS', 300)
    cutoff_time = datetime.utcnow() - timedelta(seconds=inactive_timeout)
    
    # Build query
    query = Device.query
    
    if not show_ignored:
        query = query.filter_by(ignored=False)
    
    if unnamed_only:
        query = query.filter(Device.friendly_name.is_(None))
    
    # Separate active and inactive devices
    all_devices = query.order_by(Device.last_seen.desc()).all()
    
    active_devices = [d for d in all_devices if d.last_seen and d.last_seen >= cutoff_time]
    inactive_devices = [d for d in all_devices if not d.last_seen or d.last_seen < cutoff_time]
    
    return render_template('devices.html', 
                         active_devices=active_devices,
                         inactive_devices=inactive_devices,
                         show_ignored=show_ignored,
                         unnamed_only=unnamed_only)
