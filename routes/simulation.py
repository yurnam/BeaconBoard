"""Simulation mode page route"""
from flask import render_template
from . import routes_bp


@routes_bp.route('/simulation')
def simulation():
    """Simulation mode control page"""
    return render_template('simulation.html')
