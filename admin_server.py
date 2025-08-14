# admin_server.py
# A separate server for the admin panel, now refactored to use request handlers.

import http.server
import socketserver
import json
import os
from urllib.parse import urlparse
import datetime

# Import the new database and handler modules
from db.user_queries import get_entity_by_token
from handlers.admin_handler import handle_admin_get_request, handle_admin_post_request

# Define server constants
ADMIN_PORT = 8001
STATIC_DIR = "static"
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects."""
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

class AdminHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    Handles HTTP requests by dispatching them to the appropriate
    functions in the admin_handler module.
    """

    def _send_response(self, status_code, data, content_type='application/json'):
        """Helper to send a standardized HTTP response."""
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        if data is not None:
            response_data = json.dumps(data, cls=DateTimeEncoder).encode('utf-8')
            self.wfile.write(response_data)

    def _get_auth_admin(self):
        """Validates the token and returns the authenticated admin."""
        auth_header = self.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            # Use the refactored database query function
            return get_entity_by_token(token, 'admin')
        return None

    def do_OPTIONS(self):
        """Handle pre-flight CORS requests."""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        """Dispatches GET requests to the admin handler."""
        handle_admin_get_request(self)

    def do_POST(self):
        """Dispatches POST requests to the admin handler."""
        handle_admin_post_request(self)

# --- Main Execution Block ---
if __name__ == "__main__":
    with socketserver.TCPServer(("", ADMIN_PORT), AdminHTTPRequestHandler) as httpd:
        print(f"Admin server running at http://localhost:{ADMIN_PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping admin server...")
            httpd.shutdown()