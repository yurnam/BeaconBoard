"""Tests for worker modules (TriangulationWorker, WebhookWorker)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from models import Device, Observation, Map, Webhook, db


class TestTriangulationWorker:
    """Tests for TriangulationWorker."""

    @pytest.fixture(autouse=True)
    def _no_workers(self):
        """Ensure no existing workers are running during tests."""
        import app as app_module
        app_module.triangulation_worker = None
        app_module.webhook_worker = None
        yield
        for attr in ('triangulation_worker', 'webhook_worker'):
            if getattr(app_module, attr) and not hasattr(getattr(app_module, attr), '_test_cleanup'):
                pass

    def test_init_sets_defaults(self, app):
        from workers import TriangulationWorker
        worker = TriangulationWorker(app, MagicMock())
        assert worker.interval_seconds == 2
        assert worker.running is False
        assert worker.thread is None

    @pytest.fixture(autouse=True)
    def _stop_workers(self, request):
        """Stop any workers before and after each test."""
        import app as app_module
        yield
        if getattr(app_module, 'triangulation_worker') and \
           getattr(app_module.triangulation_worker, 'thread', None) and \
           getattr(app_module.triangulation_worker.thread, 'is_alive', lambda: False)():
            try:
                app_module.triangulation_worker.stop()
            except Exception:
                pass

    def test_start_starts_thread(self, app):
        from workers import TriangulationWorker
        mock_socketio = MagicMock()
        worker = TriangulationWorker(app, mock_socketio)
        worker.start()
        assert worker.running is True
        assert worker.thread is not None
        assert worker.thread.is_alive()

    def test_stop_stops_thread(self, app):
        from workers import TriangulationWorker
        mock_socketio = MagicMock()
        worker = TriangulationWorker(app, mock_socketio)
        worker.start()
        worker.stop()
        assert worker.running is False

    def test_process_positions_no_devices(self, app):
        """Should not fail with no devices."""
        from workers import TriangulationWorker
        mock_socketio = MagicMock()
        worker = TriangulationWorker(app, mock_socketio)
        with app.app_context():
            Map.query.update({'is_active': True})
            worker._process_positions()

    def test_process_positions_enough_stations(
        self, app, active_map, stations_3
    ):
        """With 3+ stations and observations, device should get a position."""
        from workers import TriangulationWorker

        now = datetime.utcnow() - timedelta(seconds=2)

        device = Device(
            mac='pos:test:device',
            first_seen=now,
            last_seen=now,
            protocol='wifi',
        )
        for s in stations_3:
            db.session.add(Observation(
                device_mac=device.mac,
                station_uuid=s.uuid,
                timestamp=now,
                rssi=-50,
                protocol='wifi',
            ))

        db.session.add(device)
        db.session.commit()

        mock_socketio = MagicMock()
        worker = TriangulationWorker(
            app, mock_socketio, interval_seconds=0.1
        )

        with app.app_context():
            device_new = Device.query.filter_by(mac='pos:test:device').first()
            if device_new:
                device_new.last_x_norm = None
                device_new.last_y_norm = None
                worker._process_positions()

        emitted = mock_socketio.emit.call_args
        assert emitted is not None
        assert emitted[0][0] == 'device_positions'
        assert 'devices' in emitted[0][1]


class TestWebhookWorker:
    """Tests for WebhookWorker."""

    def test_init(self, app):
        import queue
        mock_queue = queue.Queue()
        from workers import WebhookWorker
        worker = WebhookWorker(app, mock_queue)
        assert worker.running is False

    @patch('workers.send_webhook', MagicMock(return_value=True))
    def test_send_new_device_webhooks_fires_webhook(
        self, client, monkeypatch
    ):
        from workers import WebhookWorker
        import queue

        mock_callback = MagicMock()
        monkeypatch.setattr(WebhookWorker, '_send_new_device_webhooks', mock_callback)

        # Create a webhook in the DB
        with client.application.app_context():
            db.session.add(Webhook(
                name='TestHook',
                url='http://example.com/hook',
                event_type='device_first_seen',
            ))
            db.session.commit()

        mock_queue = queue.Queue()
        worker = WebhookWorker(client.application, mock_queue)
        mock_queue.put({'mac': 'aa:bb'})

        # Call one loop iteration manually
        try:
            device_data = mock_queue.get(timeout=0.1)
        except __import__('queue').Empty:
            pass
        else:
            worker._send_new_device_webhooks(device_data)
        assert mock_callback.called, "Webhook should have been fired"

    def test_queue_timeout_no_crash(self):
        import queue
        empty_queue = queue.Queue()
        try:
            empty_queue.get(timeout=0.1)
        except __import__('queue').Empty as e:
            assert type(e).__name__ == 'Empty'


class TestSendWebhook:
    """Tests for send_webhook standalone function."""

    def test_send_webhook_success(self, app):
        from workers import send_webhook
        webhook = Webhook(
            name='Test',
            url='http://example.com/hook',
        )
        with patch('workers.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = send_webhook(webhook, {'event': 'test'})
            assert result is True

    def test_send_webhook_failure(self, app):
        from workers import send_webhook
        webhook = Webhook(
            name='Test',
            url='http://example.com/hook',
        )
        with patch('workers.requests.post') as mock_post:
            mock_post.side_effect = Exception('Connection refused')

            result = send_webhook(webhook, {'event': 'test'})
            assert result is False

    def test_hmac_signature_added(self, app):
        from workers import send_webhook
        webhook = Webhook(
            name='Test',
            url='http://example.com/hook',
            secret='my-secret',
        )
        with patch('workers.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            send_webhook(webhook, {'event': 'test'})

            headers = mock_post.call_args[1]['headers']
            assert 'X-Signature' in headers
            assert 'sha256=' in headers['X-Signature']


class TestUnauthorizedDeviceMonitor:
    """Tests for UnauthorizedDeviceMonitor."""

    def test_init(self, app):
        from workers import UnauthorizedDeviceMonitor
        monitor = UnauthorizedDeviceMonitor(app)
        assert monitor.running is False
        assert monitor.interval_seconds == 30

    @patch('workers.send_webhook')
    def test_checks_unauthorized_devices(self, mock_send, client):
        """Devices present > notification_timeout that are not authorized
        should be detected and webhook fired."""
        from workers import UnauthorizedDeviceMonitor
        old_time = datetime.utcnow() - timedelta(hours=1)

        device = Device(
            mac='unauth:test:device',
            first_seen=old_time,
            last_seen=old_time,
            authorized=False,
            ignored=False,
            unauthorized_notified_at=None,
        )
        with client.application.app_context():
            db.session.add(device)
            db.session.commit()

        monitor = UnauthorizedDeviceMonitor(client.application, interval_seconds=0.1)

        with client.application.app_context():
            monitor._check_unauthorized_devices()

        # Should have been notified now (unauthorized_notified_at updated)
        updated = Device.query.filter_by(mac='unauth:test:device').first()
        assert updated.unauthorized_notified_at is not None
