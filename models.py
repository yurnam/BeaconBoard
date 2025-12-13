"""Database models for BeaconBoard"""
from datetime import datetime
import secrets
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Station(db.Model):
    """Represents a physical Raspberry Pi scanning station"""
    __tablename__ = 'stations'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(255))
    
    # Normalized coordinates on current map (0-1 relative to width/height)
    x_norm = db.Column(db.Float)
    y_norm = db.Column(db.Float)
    
    active = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'name': self.name,
            'description': self.description,
            'x_norm': self.x_norm,
            'y_norm': self.y_norm,
            'active': self.active,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Map(db.Model):
    """Represents a floor plan or house map"""
    __tablename__ = 'maps'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    image_filename = db.Column(db.String(255), nullable=False)
    width_px = db.Column(db.Integer)
    height_px = db.Column(db.Integer)
    
    # Real-world dimensions for triangulation accuracy
    width_meters = db.Column(db.Float, default=20.0)  # Default 20m width
    height_meters = db.Column(db.Float, default=20.0)  # Default 20m height
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'image_filename': self.image_filename,
            'width_px': self.width_px,
            'height_px': self.height_px,
            'width_meters': self.width_meters,
            'height_meters': self.height_meters,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Device(db.Model):
    """Represents a unique WiFi/BLE device being tracked"""
    __tablename__ = 'devices'
    
    id = db.Column(db.Integer, primary_key=True)
    mac = db.Column(db.String(32), unique=True, nullable=False, index=True)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    # User customization
    friendly_name = db.Column(db.String(128))
    icon = db.Column(db.String(64), default='question')  # phone, laptop, car, tag, etc.
    color = db.Column(db.String(16), default='#3498db')  # hex color for UI
    ignored = db.Column(db.Boolean, default=False)
    authorized = db.Column(db.Boolean, default=False)  # For authorization tracking
    unauthorized_notified_at = db.Column(db.DateTime)  # Track when notification was sent
    
    # Last estimated position (normalized map coords)
    last_x_norm = db.Column(db.Float)
    last_y_norm = db.Column(db.Float)
    
    # Signal strength tracking
    last_rssi = db.Column(db.Integer)  # Most recent average RSSI
    
    protocol = db.Column(db.String(16), default='wifi')  # 'wifi', 'ble', 'both'
    
    def to_dict(self):
        return {
            'id': self.id,
            'mac': self.mac,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'friendly_name': self.friendly_name,
            'icon': self.icon,
            'color': self.color,
            'ignored': self.ignored,
            'authorized': self.authorized,
            'last_x_norm': self.last_x_norm,
            'last_y_norm': self.last_y_norm,
            'last_rssi': self.last_rssi,
            'protocol': self.protocol
        }


class Observation(db.Model):
    """Raw RSSI data from stations"""
    __tablename__ = 'observations'
    
    id = db.Column(db.Integer, primary_key=True)
    device_mac = db.Column(db.String(32), nullable=False, index=True)
    station_uuid = db.Column(db.String(64), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True, default=datetime.utcnow)
    rssi = db.Column(db.Integer, nullable=False)
    protocol = db.Column(db.String(16), nullable=False)  # 'wifi' or 'ble'
    
    # Optional raw fields
    channel = db.Column(db.Integer)
    ssid = db.Column(db.String(64))
    
    def to_dict(self):
        return {
            'id': self.id,
            'device_mac': self.device_mac,
            'station_uuid': self.station_uuid,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'rssi': self.rssi,
            'protocol': self.protocol,
            'channel': self.channel,
            'ssid': self.ssid
        }


class Webhook(db.Model):
    """Webhook configuration for event notifications"""
    __tablename__ = 'webhooks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    secret = db.Column(db.String(255))  # optional HMAC secret
    enabled = db.Column(db.Boolean, default=True)
    event_type = db.Column(db.String(64), default='device_first_seen')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'has_secret': bool(self.secret),
            'enabled': self.enabled,
            'event_type': self.event_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class User(UserMixin, db.Model):
    """User accounts for web interface authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    api_keys = db.relationship('APIKey', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and store password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'is_admin': self.is_admin,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class APIKey(db.Model):
    """API keys for programmatic access"""
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)  # Optional expiration
    
    # Permissions/scopes (could be extended for more granular control)
    can_read = db.Column(db.Boolean, default=True)
    can_write = db.Column(db.Boolean, default=True)
    can_delete = db.Column(db.Boolean, default=False)
    
    @staticmethod
    def generate_key():
        """Generate a secure random API key"""
        return secrets.token_urlsafe(48)  # Approximately 64 character URL-safe key
    
    def to_dict(self, include_key=False):
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'can_read': self.can_read,
            'can_write': self.can_write,
            'can_delete': self.can_delete
        }
        if include_key:
            result['key'] = self.key
        else:
            result['key_preview'] = self.key[:8] + '...' + self.key[-4:] if self.key else None
        return result
