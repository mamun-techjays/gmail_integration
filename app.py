import os
from flask import Flask, render_template, redirect, url_for, session, request, jsonify, make_response
from authlib.integrations.flask_client import OAuth
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
import email
from email.mime.text import MIMEText
import re
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this')

# Configure session
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Simple in-memory cache for email metadata
email_cache = {}
cache_ttl = 300  # 5 minutes

def get_cached_email(email_id):
    """Get email from cache if not expired"""
    if email_id in email_cache:
        cached_data, timestamp = email_cache[email_id]
        if time.time() - timestamp < cache_ttl:
            return cached_data
        else:
            del email_cache[email_id]
    return None

def cache_email(email_id, email_data):
    """Cache email data with timestamp"""
    email_cache[email_id] = (email_data, time.time())
    
    # Clean up old cache entries if cache gets too large
    if len(email_cache) > 1000:
        current_time = time.time()
        expired_keys = [k for k, (_, t) in email_cache.items() if current_time - t > cache_ttl]
        for k in expired_keys:
            del email_cache[k]

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://oauth2.googleapis.com/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
    client_kwargs={
        'scope': 'openid email profile https://www.googleapis.com/auth/gmail.readonly'
    }
)

def is_authenticated():
    """Check if user is authenticated and has valid credentials"""
    if 'user' not in session or 'credentials' not in session:
        return False
    
    # Check if credentials are still valid
    try:
        credentials = Credentials(
            token=session['credentials']['token'],
            refresh_token=session['credentials'].get('refresh_token'),
            token_uri=session['credentials'].get('token_uri'),
            client_id=session['credentials'].get('client_id'),
            client_secret=session['credentials'].get('client_secret'),
            scopes=session['credentials'].get('scopes')
        )
        
        # Try to build service to test credentials
        service = build('gmail', 'v1', credentials=credentials)
        # Make a simple API call to test
        service.users().getProfile(userId='me').execute()
        return True
    except Exception:
        # Credentials are invalid, clear session
        session.clear()
        return False

def get_gmail_service():
    """Create Gmail service instance using stored credentials"""
    if not is_authenticated():
        return None
    
    credentials = Credentials(
        token=session['credentials']['token'],
        refresh_token=session['credentials'].get('refresh_token'),
        token_uri=session['credentials'].get('token_uri'),
        client_id=session['credentials'].get('client_id'),
        client_secret=session['credentials'].get('client_secret'),
        scopes=session['credentials'].get('scopes')
    )
    
    return build('gmail', 'v1', credentials=credentials)

def add_performance_headers(response, cache_duration=300):
    """Add performance and caching headers to response"""
    response.headers['Cache-Control'] = f'private, max-age={cache_duration}'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

def decode_email_content(data):
    """Decode base64 encoded email content"""
    try:
        decoded_data = base64.urlsafe_b64decode(data + '===')
        return decoded_data.decode('utf-8')
    except Exception as e:
        return f"Error decoding content: {str(e)}"

def get_email_body(message):
    """Extract email body from Gmail message"""
    body = ""
    
    if 'parts' in message['payload']:
        for part in message['payload']['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    body = decode_email_content(part['body']['data'])
                    break
            elif part['mimeType'] == 'text/html':
                if 'data' in part['body']:
                    body = decode_email_content(part['body']['data'])
    else:
        if message['payload']['body'].get('data'):
            body = decode_email_content(message['payload']['body']['data'])
    
    return body

@app.route('/')
def index():
    """Home page - login or redirect to inbox"""
    print(f"Index route - Session keys: {list(session.keys())}")
    print(f"Index route - Is authenticated: {is_authenticated()}")
    
    if is_authenticated():
        print("User is authenticated, redirecting to inbox")
        return redirect(url_for('inbox'))
    
    print("User is not authenticated, showing login page")
    return render_template('index.html')

@app.route('/login')
def login():
    """Initiate Google OAuth login"""
    print(f"Login route - Session keys: {list(session.keys())}")
    print(f"Login route - Is authenticated: {is_authenticated()}")
    
    if is_authenticated():
        print("User already authenticated, redirecting to inbox")
        return redirect(url_for('inbox'))
    
    print("Initiating Google OAuth login")
    redirect_uri = url_for('auth_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/callback')
def auth_callback():
    """Handle OAuth callback"""
    print("Auth callback route called")
    print(f"Request args: {dict(request.args)}")
    
    try:
        token = google.authorize_access_token()
        print(f"Token: {token}")
        print(f"Token received successfully: {list(token.keys())}")
        print(f"User info: {token.get('userinfo', {}).get('email', 'No email')}")
        
        # Store user info and credentials
        session['user'] = token['userinfo']
        session['credentials'] = {
            'token': token['access_token'],
            'refresh_token': token.get('refresh_token'),
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'scopes': ['openid', 'email', 'profile', 'https://www.googleapis.com/auth/gmail.readonly']
        }
        
        # Make session permanent
        session.permanent = True
        
        print(f"Session after auth: {list(session.keys())}")
        print(f"User stored in session: {session['user'].get('email', 'No email')}")
        print("Redirecting to inbox")
        
        return redirect(url_for('inbox'))
    except Exception as e:
        print(f"Auth callback error: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('index'))

@app.route('/inbox')
def inbox():
    """Display inbox shell - emails loaded via AJAX for better performance"""
    print(f"Inbox route - Session keys: {list(session.keys())}")
    print(f"Inbox route - Is authenticated: {is_authenticated()}")
    
    if not is_authenticated():
        print("User not authenticated, redirecting to index")
        return redirect(url_for('index'))
    
    print("User authenticated, rendering inbox shell")
    
    # Just render the template with user info - emails loaded via AJAX
    response = make_response(render_template('inbox.html', 
                                           emails=[], 
                                           user=session['user'],
                                           pagination=None,
                                           search_query=''))
    return add_performance_headers(response, cache_duration=300)  # Cache shell for 5 minutes

@app.route('/email/<email_id>')
def view_email(email_id):
    """View full email content"""
    if not is_authenticated():
        return redirect(url_for('index'))
    
    service = get_gmail_service()
    if not service:
        return redirect(url_for('logout'))
    
    try:
        message = service.users().messages().get(userId='me', id=email_id).execute()
        headers = message['payload']['headers']
        
        # Extract email details
        email_data = {
            'id': email_id,
            'from': next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown'),
            'to': next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown'),
            'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
            'date': next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown'),
            'body': get_email_body(message)
        }
        
        response = make_response(render_template('email.html', email=email_data, user=session['user']))
        return add_performance_headers(response, cache_duration=60)  # Cache for 1 minute
    
    except Exception as e:
        print(f"Error fetching email: {e}")
        return f"Error fetching email: {str(e)}"

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/search')
def search_emails():
    """API endpoint for searching emails"""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    service = get_gmail_service()
    if not service:
        return jsonify({'error': 'Service not available'}), 500
    
    try:
        query = request.args.get('q', '')
        max_results = request.args.get('max', 50, type=int)
        
        if not query:
            return jsonify({'emails': [], 'total': 0})
        
        # Build Gmail search query
        gmail_query = f'in:inbox {query}'
        
        results = service.users().messages().list(
            userId='me',
            maxResults=min(max_results, 100),
            q=gmail_query
        ).execute()
        
        messages = results.get('messages', [])
        
        email_list = []
        for msg in messages[:max_results]:
            try:
                message = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = message['payload']['headers']
                
                email_info = {
                    'id': msg['id'],
                    'from': next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown'),
                    'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
                    'date': next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown'),
                    'snippet': message.get('snippet', '')[:100] + '...' if len(message.get('snippet', '')) > 100 else message.get('snippet', '')
                }
                email_list.append(email_info)
                
            except Exception as e:
                continue
        
        response = make_response(jsonify({
            'emails': email_list,
            'total': len(email_list),
            'query': query
        }))
        return add_performance_headers(response, cache_duration=30)  # Cache for 30 seconds
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails')
def api_emails():
    """API endpoint for loading emails with pagination - much faster than full page load"""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    service = get_gmail_service()
    if not service:
        return jsonify({'error': 'Service not available'}), 500
    
    try:
        # Get parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)  # Cap at 50 for performance
        search_query = request.args.get('q', '')
        
        # Validate parameters
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 20
        
        # Build query
        query = 'in:inbox'
        if search_query:
            query += f' {search_query}'
        
        # Calculate fetch count efficiently
        if page == 1:
            fetch_count = min(per_page + 5, 100)
        else:
            fetch_count = min(page * per_page + 5, 100)
        
        # Get messages list
        results = service.users().messages().list(
            userId='me', 
            maxResults=fetch_count,
            q=query
        ).execute()
        
        messages = results.get('messages', [])
        total_messages = len(messages)
        
        # Calculate pagination
        total_pages = (total_messages + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_messages)
        current_page_messages = messages[start_idx:end_idx]
        
        # Batch fetch emails
        email_list = []
        if current_page_messages:
            message_ids = [msg['id'] for msg in current_page_messages]
            
            # Check cache first for any emails we already have
            cached_emails = {}
            uncached_ids = []
            
            for msg_id in message_ids:
                cached_data = get_cached_email(msg_id)
                if cached_data:
                    cached_emails[msg_id] = cached_data
                else:
                    uncached_ids.append(msg_id)
            
            # Only fetch uncached emails
            if uncached_ids:
                # Use batch request for better performance
                batch_request = service.new_batch_http_request()
                message_results = {}
                
                def callback(request_id, response, exception):
                    if exception is None:
                        message_results[request_id] = response
                    else:
                        message_results[request_id] = None
                
                # Add requests to batch
                for msg_id in uncached_ids:
                    batch_request.add(
                        service.users().messages().get(
                            userId='me',
                            id=msg_id,
                            format='metadata',
                            metadataHeaders=['From', 'Subject', 'Date']
                        ),
                        callback=callback,
                        request_id=msg_id
                    )
                
                # Execute batch
                batch_request.execute()
                
                # Process and cache new results
                for msg_id in uncached_ids:
                    message = message_results.get(msg_id)
                    if message and 'payload' in message:
                        try:
                            headers = message['payload']['headers']
                            
                            email_info = {
                                'id': msg_id,
                                'from': next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown'),
                                'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
                                'date': next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown'),
                                'snippet': message.get('snippet', '')[:150] + '...' if len(message.get('snippet', '')) > 150 else message.get('snippet', '')
                            }
                            
                            # Cache the email data
                            cache_email(msg_id, email_info)
                            cached_emails[msg_id] = email_info
                            
                        except Exception as e:
                            continue
            
            # Combine cached and newly fetched emails
            email_list = [cached_emails.get(msg_id) for msg_id in message_ids if cached_emails.get(msg_id)]
        
        # Return JSON response
        response_data = {
            'emails': email_list,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_messages': total_messages,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages,
                'prev_page': page - 1 if page > 1 else None,
                'next_page': page + 1 if page < total_pages else None,
                'start_item': start_idx + 1 if total_messages > 0 else 0,
                'end_item': end_idx
            },
            'search_query': search_query,
            'timestamp': datetime.now().isoformat()
        }
        
        response = make_response(jsonify(response_data))
        return add_performance_headers(response, cache_duration=60)  # Cache for 1 minute
        
    except Exception as e:
        print(f"API emails error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to load emails. Please try again.'}), 500

@app.route('/debug')
def debug():
    """Debug route to check authentication state"""
    debug_info = {
        'session_keys': list(session.keys()),
        'user_in_session': 'user' in session,
        'credentials_in_session': 'credentials' in session,
        'is_authenticated': is_authenticated(),
        'session_data': dict(session) if session else {}
    }
    return jsonify(debug_info)

# ===== CREDENTIALS EXPORT ENDPOINTS FOR OTHER SERVICES =====

@app.route('/api/credentials')
def export_credentials():
    """Export credentials for use in other services"""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    return jsonify({
        'access_token': session['credentials']['token'],
        'refresh_token': session['credentials'].get('refresh_token'),
        'token_uri': session['credentials']['token_uri'],
        'client_id': session['credentials']['client_id'],
        'client_secret': session['credentials']['client_secret'],
        'scopes': session['credentials']['scopes'],
        'user_email': session['user'].get('email')
    })

@app.route('/api/credentials/status')
def get_credentials_status():
    """Check if credentials are valid and active"""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        service = get_gmail_service()
        if service:
            service.users().getProfile(userId='me').execute()
            return jsonify({
                'status': 'valid',
                'user_email': session['user'].get('email'),
                'message': 'Credentials are working correctly'
            })
        else:
            return jsonify({'status': 'invalid', 'error': 'Failed to create service'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)