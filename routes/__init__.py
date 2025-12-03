"""Web UI routes"""
from flask import Blueprint

routes_bp = Blueprint('routes', __name__)

from . import main, stations, devices, maps, simulation
