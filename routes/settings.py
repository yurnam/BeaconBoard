from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from models import db, Webhook
from auth import login_required_web
from datetime import datetime

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
@login_required_web
def settings_page():
    """Settings page with configuration options"""
    from config import Config
    
    # Get all webhooks
    webhooks = Webhook.query.all()
    
    # Get current configuration values
    config_values = {
        'device_inactive_timeout': Config.DEVICE_INACTIVE_TIMEOUT_SECONDS,
        'unauthorized_notification_timeout': Config.UNAUTHORIZED_DEVICE_NOTIFICATION_TIMEOUT_SECONDS,
        'observation_window': Config.OBSERVATION_WINDOW_SECONDS,
        'triangulation_interval': Config.TRIANGULATION_INTERVAL_SECONDS,
        'min_stations_triangulation': Config.MIN_STATIONS_FOR_TRIANGULATION,
        'rssi_smoothing_factor': Config.RSSI_SMOOTHING_FACTOR,
        'webhook_timeout': Config.WEBHOOK_TIMEOUT_SECONDS,
        'webhook_retry_attempts': Config.WEBHOOK_RETRY_ATTEMPTS,
    }
    
    return render_template('settings.html', webhooks=webhooks, config=config_values)


@settings_bp.route('/api/v1/config/update', methods=['POST'])
@login_required_web
def update_config():
    """Update configuration values"""
    try:
        data = request.json
        from config import Config
        
        # Update configuration values if provided
        if 'device_inactive_timeout' in data:
            Config.DEVICE_INACTIVE_TIMEOUT_SECONDS = int(data['device_inactive_timeout'])
        
        if 'unauthorized_notification_timeout' in data:
            Config.UNAUTHORIZED_DEVICE_NOTIFICATION_TIMEOUT_SECONDS = int(data['unauthorized_notification_timeout'])
        
        if 'observation_window' in data:
            Config.OBSERVATION_WINDOW_SECONDS = int(data['observation_window'])
        
        if 'triangulation_interval' in data:
            Config.TRIANGULATION_INTERVAL_SECONDS = int(data['triangulation_interval'])
        
        if 'min_stations_triangulation' in data:
            Config.MIN_STATIONS_FOR_TRIANGULATION = int(data['min_stations_triangulation'])
        
        if 'rssi_smoothing_factor' in data:
            Config.RSSI_SMOOTHING_FACTOR = float(data['rssi_smoothing_factor'])
        
        if 'webhook_timeout' in data:
            Config.WEBHOOK_TIMEOUT_SECONDS = int(data['webhook_timeout'])
        
        if 'webhook_retry_attempts' in data:
            Config.WEBHOOK_RETRY_ATTEMPTS = int(data['webhook_retry_attempts'])
        
        return jsonify({'status': 'success', 'message': 'Configuration updated successfully'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@settings_bp.route('/api/v1/webhooks', methods=['GET'])
@login_required_web
def list_webhooks():
    """List all webhooks"""
    webhooks = Webhook.query.all()
    return jsonify({
        'webhooks': [w.to_dict() for w in webhooks]
    })


@settings_bp.route('/api/v1/webhooks', methods=['POST'])
@login_required_web
def create_webhook():
    """Create a new webhook"""
    try:
        data = request.json
        
        webhook = Webhook(
            name=data.get('name', ''),
            url=data['url'],
            secret=data.get('secret', ''),
            event_type=data.get('event_type', 'device_first_seen'),
            enabled=data.get('enabled', True)
        )
        
        db.session.add(webhook)
        db.session.commit()
        
        return jsonify({'status': 'success', 'webhook': webhook.to_dict()}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 400


@settings_bp.route('/api/v1/webhooks/<int:webhook_id>', methods=['PUT'])
@login_required_web
def update_webhook(webhook_id):
    """Update a webhook"""
    try:
        webhook = Webhook.query.get_or_404(webhook_id)
        data = request.json
        
        if 'name' in data:
            webhook.name = data['name']
        if 'url' in data:
            webhook.url = data['url']
        if 'secret' in data:
            webhook.secret = data['secret']
        if 'event_type' in data:
            webhook.event_type = data['event_type']
        if 'enabled' in data:
            webhook.enabled = data['enabled']
        
        db.session.commit()
        
        return jsonify({'status': 'success', 'webhook': webhook.to_dict()})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 400


@settings_bp.route('/api/v1/webhooks/<int:webhook_id>', methods=['DELETE'])
@login_required_web
def delete_webhook(webhook_id):
    """Delete a webhook"""
    try:
        webhook = Webhook.query.get_or_404(webhook_id)
        db.session.delete(webhook)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Webhook deleted'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 400


@settings_bp.route('/api/v1/webhooks/<int:webhook_id>/test', methods=['POST'])
@login_required_web
def test_webhook(webhook_id):
    """Send a test webhook"""
    try:
        webhook = Webhook.query.get_or_404(webhook_id)
        import requests
        import json
        import hmac
        import hashlib
        
        test_payload = {
            'event': 'test',
            'message': 'This is a test webhook notification',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        headers = {'Content-Type': 'application/json'}
        
        # Add HMAC signature if secret is set
        if webhook.secret:
            payload_bytes = json.dumps(test_payload).encode('utf-8')
            signature = hmac.new(
                webhook.secret.encode('utf-8'),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            headers['X-Signature'] = f'sha256={signature}'
        
        response = requests.post(
            webhook.url,
            json=test_payload,
            headers=headers,
            timeout=5
        )
        
        return jsonify({
            'status': 'success',
            'message': f'Test webhook sent. Response: {response.status_code}',
            'response_code': response.status_code
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
