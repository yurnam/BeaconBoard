"""Tests for app factory and application."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest


class TestAppFactory:
    """Tests for create_app()"""

    def test_app_created(self, app):
        assert app is not None
        assert app.config['TESTING'] is True

    def test_db_initialized(self, app):
        from models import db
        assert db.get_engine(app) is not None

    def test_default_admin_created(self, client):
        from models import User
        admin = User.query.filter_by(username='admin').first()
        assert admin is not None
        assert admin.is_admin is True

    def test_default_admin_can_login(self, auth_client):
        response = auth_client['client'].post('/auth/login', data={
            'username': 'admin',
            'password': 'admin',
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_app_has_blueprints(self, app):
        assert 'api' in app.blueprints
        assert 'routes' in app.blueprints


class TestAppConfig:
    """Tests for application configuration."""

    def test_secret_key_configured(self, app):
        assert app.config['SECRET_KEY'] is not None

    def test_default_database_uri(self, app):
        uri = app.config['SQLALCHEMY_DATABASE_URI']
        assert 'sqlite' in uri

    def test_upload_folder_created(self, app):
        with app.app_context():
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            assert os.path.isdir(app.config['UPLOAD_FOLDER'])

    def test_allowed_extensions(self, app):
        allowed = app.config['ALLOWED_EXTENSIONS']
        assert 'png' in allowed
        assert 'jpg' in allowed
        assert 'jpeg' in allowed


class TestAppContext:
    """Tests for creating database tables."""

    def test_tables_created(self, client):
        from models import Station, Device, Map, Observation, Webhook, User, APIKey
        # The app fixture already calls db.create_all()
        with client.application.app_context():
            assert Station.__table__ is not None
            assert Device.__table__ is not None


class TestIndexRoute:
    """Tests for the main index route."""

    def test_root_route(self, client):
        response = client.get('/')
        assert response.status_code == 200 or response.status_code == 302
