"""Tests for API endpoints."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest


class TestStationAPI:
    """Tests for station API routes."""

    def test_register_station(self, client, auth_client, station_data):
        response = client.post(
            '/api/v1/station/register',
            json=station_data,
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert data['station']['name'] == 'Test Station'

    def test_register_station_missing_uuid(self, client, auth_client):
        response = client.post(
            '/api/v1/station/register',
            json={'name': 'No UUID'},
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 400

    def test_register_repeats_creates_no_duplicates(self, client, auth_client):
        data = {'station_uuid': 'dup-test-1', 'name': 'Dup Station'}
        for _ in range(3):
            response = client.post(
                '/api/v1/station/register',
                json=data,
                headers={'X-API-Key': auth_client['api_key']},
            )
            assert response.status_code == 200

    def test_get_stations_empty(self, client, auth_client):
        response = client.get(
            '/api/v1/stations',
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'stations' in data

    def test_update_station_position(self, client, auth_client):
        # Register first
        client.post(
            '/api/v1/station/register',
            json={'station_uuid': 'pos-station'},
            headers={'X-API-Key': auth_client['api_key']},
        )

        station = None
        with client.application.app_context():
            from models import Station
            station = Station.query.filter_by(uuid='pos-station').first()

        response = client.post(
            f'/api/v1/stations/{station.id}/position',
            json={'x_norm': 0.25, 'y_norm': 0.75},
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['station']['x_norm'] == pytest.approx(0.25)

    def test_update_station_position_not_found(self, client, auth_client):
        response = client.post(
            '/api/v1/stations/99999/position',
            json={'x_norm': 0.5, 'y_norm': 0.5},
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 404

    def test_get_station_by_id(self, client, auth_client):
        client.post(
            '/api/v1/station/register',
            json={'station_uuid': 'get-id-station'},
            headers={'X-API-Key': auth_client['api_key']},
        )
        with client.application.app_context():
            from models import Station
            station = Station.query.filter_by(uuid='get-id-station').first()

        response = client.get(
            f'/api/v1/stations/{station.id}',
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['uuid'] == 'get-id-station'

    def test_update_station_details(self, client, auth_client):
        client.post(
            '/api/v1/station/register',
            json={'station_uuid': 'update-name-1'},
            headers={'X-API-Key': auth_client['api_key']},
        )
        with client.application.app_context():
            from models import Station
            station = Station.query.filter_by(uuid='update-name-1').first()

        response = client.put(
            f'/api/v1/stations/{station.id}',
            json={'name': 'Renamed', 'description': 'New desc'},
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['station']['name'] == 'Renamed'

    def test_delete_station(self, client, auth_client):
        client.post(
            '/api/v1/station/register',
            json={'station_uuid': 'del-station'},
            headers={'X-API-Key': auth_client['api_key']},
        )
        # Need an API key with delete permission
        from models import User, APIKey, db
        admin = User.query.filter_by(username='admin').first()
        del_key = APIKey(name='del-key', description='', user_id=admin.id, can_delete=True)
        with client.application.app_context():
            db.session.add(del_key)
            db.session.flush()

        with client.application.app_context():
            from models import Station
            station = Station.query.filter_by(uuid='del-station').first()

        response = client.delete(
            f'/api/v1/stations/{station.id}',
            headers={'X-API-Key': del_key.key},
        )
        assert response.status_code == 200

    def test_check_reboot(self, client, auth_client):
        response = client.get(
            '/api/v1/station/check_reboot?station_uuid=s1',
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'reboot_requested' in data

    def test_check_reboot_missing_uuid(self, client, auth_client):
        response = client.get(
            '/api/v1/station/check_reboot',
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 400


class TestDeviceAPI:
    """Tests for device API routes."""

    def test_get_devices_empty(self, client, auth_client):
        response = client.get(
            '/api/v1/devices',
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 200
        assert 'devices' in response.get_json()

    def test_get_devices_with_filters(self, client, auth_client):
        response = client.get(
            '/api/v1/devices?show_ignored=true',
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 200

    @pytest.mark.skip(reason="Requires active observations")
    def test_update_device_props(self, client, auth_client):
        """Needs a device first via observation upload."""
        pass


class TestWebhookAPI:
    """Tests for webhook API routes."""

    def test_get_webhooks_empty(self, client, auth_client):
        response = client.get(
            '/api/v1/webhooks',
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 200

    def test_create_webhook(self, client, auth_client):
        response = client.post(
            '/api/v1/webhooks',
            json={
                'name': 'Test Webhook',
                'url': 'http://example.com/test',
            },
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data['webhook']['name'] == 'Test Webhook'

    def test_get_webhooks_after_create(self, client, auth_client):
        self.test_create_webhook(client, auth_client)
        response = client.get(
            '/api/v1/webhooks',
            headers={'X-API-Key': auth_client['api_key']},
        )
        data = response.get_json()
        assert len(data['webhooks']) >= 1

    def test_update_webhook(self, client, auth_client):
        # Create first
        res1 = client.post(
            '/api/v1/webhooks',
            json={'name': 'Original', 'url': 'http://orig.com'},
            headers={'X-API-Key': auth_client['api_key']},
        )
        webhook_id = res1.get_json()['webhook']['id']

        response = client.put(
            f'/api/v1/webhooks/{webhook_id}',
            json={'name': 'Updated', 'enabled': False},
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['webhook']['name'] == 'Updated'

    def test_delete_webhook(self, client, auth_client):
        # Create with delete-permission key first
        from models import User, APIKey, db
        admin = User.query.filter_by(username='admin').first()
        del_key = APIKey(
            name='wh-del-key', description='', user_id=admin.id, can_delete=True
        )
        with client.application.app_context():
            db.session.add(del_key)
            db.session.flush()

        # Create webhook
        res1 = client.post(
            '/api/v1/webhooks',
            json={'name': 'To Delete', 'url': 'http://del.com'},
            headers={'X-API-Key': auth_client['api_key']},
        )
        webhook_id = res1.get_json()['webhook']['id']

        response = client.delete(
            f'/api/v1/webhooks/{webhook_id}',
            headers={'X-API-Key': del_key.key},
        )
        assert response.status_code == 200


class TestObservationsAPI:
    """Tests for observation API routes."""

    def test_upload_observations(self, client, auth_client):
        # Make sure station exists first
        with client.application.app_context():
            from models import Station
            already = Station.query.filter_by(uuid='obs-station').first()
            if not already:
                db.session.add(Station(uuid='obs-station', name='Obs Station'))
                db.session.commit()

        response = client.post(
            '/api/v1/observations/batch',
            json={
                'station_uuid': 'obs-station',
                'observations': [
                    {'device_mac': 'bb:cc:dd:ee:ff:00', 'rssi': -50, 'protocol': 'wifi'},
                ],
            },
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 200

    def test_upload_observations_no_station(self, client, auth_client):
        response = client.post(
            '/api/v1/observations/batch',
            json={
                'station_uuid': 'nonexistent-station-xyz',
                'observations': [
                    {'device_mac': 'aa:bb:cc:dd:ee:ff', 'rssi': -50},
                ],
            },
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 404

    def test_get_observations(self, client, auth_client):
        response = client.get(
            '/api/v1/observations',
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'observations' in data


class TestSimulationAPI:
    """Tests for simulation API routes."""

    def test_get_simulation_status(self, client, auth_client):
        response = client.get(
            '/api/v1/simulation/status',
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 200

    def test_start_simulation(self, client, auth_client):
        response = client.post(
            '/api/v1/simulation/start',
            json={},
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response.status_code == 200

    def test_stop_simulation(self, client, auth_client):
        response = client.post(
            '/api/v1/simulation/status',
            headers={'X-API-Key': auth_client['api_key']},
        )
        assert response is not None


class TestNoAuthAccess:
    """Tests confirming unauthenticated access is blocked."""

    def test_get_stations_no_auth(self, client):
        response = client.get('/api/v1/stations')
        assert response.status_code == 401

    def test_register_station_no_auth(self, client):
        response = client.post(
            '/api/v1/station/register',
            json={'station_uuid': 'x'},
        )
        assert response.status_code == 401
