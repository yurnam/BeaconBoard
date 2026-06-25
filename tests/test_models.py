"""Tests for database models."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import datetime


class TestStationModel:
    """Tests for Station model."""

    def test_create_station(self, app):
        from models import Station
        station = Station(
            uuid='test-station-uuid',
            name='Test Station',
            description='A test station',
        )
        with app.app_context():
            db.session.add(station)
            db.session.commit()

        retrieved = Station.query.filter_by(uuid='test-station-uuid').first()
        assert retrieved is not None
        assert retrieved.name == 'Test Station'

    def test_station_to_dict(self, client):
        from models import Station
        admin = User.query.filter_by(username='admin').first()
        station = Station(
            uuid='dict-station-1',
            name='Dict Station',
            description='A description',
            x_norm=0.5,
            y_norm=0.75,
            active=True,
        )
        with client.application.app_context():
            db.session.add(station)
            db.session.commit()

        result = station.to_dict()
        assert result['uuid'] == 'dict-station-1'
        assert result['name'] == 'Dict Station'
        assert result['x_norm'] == 0.5
        assert result['y_norm'] == 0.75
        assert result['active'] is True
        assert 'id' in result

    def test_station_last_seen_updates(self, app):
        from models import Station
        station = Station(
            uuid='seen-station',
            name='Seen Station',
        )
        with app.app_context():
            db.session.add(station)
            db.session.flush()
            old_seen = station.last_seen
            station.last_seen = datetime.utcnow()
            db.session.commit()

        updated = Station.query.get(station.id)
        assert updated is not None


class TestDeviceModel:
    """Tests for Device model."""

    def test_create_device(self, app):
        from models import Device
        device = Device(
            mac='aa:bb:cc:dd:ee:ff',
            protocol='wifi',
        )
        with app.app_context():
            db.session.add(device)
            db.session.commit()

        retrieved = Device.query.filter_by(mac='aa:bb:cc:dd:ee:ff').first()
        assert retrieved is not None
        assert retrieved.protocol == 'wifi'

    def test_device_default_values(self, app):
        from models import Device
        device = Device(mac='11:22:33:44:55:66')
        with app.app_context():
            db.session.add(device)
            db.session.flush()

        assert device.icon == 'question'
        assert device.color == '#3498db'
        assert device.ignored is False
        assert device.authorized is False
        assert device.protocol == 'wifi'

    def test_device_to_dict(self, app):
        from models import Device
        device = Device(
            mac='aa:bb:cc:dd:ee:ff',
            friendly_name='MyPhone',
            icon='phone',
            color='#ff5733',
            last_rssi=-65,
            protocol='both',
        )
        with app.app_context():
            db.session.add(device)
            db.session.flush()

        result = device.to_dict()
        assert result['mac'] == 'aa:bb:cc:dd:ee:ff'
        assert result['friendly_name'] == 'MyPhone'
        assert result['icon'] == 'phone'
        assert result['color'] == '#ff5733'
        assert result['last_rssi'] == -65
        assert result['protocol'] == 'both'


class TestObservationModel:
    """Tests for Observation model."""

    def test_create_observation(self, app):
        from models import Observation
        obs = Observation(
            device_mac='aa:bb:cc:dd:ee:ff',
            station_uuid='station-1',
            rssi=-55,
            protocol='wifi',
        )
        with app.app_context():
            db.session.add(obs)
            db.session.flush()

        assert obs.id is not None
        assert obs.rssi == -55

    def test_observation_to_dict(self, app):
        from models import Observation
        obs = Observation(
            device_mac='aa:bb:cc:dd:ee:ff',
            station_uuid='station-1',
            rssi=-60,
            protocol='ble',
            channel=37,
            ssid='test-network',
        )
        db.session.add(obs)
        db.session.flush()

        result = obs.to_dict()
        assert result['device_mac'] == 'aa:bb:cc:dd:ee:ff'
        assert result['station_uuid'] == 'station-1'
        assert result['rssi'] == -60
        assert result['protocol'] == 'ble'


class TestWebhookModel:
    """Tests for Webhook model."""

    def test_create_webhook(self, app):
        from models import Webhook
        webhook = Webhook(
            name='Test Webhook',
            url='http://example.com/webhook',
        )
        with app.app_context():
            db.session.add(webhook)
            db.session.flush()

        assert webhook.id is not None
        assert webhook.enabled is True

    def test_webhook_to_dict_includes_has_secret(self, app):
        from models import Webhook
        webhook = Webhook(
            name='With Secret',
            url='http://example.com/hook',
            secret='supersecret',
        )
        db.session.add(webhook)
        db.session.flush()

        result = webhook.to_dict()
        assert result['has_secret'] is True
        assert result['enabled'] is True


class TestUserModel:
    """Tests for User model."""

    def test_set_and_check_password(self):
        user = User(username='testuser')
        user.set_password('mypassword123')
        assert user.check_password('mypassword123') is True
        assert user.check_password('wrongpassword') is False

    def test_user_to_dict(self, app):
        user = User(
            username='dictuser',
            is_admin=True,
            active=False,
        )
        with app.app_context():
            db.session.add(user)
            db.session.flush()

        result = user.to_dict()
        assert result['username'] == 'dictuser'
        assert result['is_admin'] is True
        assert result['active'] is False
        assert 'password_hash' not in result


class TestApiKeyModel:
    """Tests for APIKey model."""

    def test_api_key_to_dict_preview(self, app):
        admin = User.query.filter_by(username='admin').first()
        key_obj = APIKey(
            name='preview-key',
            description='',
            user_id=admin.id,
            key='abcdefghijklmnop' * 4,
        )
        db.session.add(key_obj)
        db.session.flush()

        result = key_obj.to_dict(include_key=False)
        assert result['key'] != 'abcdefghijklmnop' * 4  # Not the full key
        assert '...' in result['key_preview']


class TestMapModel:
    """Tests for Map model."""

    def test_create_map(self, app):
        from models import Map
        test_map = Map(
            name='Test Map',
            image_filename='map.png',
            width_px=1920,
            height_px=1080,
            width_meters=30.0,
            height_meters=20.0,
        )
        with app.app_context():
            db.session.add(test_map)
            db.session.flush()

        assert test_map.id is not None
        assert test_map.is_active is True

    def test_map_to_dict(self, client):
        from models import Map
        test_map = Map(
            name='DictMap',
            image_filename='dict_map.png',
            width_px=800,
            height_px=600,
            width_meters=12.0,
            height_meters=9.0,
            is_active=False,
        )
        with client.application.app_context():
            db.session.add(test_map)
            db.session.flush()

        result = test_map.to_dict()
        assert result['name'] == 'DictMap'
        assert result['width_px'] == 800
        assert result['height_meters'] == 9.0
        assert result['is_active'] is False
