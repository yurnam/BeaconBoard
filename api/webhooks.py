"""Webhook API endpoints"""
from flask import request, jsonify
from models import db, Webhook
from . import api_bp


@api_bp.route('/webhooks', methods=['GET'])
def get_webhooks():
    """Get all webhooks"""
    webhooks = Webhook.query.all()
    return jsonify({
        'webhooks': [w.to_dict() for w in webhooks]
    }), 200


@api_bp.route('/webhooks', methods=['POST'])
def create_webhook():
    """Create a new webhook"""
    data = request.get_json()
    
    if not data or 'name' not in data or 'url' not in data:
        return jsonify({'error': 'name and url are required'}), 400
    
    webhook = Webhook(
        name=data['name'],
        url=data['url'],
        secret=data.get('secret'),
        enabled=data.get('enabled', True),
        event_type=data.get('event_type', 'device_first_seen')
    )
    
    db.session.add(webhook)
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'webhook': webhook.to_dict()
    }), 201


@api_bp.route('/webhooks/<int:webhook_id>', methods=['GET'])
def get_webhook(webhook_id):
    """Get a specific webhook"""
    webhook = Webhook.query.get(webhook_id)
    if not webhook:
        return jsonify({'error': 'Webhook not found'}), 404
    
    return jsonify(webhook.to_dict()), 200


@api_bp.route('/webhooks/<int:webhook_id>', methods=['PUT'])
def update_webhook(webhook_id):
    """Update webhook details"""
    webhook = Webhook.query.get(webhook_id)
    if not webhook:
        return jsonify({'error': 'Webhook not found'}), 404
    
    data = request.get_json()
    
    if 'name' in data:
        webhook.name = data['name']
    if 'url' in data:
        webhook.url = data['url']
    if 'secret' in data:
        webhook.secret = data['secret']
    if 'enabled' in data:
        webhook.enabled = bool(data['enabled'])
    if 'event_type' in data:
        webhook.event_type = data['event_type']
    
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'webhook': webhook.to_dict()
    }), 200


@api_bp.route('/webhooks/<int:webhook_id>', methods=['DELETE'])
def delete_webhook(webhook_id):
    """Delete a webhook"""
    webhook = Webhook.query.get(webhook_id)
    if not webhook:
        return jsonify({'error': 'Webhook not found'}), 404
    
    db.session.delete(webhook)
    db.session.commit()
    
    return jsonify({'status': 'ok'}), 200


@api_bp.route('/webhooks/<int:webhook_id>/test', methods=['POST'])
def test_webhook(webhook_id):
    """Send a test event to the webhook"""
    webhook = Webhook.query.get(webhook_id)
    if not webhook:
        return jsonify({'error': 'Webhook not found'}), 404
    
    # Import here to avoid circular dependency
    from workers import send_webhook
    
    test_data = {
        'event': 'test',
        'message': 'This is a test webhook event',
        'webhook_id': webhook.id
    }
    
    success = send_webhook(webhook, test_data)
    
    if success:
        return jsonify({'status': 'ok', 'message': 'Test webhook sent'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Failed to send webhook'}), 500
