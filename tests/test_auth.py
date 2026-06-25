"""Tests for auth.py decorators."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import datetime, timedelta
from models import User, APIKey, db


class TestApiKeyRequired:
    """Tests for the api_key_required decorator."""

    def test_missing_api_key_returns_401(self, client):
        response = client.get('/api/v1/stations')
        assert response.status_code == 401
        assert b'API key required' in response.data

    def test_invalid_api_key_returns_401(self, client):
        response = client.get(
            '/api/v1/stations',
            headers={'X-API-Key': 'invalid-key-here'}
        )
        assert response.status_code == 401
        assert b'Invalid or inactive' in response.data

    def test_inactive_api_key_returns_401(self, client):
        admin = User.query.filter_by(username='admin').first()
        api_key = APIKey(
            name='inactive-key',
            description='Test key',
            user_id=admin.id,
            active=False,
        )
        with client.application.app_context():
            db.session.add(api_key)
            db.session.commit()

        response = client.get(
            '/api/v1/stations',
            headers={'X-API-Key': api_key.key}
        )
        assert response.status_code == 401
        assert b'Invalid or inactive' in response.data

    def test_expired_api_key_returns_401(self, client):
        admin = User.query.filter_by(username='admin').first()
        expired_date = datetime.utcnow() - timedelta(days=1)
        api_key = APIKey(
            name='expired-key',
            description='Test key',
            user_id=admin.id,
            expires_at=expired_date,
        )
        with client.application.app_context():
            db.session.add(api_key)
            db.session.commit()

        response = client.get(
            '/api/v1/stations',
            headers={'X-API-Key': api_key.key}
        )
        assert response.status_code == 401
        assert b'expired' in response.data

    def test_valid_read_key_succeeds(self, client, auth_client):
        response = client.get(
            '/api/v1/stations',
            headers={'X-API-Key': auth_client['api_key']}
        )
        assert response.status_code == 200

    def test_no_write_perm_denied_on_read_only_key(self, app, client):
        """Key with can_read=True but can_write=False should be denied on write routes."""
        admin = User.query.filter_by(username='admin').first()
        read_key = APIKey(
            name='read-only-key',
            description='Test key',
            user_id=admin.id,
            can_read=True,
            can_write=False,
        )
        with app.app_context():
            db.session.add(read_key)
            db.session.flush()

        with client.post(
            '/api/v1/station/register',
            json={'station_uuid': 'test', 'name': 'Test'},
            headers={'X-API-Key': read_key.key},
            content_type='application/json'
        ) as response:
            assert response.status_code == 403
            assert b'lacks write permission' in response.data


class TestApiKeyGeneration:
    """Tests for APIKey.generate_key()"""

    def test_generates_non_empty_key(self):
        key = APIKey.generate_key()
        assert len(key) > 0
        assert isinstance(key, str)

    def test_unique_keys(self):
        keys = {APIKey.generate_key() for _ in range(10)}
        assert len(keys) == 10


class TestApiKeyModel:
    """Tests for APIKey model."""

    def test_to_dict_without_key(self, app):
        admin = User.query.filter_by(username='admin').first()
        key_obj = APIKey(
            name='preview-key',
            description='A preview key',
            user_id=admin.id,
        )
        with app.app_context():
            db.session.add(key_obj)
            db.session.flush()

        result = key_obj.to_dict(include_key=False)
        assert 'key' not in result
        assert result['key_preview'].endswith('...')

    def test_to_dict_with_key(self, client):
        admin = User.query.filter_by(username='admin').first()
        api_key = APIKey.query.first()

        with client.application.app_context():
            key_obj = APIKey(
                name='full-key',
                description='Full key display',
                user_id=admin.id,
                key=api_key.key,
            )
            db.session.add(key_obj)
            db.session.flush()

        result = key_obj.to_dict(include_key=True)
        assert result['key'] == api_key.key


class TestLoginRequiredIntegration:
    """Tests for login_required_web decorator via route access."""

    def test_unauthenticated_access_redirects_to_login(self, client, app):
        with client:
            response = client.get('/stations')
            assert response.status_code == 302
            assert b'login' in response.data.lower() or b'Login' in response.data

    def test_authenticated_user_can_access_stations(self, client):
        # Login first
        client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin',
        }, follow_redirects=True)
        response = client.get('/stations')
        assert response.status_code == 200

    def test_wrong_password_fails_login(self, client):
        response = client.post('/auth/login', data={
            'username': 'admin',
            'password': 'wrong-password',
        })
        assert response.status_code == 200 or response.status_code == 401


class TestAdminRequired:
    """Tests for admin_required decorator."""

    def test_non_admin_cannot_access_admin_route(self, client):
        # Create non-admin user
        non_admin = User(username='user', is_admin=False, active=True)
        non_admin.set_password('password')
        with client.application.app_context():
            db.session.add(non_admin)
            db.session.flush()

        # Login as non-admin
        client.post('/auth/login', data={
            'username': 'user',
            'password': 'password',
        }, follow_redirects=True)

        # Try to access auth users page (admin-only route)
        response = client.get('/auth/users')
        assert response.status_code == 302 or 'administrator' in response.data.decode().lower()
