"""BeaconBoard - IoT Device Tracking System"""
import os
from flask import Flask
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_login import LoginManager
from config import config
from models import db, User
from api import api_bp
from routes import routes_bp
from routes.settings import settings_bp
from routes.auth import auth_bp
from workers import TriangulationWorker, WebhookWorker, UnauthorizedDeviceMonitor
from api.observations import new_devices_queue

# Initialize extensions
socketio = SocketIO()
migrate = Migrate()
login_manager = LoginManager()

# Global workers
triangulation_worker = None
webhook_worker = None
unauthorized_monitor = None


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))


def create_app(config_name='default'):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    
    socketio.init_app(app, 
                     cors_allowed_origins="*",
                     async_mode=app.config.get('SOCKETIO_ASYNC_MODE'))
    
    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(auth_bp)
    
    # Create database tables and default admin user
    with app.app_context():
        db.create_all()
        
        # Create default admin user if no users exist
        if User.query.count() == 0:
            admin = User(
                username='admin',
                email='admin@beaconboard.local',
                is_admin=True,
                active=True
            )
            admin.set_password('admin')  # Default password - should be changed!
            db.session.add(admin)
            db.session.commit()
            print("Created default admin user: username='admin', password='admin'")
            print("IMPORTANT: Change the default password immediately!")
    
    # Start background workers
    global triangulation_worker, webhook_worker, unauthorized_monitor
    
    triangulation_worker = TriangulationWorker(
        app, 
        socketio,
        interval_seconds=app.config.get('TRIANGULATION_INTERVAL_SECONDS', 2)
    )
    triangulation_worker.start()
    
    webhook_worker = WebhookWorker(app, new_devices_queue)
    webhook_worker.start()
    
    unauthorized_monitor = UnauthorizedDeviceMonitor(app, interval_seconds=30)
    unauthorized_monitor.start()
    
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
