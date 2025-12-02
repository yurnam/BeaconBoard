import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'beaconboard.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Uploads
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAPS_FOLDER = os.path.join(UPLOAD_FOLDER, 'maps')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Triangulation settings
    OBSERVATION_WINDOW_SECONDS = 10  # Consider observations from last N seconds
    TRIANGULATION_INTERVAL_SECONDS = 2  # Run triangulation every N seconds
    MIN_STATIONS_FOR_TRIANGULATION = 3
    RSSI_SMOOTHING_FACTOR = 0.3  # For exponential moving average
    
    # Webhook settings
    WEBHOOK_TIMEOUT_SECONDS = 5
    WEBHOOK_RETRY_ATTEMPTS = 3
    
    # SocketIO
    SOCKETIO_MESSAGE_QUEUE = None
    SOCKETIO_ASYNC_MODE = 'threading'  # Use threading instead of eventlet for Python 3.12 compatibility
    # Note: For production with high load, consider using eventlet with Python 3.11 or earlier,
    # or use a message queue (Redis/RabbitMQ) for horizontal scaling
    
    @staticmethod
    def init_app(app):
        """Initialize application with this config"""
        # Create necessary directories
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['MAPS_FOLDER'], exist_ok=True)
        os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
