"""BeaconBoard - IoT Device Tracking System"""
import os
from flask import Flask
from flask_socketio import SocketIO
from flask_migrate import Migrate
from config import config
from models import db
from api import api_bp
from routes import routes_bp
from workers import TriangulationWorker, WebhookWorker
from api.observations import new_devices_queue

# Initialize extensions
socketio = SocketIO()
migrate = Migrate()

# Global workers
triangulation_worker = None
webhook_worker = None


def create_app(config_name='default'):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, 
                     cors_allowed_origins="*",
                     async_mode=app.config.get('SOCKETIO_ASYNC_MODE'))
    
    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(routes_bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Start background workers
    global triangulation_worker, webhook_worker
    
    triangulation_worker = TriangulationWorker(
        app, 
        socketio,
        interval_seconds=app.config.get('TRIANGULATION_INTERVAL_SECONDS', 2)
    )
    triangulation_worker.start()
    
    webhook_worker = WebhookWorker(app, new_devices_queue)
    webhook_worker.start()
    
    return app


def create_cli_app():
    """Create app for CLI commands (migrations, etc.)"""
    app = Flask(__name__)
    app.config.from_object(config['default'])
    config['default'].init_app(app)
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    return app


# Create app instance
app = create_app(os.getenv('FLASK_ENV', 'default'))


if __name__ == '__main__':
    # Run with SocketIO
    socketio.run(app, 
                debug=True,
                host='0.0.0.0',
                port=5000)
