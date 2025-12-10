"""Station management routes"""
from flask import render_template
from models import Station
from auth import login_required_web
from . import routes_bp


@routes_bp.route('/stations')
@login_required_web
def stations_list():
    """Stations management page"""
    stations = Station.query.order_by(Station.created_at.desc()).all()
    return render_template('stations.html', stations=stations)
