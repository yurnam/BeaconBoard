"""Fixtures and configuration for tests."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch


# Mock db.create_all() so the real DB isn't hit when importing app module
original_create_all = None


@pytest.fixture(scope='module', autouse=True)
def mock_db_init():
    """Prevent the app factory from writing to the real database."""
    from models import db

    def noop_create_all(*args, **kwargs):
        pass

    with patch.object(db.__class__, 'create_all', noop_create_all):
        yield


# Now safe to import app - it won't hit a real DB during module load
from app import create_app  # noqa: E402


@pytest.fixture(scope='module')
def app():
    """Create fresh application for testing with in-memory SQLite."""
    test_app = create_app('development')
    test_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })

    with test_app.app_context():
        # Initialize DB tables for tests and create default admin user
        from models import db as _db, User
        _db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                is_admin=True,
                active=True
            )
            admin.set_password('admin')
            _db.session.add(admin)
            _db.session.commit()
        yield test_app
        _db.session.remove()


@pytest.fixture(scope='module')
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope='module')
def runner(app):
    """Create CLI test runner."""
    return app.test_cli_runner()


@pytest.fixture(scope='module')
def auth_client(client):
    """Provide credentials for tests that need them."""
    from models import User, APIKey

    with client.application.app_context():
        # Always ensure admin exists and has an active read/write key
        admin = User.query.filter_by(username='admin').first()
        if not api_key := APIKey.query.filter_by(name='test-key', active=True).first():
            api_key = APIKey(
                name='test-key',
                description='Test API key',
                user_id=admin.id,
                can_read=True,
                can_write=True,
                can_delete=False
            )
            from models import db as _db
            _db.session.add(api_key)
            _db.session.commit()

        admin = User.query.filter_by(username='admin').first()
        api_key = APIKey.query.filter_by(name='test-key').first()

    return {
        'client': client,
        'admin_username': admin.username,
        'admin_password': 'admin',
        'api_key': api_key.key,
    }


@pytest.fixture(scope='module')
def station_data():
    """Fixture with valid station registration data."""
    return {
        'station_uuid': 'test-station-001',
        'name': 'Test Station',
        'description': 'A test station',
    }


@pytest.fixture(scope='module')
def device_data():
    """Fixture with valid observation data for a device."""
    from datetime import datetime

    return {
        'station_uuid': 'test-station-001',
        'observations': [
            {
                'device_mac': 'aa:bb:cc:dd:ee:ff',
                'rssi': -60,
                'protocol': 'wifi',
                'timestamp': datetime.utcnow().isoformat(),
            },
            {
                'device_mac': 'aa:bb:cc:dd:ee:11',
                'rssi': -75,
                'protocol': 'ble',
                'channel': 37,
                'timestamp': datetime.utcnow().isoformat(),
            },
        ],
    }


@pytest.fixture(scope='module')
def active_map(app):
    """Create an active map for tests that need triangulation."""
    from models import Map

    with app.app_context():
        Map.query.update({'is_active': False})
        test_map = Map(
            name='Test Floor Plan',
            image_filename='test_floorplan.png',
            width_px=1200,
            height_px=800,
            width_meters=20.0,
            height_meters=15.0,
            is_active=True,
        )
        from models import db as _db
        _db.session.add(test_map)
        _db.session.commit()

    return test_map


@pytest.fixture(scope='module')
def stations_3(app):
    """Create 3 stations forming a non-collinear triangle."""
    from models import Station, db as _db

    with app.app_context():
        _db.session.execute(_db.delete(Station))
        _db.session.flush()

        s1 = Station(uuid='tri-station-1', name='Tri Station 1', x_norm=0.0, y_norm=0.0)
        s2 = Station(uuid='tri-station-2', name='Tri Station 2', x_norm=1.0, y_norm=0.0)
        s3 = Station(uuid='tri-station-3', name='Tri Station 3', x_norm=0.5, y_norm=1.0)
        _db.session.add_all([s1, s2, s3])
        _db.session.commit()

    return [s1, s2, s3]
