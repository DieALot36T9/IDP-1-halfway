# admin_server.py
# A separate server for the admin panel.

import http.server
import socketserver
import json
import os
from urllib.parse import urlparse, parse_qs
import datetime

import database as db

# Define the admin server port
ADMIN_PORT = 8001
STATIC_DIR = "static"
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")

# Use the same custom JSON encoder from your main server.py
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

class AdminHTTPRequestHandler(http.server.BaseHTTPRequestHandler):

    def _send_response(self, status_code, data, content_type='application/json'):
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*') # Allow requests from the main app's origin if needed
        self.end_headers()
        if data is not None:
            response_data = json.dumps(data, cls=DateTimeEncoder).encode('utf-8')
            self.wfile.write(response_data)

    def _get_auth_admin(self):
        """Validates the token and returns the authenticated admin."""
        auth_header = self.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            return db.get_entity_by_token(token, 'admin')
        return None

    def do_OPTIONS(self):
        """Handle pre-flight CORS requests."""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        """Handles GET requests for admin panel and its API."""
        path = urlparse(self.path).path

        if path.startswith('/api/admin/'):
            admin = self._get_auth_admin()
            if not admin:
                self._send_response(401, {'error': 'Unauthorized: Admin access required'})
                return

            # --- NEW: Routes to get a single user or publisher for editing ---
            if path.startswith('/api/admin/users/'):
                try:
                    user_id = int(path.split('/')[-1])
                    user_data = db.get_user_by_id_for_admin(user_id)
                    if user_data:
                        self._send_response(200, user_data)
                    else:
                        self._send_response(404, {'error': 'User not found'})
                except (ValueError, IndexError):
                    self._send_response(400, {'error': 'Invalid User ID format'})
                return
                
            elif path.startswith('/api/admin/publishers/'):
                try:
                    pub_id = int(path.split('/')[-1])
                    pub_data = db.get_publisher_by_id_for_admin(pub_id)
                    if pub_data:
                        self._send_response(200, pub_data)
                    else:
                        self._send_response(404, {'error': 'Publisher not found'})
                except (ValueError, IndexError):
                    self._send_response(400, {'error': 'Invalid Publisher ID format'})
                return

            # --- Existing List Routes ---
            if path == '/api/admin/users':
                users = db.get_all_users_for_admin()
                self._send_response(200, users)
            elif path == '/api/admin/publishers':
                publishers = db.get_all_publishers_for_admin()
                self._send_response(200, publishers)
            elif path == '/api/admin/books':
                books = db.get_all_books()
                self._send_response(200, books)
            elif path == '/api/admin/categories':
                categories = db.get_all_categories()
                self._send_response(200, categories)    
            else:
                self._send_response(404, {'error': 'Admin API endpoint not found'})
        
        elif path.startswith('/static/'):
            filepath = path.lstrip('/')
            if os.path.exists(filepath):
                mime_type = 'text/plain'
                if filepath.endswith('.html'): mime_type = 'text/html'
                if filepath.endswith('.css'): mime_type = 'text/css'
                if filepath.endswith('.js'): mime_type = 'application/javascript'
                self.send_response(200)
                self.send_header('Content-type', mime_type)
                self.end_headers()
                with open(filepath, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self._send_response(404, {'error': f'Static file not found: {filepath}'})

        else:
            try:
                with open('templates/admin.html', 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self._send_response(404, {'error': 'admin.html not found'})

    def do_POST(self):
        """Handles POST requests for admin actions."""
        path = urlparse(self.path).path
        content_length = int(self.headers['Content-Length'])
        post_data = json.loads(self.rfile.read(content_length))

        if path == '/api/admin/login':
            admin_data = db.verify_admin_login(post_data.get('email'), post_data.get('password'))
            if admin_data:
                self._send_response(200, admin_data)
            else:
                self._send_response(401, {'error': 'Invalid admin credentials'})
            return

        admin = self._get_auth_admin()
        if not admin:
            self._send_response(401, {'error': 'Unauthorized: Admin access required'})
            return
        
        # --- NEW: Endpoints for updating user and publisher details ---
        if path == '/api/admin/users/update':
            success = db.update_user_by_admin(
                post_data.get('user_id'),
                post_data.get('name'),
                post_data.get('phone')
            )
            self._send_response(200 if success else 400, {'success': success})

        elif path == '/api/admin/publishers/update':
            success = db.update_publisher_by_admin(
                post_data.get('publisher_id'),
                post_data.get('name'),
                post_data.get('phone'),
                post_data.get('address'),
                post_data.get('description')
            )
            self._send_response(200 if success else 400, {'success': success})
        
        # --- Existing POST Routes ---
        elif path == '/api/admin/users/add_subscription':
            success = db.add_subscription_for_user(
                post_data.get('user_id'), 
                post_data.get('category_id')
            )
            self._send_response(200 if success else 400, {'success': success})
        
        elif path == '/api/admin/users/remove_subscription':
            success = db.remove_subscription_for_user(
                post_data.get('user_id'),
                post_data.get('category_id')
            )
            self._send_response(200 if success else 400, {'success': success})
        
        elif path == '/api/admin/users/delete':
            success = db.delete_user_by_admin(post_data.get('user_id'))
            self._send_response(200 if success else 400, {'success': success})

        elif path == '/api/admin/publishers/delete':
            files_to_delete = db.delete_publisher_by_admin(post_data.get('publisher_id'))
            if files_to_delete:
                if files_to_delete.get('publisher_images'):
                    for img in files_to_delete['publisher_images']:
                        if img: os.remove(os.path.join(UPLOADS_DIR, img))
                self._send_response(200, {'success': True, 'message': 'Publisher and assets deleted'})
            else:
                self._send_response(400, {'success': False})

        elif path == '/api/admin/categories/add':
            success = db.add_category(post_data.get('name'))
            self._send_response(201 if success else 400, {'success': success})
        
        elif path == '/api/admin/categories/delete':
            success = db.delete_category(post_data.get('category_id'))
            self._send_response(200 if success else 400, {'success': success})

        elif path == '/api/admin/books/delete':
            file_paths = db.delete_book(post_data.get('book_id'))
            if file_paths:
                self._send_response(200, {'message': 'Book deleted'})
            else:
                self._send_response(404, {'error': 'Book not found'})
        
        else:
            self._send_response(404, {'error': 'Admin API endpoint not found'})

if __name__ == "__main__":
    with socketserver.TCPServer(("", ADMIN_PORT), AdminHTTPRequestHandler) as httpd:
        print(f"Admin server running at http://localhost:{ADMIN_PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping admin server...")
            httpd.shutdown()