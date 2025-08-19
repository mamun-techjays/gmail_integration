# Flask POC Gmail Integration - Credentials Export

Simple Flask app that provides Google OAuth authentication and exports credentials for other services to use.

## 🚀 Quick Start

1. **Setup environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Google OAuth**
   - Create `.env` file:
   ```env
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   FLASK_SECRET_KEY=your_secret_key
   ```

3. **Run the app**
   ```bash
   python app.py
   ```

4. **Login in browser**
   - Go to `http://localhost:5000`
   - Complete Google OAuth login

## 📡 API Endpoints

### Get Credentials
```
GET /api/credentials
```
**Response:**
```json
{
  "access_token": "ya29.a0AfH6SMC...",
  "refresh_token": "1//04dX...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "your_client_id.apps.googleusercontent.com",
  "client_secret": "your_client_secret",
  "scopes": ["openid", "email", "profile", "https://www.googleapis.com/auth/gmail.readonly"],
  "user_email": "user@example.com"
}
```

### Check Status
```
GET /api/credentials/status
```
**Response:**
```json
{
  "status": "valid",
  "user_email": "user@example.com",
  "message": "Credentials are working correctly"
}
```

## 🔗 Using in Other Services

### Django/Flask Service
```python
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_gmail_service():
    """Get Gmail service using Flask POC credentials"""
    response = requests.get('http://localhost:5000/api/credentials')
    if response.status_code == 200:
        cred_data = response.json()
        
        credentials = Credentials(
            token=cred_data['access_token'],
            refresh_token=cred_data['refresh_token'],
            token_uri=cred_data['token_uri'],
            client_id=cred_data['client_id'],
            client_secret=cred_data['client_secret'],
            scopes=cred_data['scopes']
        )
        
        return build('gmail', 'v1', credentials=credentials)
    return None

# Usage
gmail_service = get_gmail_service()
if gmail_service:
    profile = gmail_service.users().getProfile(userId='me').execute()
    print(f"Email: {profile.get('emailAddress')}")
```

### Python Script
```python
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Get credentials from Flask POC
response = requests.get('http://localhost:5000/api/credentials')
credentials_data = response.json()

# Create credentials object
credentials = Credentials(
    token=credentials_data['access_token'],
    refresh_token=credentials_data['refresh_token'],
    token_uri=credentials_data['token_uri'],
    client_id=credentials_data['client_id'],
    client_secret=credentials_data['client_secret'],
    scopes=credentials_data['scopes']
)

# Use with Google APIs
service = build('gmail', 'v1', credentials=credentials)
```

## 🧪 Test

```bash
# Test the endpoints
curl http://localhost:5000/api/credentials
curl http://localhost:5000/api/credentials/status
```

## 📋 Requirements

- Python 3.7+
- Google Cloud Project with Gmail API enabled
- Google OAuth 2.0 credentials

## 🔒 Security Note

- Change `FLASK_SECRET_KEY` in production
- Use HTTPS in production
- Implement proper token refresh for long-running services 