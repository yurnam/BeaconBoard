"""Simulation mode page route"""
from flask import render_template
from auth import login_required_web
from . import routes_bp


@routes_bp.route('/simulation')
@login_required_web
def simulation():
    """Simulation mode control page"""
    return render_template('simulation.html')
