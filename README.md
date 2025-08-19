# Flask POC Gmail Integration with Credentials Export

This Flask POC application provides Gmail integration with the ability to export credentials for use in other services (Django, Flask, or any other Python application).

## 🚀 Features

- **Google OAuth Authentication** - Secure login with Google accounts
- **Gmail Integration** - Read emails, search inbox, view email content
- **Credentials Export API** - Share authentication with other services
- **Session Management** - Secure credential storage and validation
- **Performance Optimized** - Caching and batch processing for better performance

## 📋 Prerequisites

- Python 3.7+
- Google Cloud Project with Gmail API enabled
- Google OAuth 2.0 credentials (Client ID and Client Secret)

## 🛠️ Installation

1. **Clone or download the project**
   ```bash
   cd gmail_integration
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   FLASK_SECRET_KEY=your_secret_key_here
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser and go to: `http://localhost:5000`

## 🔐 Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API
4. Go to Credentials → Create Credentials → OAuth 2.0 Client IDs
5. Set application type to "Web application"
6. Add authorized redirect URIs:
   - `http://localhost:5000/auth/callback` (for development)
   - `https://yourdomain.com/auth/callback` (for production)
7. Copy Client ID and Client Secret to your `.env` file

## 📡 API Endpoints

### Authentication Required Endpoints

All credentials export endpoints require authentication. Users must login through the web interface first.

#### 1. Credentials Export
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

#### 2. Credentials Status
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

## 🔗 Using with Other Services

### Django Service Example

```python
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

class FlaskPOCCredentialsManager:
    def __init__(self, flask_poc_url="http://localhost:5000"):
        self.flask_poc_url = flask_poc_url
    
    def get_credentials(self):
        """Get credentials from Flask POC app"""
        try:
            response = requests.get(f"{self.flask_poc_url}/api/credentials")
            if response.status_code == 200:
                cred_data = response.json()
                
                # Create Google Credentials object
                credentials = Credentials(
                    token=cred_data['access_token'],
                    refresh_token=cred_data['refresh_token'],
                    token_uri=cred_data['token_uri'],
                    client_id=cred_data['client_id'],
                    client_secret=cred_data['client_secret'],
                    scopes=cred_data['scopes']
                )
                return credentials
            else:
                print(f"Failed to get credentials: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error getting credentials: {e}")
            return None
    
    def get_gmail_service(self):
        """Get Gmail service using Flask POC credentials"""
        credentials = self.get_credentials()
        if credentials:
            return build('gmail', 'v1', credentials=credentials)
        return None

# Usage in Django view
def send_gmail_view(request):
    credentials_manager = FlaskPOCCredentialsManager()
    gmail_service = credentials_manager.get_gmail_service()
    
    if gmail_service:
        # Use Gmail service
        profile = gmail_service.users().getProfile(userId='me').execute()
        return JsonResponse({'email': profile.get('emailAddress')})
    else:
        return JsonResponse({'error': 'No credentials available'}, status=401)
```

### Flask Service Example

```python
from flask import Flask, jsonify
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)

def get_flask_poc_credentials():
    """Get credentials from Flask POC app"""
    try:
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
            return credentials
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route('/api/gmail/profile')
def get_gmail_profile():
    """Get Gmail profile using Flask POC credentials"""
    credentials = get_flask_poc_credentials()
    if not credentials:
        return jsonify({'error': 'No credentials available'}), 401
    
    try:
        service = build('gmail', 'v1', credentials=credentials)
        profile = service.users().getProfile(userId='me').execute()
        return jsonify(profile)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5001)
```

### Python Script Example

```python
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def send_email_with_flask_poc_credentials():
    """Send email using credentials from Flask POC"""
    
    # Get credentials from Flask POC
    response = requests.get('http://localhost:5000/api/credentials')
    if response.status_code != 200:
        print("Failed to get credentials")
        return
    
    cred_data = response.json()
    
    # Create credentials object
    credentials = Credentials(
        token=cred_data['access_token'],
        refresh_token=cred_data['refresh_token'],
        token_uri=cred_data['token_uri'],
        client_id=cred_data['client_id'],
        client_secret=cred_data['client_secret'],
        scopes=cred_data['scopes']
    )
    
    # Create Gmail service
    service = build('gmail', 'v1', credentials=credentials)
    
    # Send email
    message = {
        'raw': 'base64_encoded_message_here'
    }
    
    try:
        sent_message = service.users().messages().send(
            userId='me', body=message
        ).execute()
        print(f"Message sent: {sent_message['id']}")
    except Exception as e:
        print(f"Error sending message: {e}")

if __name__ == "__main__":
    send_email_with_flask_poc_credentials()
```

## 🧪 Testing

Run the test file to verify everything works:

```bash
python test_credentials_export.py
```

This will:
1. Test connection to Flask POC app
2. Test all credentials export endpoints
3. Test using exported credentials with Google services
4. Provide detailed feedback on each step

## 🔒 Security Considerations

- **Credentials are stored in Flask session** - ensure secure session configuration
- **Client secret is exposed** - in production, consider more secure storage
- **Token expiry** - implement proper token refresh handling in consuming services
- **HTTPS** - use HTTPS in production for all API calls

## 🚨 Common Issues

### 1. "Not authenticated" error
- User must login through Flask POC web interface first
- Check if Flask POC app is running
- Verify session cookies are being sent

### 2. Connection refused
- Ensure Flask POC app is running on port 5000
- Check firewall settings
- Verify URL in your service matches Flask POC URL

### 3. Invalid credentials
- Tokens may have expired
- Check Flask POC app for authentication status
- Re-login if necessary

### 4. Scope issues
- Ensure required scopes are requested during OAuth
- Check if user has granted necessary permissions

## 📚 Dependencies

- **Flask** - Web framework
- **Authlib** - OAuth client
- **google-api-python-client** - Google API client
- **google-auth** - Google authentication
- **requests** - HTTP client (for testing)

## 🔄 Token Refresh

The Flask POC app handles basic token validation, but for production use in other services, implement proper token refresh:

```python
from google.auth.transport.requests import Request

def refresh_credentials_if_needed(credentials):
    """Refresh credentials if expired"""
    if credentials.expired:
        credentials.refresh(Request())
        # Update stored credentials in your service
    return credentials
```

## 📞 Support

For issues or questions:
1. Check the test file output for detailed error messages
2. Verify Flask POC app is running and accessible
3. Ensure proper authentication flow is completed
4. Check Google Cloud Console for API quotas and permissions

## 🎯 Next Steps

1. **Test the credentials export** using the test file
2. **Integrate with your Django/Flask services** using the examples
3. **Implement proper error handling** for production use
4. **Add token refresh logic** for long-running services
5. **Extend to other Google APIs** (Google Docs, Drive, etc.) 