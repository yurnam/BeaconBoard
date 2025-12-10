# BeaconBoard Authentication & API Keys Guide

## Overview

BeaconBoard now includes enterprise-grade authentication and API key management. All web pages require user login, and all API endpoints require valid API keys.

## Default Credentials

On first run, BeaconBoard automatically creates a default admin user:

- **Username:** `admin`
- **Password:** `admin`

⚠️ **IMPORTANT: Change the default password immediately after first login!**

## Web Authentication

### Logging In

1. Navigate to `http://your-server:5000/auth/login`
2. Enter username and password
3. Click "Login"
4. You'll be redirected to the Dashboard

### User Management (Admin Only)

Administrators can create and manage users:

1. Click **👥 Users** in the navigation
2. Fill in the "Create New User" form:
   - Username (unique)
   - Email (unique)
   - Password
   - Admin checkbox (for admin privileges)
3. Click **Create User**

**User Actions:**
- **Activate/Deactivate** - Toggle user access
- **Delete** - Remove user and all their API keys

### Changing Passwords

Currently, administrators can delete and recreate users. A password change feature will be added in a future update.

## API Keys

### Why API Keys?

API keys provide secure, programmatic access to BeaconBoard's API. Each key:
- Belongs to a specific user
- Has configurable permissions (Read, Write, Delete)
- Can be enabled/disabled
- Tracks usage (last used timestamp)
- Can have an optional expiration date

### Creating API Keys

1. Login to BeaconBoard
2. Click **🔑 API Keys** in navigation
3. Click **Create New API Key**
4. Fill in the form:
   - **Name**: Descriptive name (e.g., "Raspberry Pi Bedroom")
   - **Description**: Optional details
   - **Write Permission**: Allow POST/PUT requests
   - **Delete Permission**: Allow DELETE requests
5. Click **Create API Key**
6. **IMPORTANT**: Copy the generated key immediately - you won't see it again!

### API Key Permissions

- **Read** (always enabled): GET requests, query data
- **Write**: POST/PUT requests, upload observations, register stations
- **Delete**: DELETE requests, remove resources

### Using API Keys

Include your API key in the `X-API-Key` header for all API requests:

```bash
curl -H "X-API-Key: YOUR_API_KEY_HERE" \
     http://localhost:5000/api/v1/stations
```

### Managing API Keys

From the API Keys page, you can:
- **Disable/Enable**: Toggle key active status
- **Delete**: Permanently remove a key
- View **Last Used**: See when the key was last used
- See **Key Preview**: First 8 and last 4 characters

## Client Configuration

### Raspberry Pi Agent

Edit `/etc/beaconboard/config.json`:

```json
{
  "station_uuid": "pi_bedroom",
  "station_name": "Bedroom Scanner",
  "server_url": "http://192.168.1.100:5000",
  "api_key": "YOUR_API_KEY_HERE",
  "bettercap_url": "http://localhost:8081",
  "bettercap_user": "user",
  "bettercap_pass": "pass",
  "wifi_interface": "wlan0",
  "ble_interface": "hci0",
  "batch_interval_sec": 10,
  "max_batch_size": 200
}
```

Restart the agent:
```bash
sudo systemctl restart beaconboard-agent
```

### ESP32-S3 Scanner

Edit `include/config.h`:

```cpp
#define WIFI_SSID "YourNetworkName"
#define WIFI_PASSWORD "YourPassword"
#define SERVER_URL "http://192.168.1.100:5000"
#define API_KEY "YOUR_API_KEY_HERE"
#define STATION_UUID "esp32_bedroom"
#define STATION_NAME "ESP32 Bedroom Scanner"
```

Rebuild and upload:
```bash
cd esp32_scanner
pio run --target upload
```

### Custom Integrations

For any custom client, include the API key header:

**Python Example:**
```python
import requests

headers = {
    'Content-Type': 'application/json',
    'X-API-Key': 'YOUR_API_KEY_HERE'
}

response = requests.post(
    'http://localhost:5000/api/v1/observations/batch',
    headers=headers,
    json={
        'station_uuid': 'my_station',
        'observations': [...]
    }
)
```

**JavaScript Example:**
```javascript
fetch('http://localhost:5000/api/v1/stations', {
    headers: {
        'X-API-Key': 'YOUR_API_KEY_HERE'
    }
})
.then(response => response.json())
.then(data => console.log(data));
```

## API Endpoints

### Protected Endpoints

All API endpoints require a valid API key. The required permission level depends on the HTTP method:

| Endpoint | Method | Permission | Description |
|----------|--------|------------|-------------|
| `/api/v1/stations` | GET | Read | List all stations |
| `/api/v1/stations/<id>` | GET | Read | Get station details |
| `/api/v1/station/register` | POST | Write | Register/update station |
| `/api/v1/stations/<id>/position` | POST | Write | Update station position |
| `/api/v1/stations/<id>` | PUT | Write | Update station details |
| `/api/v1/stations/<id>` | DELETE | Delete | Delete station |
| `/api/v1/observations/batch` | POST | Write | Upload observations |
| `/api/v1/observations` | GET | Read | Query observations |
| `/api/v1/devices` | GET | Read | List devices |
| `/api/v1/devices/<id>` | PUT | Write | Update device |
| `/api/v1/devices/<id>` | DELETE | Delete | Delete device |
| `/api/v1/webhooks` | GET | Read | List webhooks |
| `/api/v1/webhooks` | POST | Write | Create webhook |
| `/api/v1/webhooks/<id>` | PUT | Write | Update webhook |
| `/api/v1/webhooks/<id>` | DELETE | Delete | Delete webhook |
| `/api/v1/simulation/*` | * | Write | Simulation control |

### Error Responses

**401 Unauthorized** - API key missing or invalid:
```json
{
  "error": "API key required. Include X-API-Key header."
}
```

**403 Forbidden** - API key lacks required permission:
```json
{
  "error": "API key lacks write permission"
}
```

## Security Best Practices

### For Web Interface

1. **Change default password immediately** after first login
2. **Use strong passwords** (minimum 12 characters, mix of upper/lower/numbers/symbols)
3. **Create separate users** for different team members
4. **Use admin accounts sparingly** - create regular users for daily use
5. **Deactivate unused accounts** instead of deleting them (preserves audit trail)

### For API Keys

1. **Create separate keys per device/service** - easier to track and revoke
2. **Use minimal permissions** - only grant Write if needed, Delete only if absolutely necessary
3. **Rotate keys periodically** - delete old keys and create new ones every few months
4. **Store keys securely** - never commit keys to Git, use environment variables or config files
5. **Monitor key usage** - check "Last Used" timestamps regularly
6. **Disable unused keys** instead of deleting them immediately
7. **Use expiration dates** for temporary access (set expires_at field)

### For Production Deployment

1. **Use HTTPS** - always serve BeaconBoard over TLS in production
2. **Use a reverse proxy** (nginx, Apache) with proper SSL certificates
3. **Keep secrets secret** - change default passwords, use strong API keys
4. **Regular updates** - keep BeaconBoard and dependencies up to date
5. **Monitor logs** - watch for failed authentication attempts
6. **Backup database** - includes user accounts and API keys

## Troubleshooting

### "API key required" Error

**Problem:** Client gets 401 error when making API requests.

**Solution:**
1. Check that API key is included in `X-API-Key` header
2. Verify key is correct (check API Keys page for preview)
3. Ensure key is active (not disabled)
4. Check key hasn't expired

### "API key lacks permission" Error

**Problem:** Client gets 403 error.

**Solution:**
1. Check the endpoint's required permission (see table above)
2. Edit API key permissions via web UI
3. Ensure Write permission is enabled for POST/PUT requests
4. Ensure Delete permission is enabled for DELETE requests

### Can't Login

**Problem:** Login fails with "Invalid username or password".

**Solution:**
1. Double-check username and password (case-sensitive)
2. If you forgot the password, ask an admin to reset it
3. As last resort, edit the database directly:
   ```python
   from werkzeug.security import generate_password_hash
   # Use this hash for password "newpassword"
   generate_password_hash("newpassword")
   ```

### Locked Out (No Admin Access)

**Problem:** All admins locked out or password forgotten.

**Solution:** Directly edit the SQLite database:

```bash
sqlite3 instance/beaconboard.db

# Reset admin password to "admin"
UPDATE users 
SET password_hash = 'scrypt:32768:8:1$HASH...' 
WHERE username = 'admin';

# Or create a new admin user
# (use the werkzeug command above to generate hash)
```

## Database Migration

If upgrading from a version without authentication, run:

```bash
# Backup first!
cp instance/beaconboard.db instance/beaconboard.db.backup

# Run migration
sqlite3 instance/beaconboard.db < migrations_auth.sql

# Or use Flask-Migrate
flask db upgrade
```

On next startup, the default admin user will be created automatically.

## Future Enhancements

Planned features for future releases:
- Password change functionality for users
- Two-factor authentication (2FA)
- OAuth2 integration
- API key scopes (more granular permissions)
- Session timeout configuration
- Password complexity requirements
- Failed login attempt tracking
- Account lockout after failed attempts
- Audit log for security events

## Support

For issues or questions:
- Check this guide first
- Review the main README.md
- Open an issue on GitHub
- Check server logs for detailed error messages
