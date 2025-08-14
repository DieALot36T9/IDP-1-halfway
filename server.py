# server.py
# Main server for the application, now refactored to use request handlers.

import http.server
import socketserver
import json
import os
import cgi
from urllib.parse import urlparse
import datetime

# Import the new database and handler modules
from db.user_queries import get_entity_by_token
from handlers.main_handler import handle_get_request, handle_post_request

# Define server constants
PORT = 8000
STATIC_DIR = "static"
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects."""
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

class SimpleHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    Handles HTTP requests by dispatching them to the appropriate
    functions in the main_handler module.
    """

    # --- HELPER METHODS ---

    def _send_response(self, status_code, data, content_type='application/json'):
        """Helper to send a standardized HTTP response."""
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        if data is not None:
            response_data = json.dumps(data, cls=DateTimeEncoder).encode('utf-8')
            self.wfile.write(response_data)

    def _get_auth_token(self):
        """Extracts the Bearer token from the Authorization header."""
        auth_header = self.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
        return None

    def _get_authenticated_entity(self):
        """Validates the token and returns the authenticated user or publisher."""
        token = self._get_auth_token()
        if not token:
            return None, None
        
        user = get_entity_by_token(token, 'user')
        if user:
            return user, 'user'
        
        publisher = get_entity_by_token(token, 'publisher')
        if publisher:
            return publisher, 'publisher'
            
        return None, None

    def _parse_multipart_form(self):
        """Parses multipart/form-data and saves uploaded files."""
        headers = {
            'content-type': self.headers['content-type'],
            'content-length': self.headers['content-length'],
        }
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=headers,
            environ={'REQUEST_METHOD': 'POST'}
        )
        
        parsed_data = {}
        for key in form:
            if not form[key].filename:
                parsed_data[key] = form[key].value

        file_paths = {}
        os.makedirs(os.path.join(UPLOADS_DIR, "covers"), exist_ok=True)
        os.makedirs(os.path.join(UPLOADS_DIR, "pdfs"), exist_ok=True)

        for key in form:
            if form[key].filename:
                file_item = form[key]
                filename = os.path.basename(file_item.filename)
                
                if 'cover' in key.lower() or 'image' in key.lower():
                    save_dir = os.path.join(UPLOADS_DIR, "covers")
                elif 'pdf' in key.lower():
                    save_dir = os.path.join(UPLOADS_DIR, "pdfs")
                else:
                    continue

                filepath = os.path.join(save_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(file_item.file.read())
                
                # Store the relative path for database insertion
                file_paths[key] = os.path.join(os.path.basename(save_dir), filename).replace("\\", "/")

        return parsed_data, file_paths

    # --- HTTP METHOD HANDLERS (Now simplified) ---

    def do_OPTIONS(self):
        """Handle pre-flight CORS requests."""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        """Dispatches GET requests to the main handler."""
        handle_get_request(self)

    def do_POST(self):
        """Dispatches POST requests to the main handler."""
        handle_post_request(self)


# --- Main Execution Block ---
if __name__ == "__main__":
    # Ensure necessary directories exist
    os.makedirs(os.path.join(UPLOADS_DIR, "covers"), exist_ok=True)
    os.makedirs(os.path.join(UPLOADS_DIR, "pdfs"), exist_ok=True)

    with socketserver.TCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
        print(f"Serving at port {PORT}")
        print(f"Access the application at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server...")
            httpd.shutdown()