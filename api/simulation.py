"""API endpoints for controlling simulation mode"""
from flask import jsonify, request, current_app
from . import api_bp
from simulator import get_simulation_worker
import logging

logger = logging.getLogger(__name__)


@api_bp.route('/simulation/status', methods=['GET'])
def get_simulation_status():
    """Get current simulation status"""
    worker = get_simulation_worker()
    return jsonify({
        'enabled': worker.enabled if worker else False,
        'running': worker.thread.is_alive() if worker and worker.thread else False
    })


@api_bp.route('/simulation/start', methods=['POST'])
def start_simulation():
    """Start simulation mode"""
    try:
        worker = get_simulation_worker(current_app._get_current_object())
        
        # Get server URL from request or use default
        data = request.get_json() or {}
        server_url = data.get('server_url', 'http://127.0.0.1:5000')
        
        worker.start(server_url)
        
        return jsonify({
            'status': 'ok',
            'message': 'Simulation started',
            'test_stations': len(worker.TEST_STATIONS),
            'mock_devices': len(worker.MOCK_DEVICES)
        })
    except Exception as e:
        logger.error(f"Error starting simulation: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@api_bp.route('/simulation/stop', methods=['POST'])
def stop_simulation():
    """Stop simulation mode"""
    try:
        worker = get_simulation_worker()
        if worker:
            worker.stop()
        
        return jsonify({
            'status': 'ok',
            'message': 'Simulation stopped'
        })
    except Exception as e:
        logger.error(f"Error stopping simulation: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@api_bp.route('/simulation/info', methods=['GET'])
def get_simulation_info():
    """Get information about simulation configuration"""
    worker = get_simulation_worker()
    if not worker:
        return jsonify({
            'test_stations': [],
            'mock_devices': []
        })
    
    return jsonify({
        'test_stations': worker.TEST_STATIONS,
        'mock_devices': [
            {
                'mac': d['mac'],
                'protocol': d['protocol']
            } for d in worker.MOCK_DEVICES
        ]
    })
