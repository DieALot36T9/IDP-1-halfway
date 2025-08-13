# admin_server.py
# A separate server for the admin panel.

import http.server
import socketserver
import json
import os
import re
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

    # --- ROUTING ---

    def get_routes(self):
        return {
            r'^/api/admin/users/(\d+)$': self.handle_get_single_user,
            r'^/api/admin/publishers/(\d+)$': self.handle_get_single_publisher,
            r'^/api/admin/users$': self.handle_get_all_users,
            r'^/api/admin/publishers$': self.handle_get_all_publishers,
            r'^/api/admin/books$': self.handle_get_all_books,
            r'^/api/admin/categories$': self.handle_get_all_categories,
        }

    def post_routes(self):
        return {
            '/api/admin/login': self.handle_admin_login,
            '/api/admin/users/update': self.handle_user_update,
            '/api/admin/publishers/update': self.handle_publisher_update,
            '/api/admin/users/add_subscription': self.handle_user_add_subscription,
            '/api/admin/users/remove_subscription': self.handle_user_remove_subscription,
            '/api/admin/users/delete': self.handle_user_delete,
            '/api/admin/publishers/delete': self.handle_publisher_delete,
            '/api/admin/categories/add': self.handle_category_add,
            '/api/admin/categories/delete': self.handle_category_delete,
            '/api/admin/books/delete': self.handle_book_delete,
        }

    # --- CORE HTTP HANDLERS ---

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path.startswith('/api/admin/'):
            admin = self._get_auth_admin()
            if not admin:
                self._send_response(401, {'error': 'Unauthorized: Admin access required'})
                return

            routes = self.get_routes()
            for route, handler in routes.items():
                match = re.match(route, path)
                if match:
                    handler(*match.groups())
                    return
            self._send_response(404, {'error': 'Admin API GET endpoint not found'})
        
        elif path.startswith('/static/'):
            self.handle_static_file(path)
        else:
            self.serve_admin_html()

    def do_POST(self):
        path = urlparse(self.path).path

        try:
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length))
        except (TypeError, json.JSONDecodeError):
            self._send_response(400, {'error': 'Invalid JSON body'})
            return

        if path == '/api/admin/login':
            self.handle_admin_login(post_data)
            return

        if not self._get_auth_admin():
            self._send_response(401, {'error': 'Unauthorized: Admin access required'})
            return

        routes = self.post_routes()
        handler = routes.get(path)
        if handler:
            handler(post_data)
        else:
            self._send_response(404, {'error': 'Admin API POST endpoint not found'})

    # --- GET REQUEST HANDLERS ---

    def handle_get_single_user(self, user_id_str):
        try:
            user_data = db.get_user_by_id_for_admin(int(user_id_str))
            self._send_response(200 if user_data else 404, user_data or {'error': 'User not found'})
        except ValueError:
            self._send_response(400, {'error': 'Invalid User ID format'})

    def handle_get_single_publisher(self, pub_id_str):
        try:
            pub_data = db.get_publisher_by_id_for_admin(int(pub_id_str))
            self._send_response(200 if pub_data else 404, pub_data or {'error': 'Publisher not found'})
        except ValueError:
            self._send_response(400, {'error': 'Invalid Publisher ID format'})

    def handle_get_all_users(self):
        self._send_response(200, db.get_all_users_for_admin())

    def handle_get_all_publishers(self):
        self._send_response(200, db.get_all_publishers_for_admin())

    def handle_get_all_books(self):
        self._send_response(200, db.get_all_books())

    def handle_get_all_categories(self):
        self._send_response(200, db.get_all_categories())

    # --- POST REQUEST HANDLERS ---

    def handle_admin_login(self, data):
        admin_data = db.verify_admin_login(data.get('email'), data.get('password'))
        self._send_response(200 if admin_data else 401, admin_data or {'error': 'Invalid admin credentials'})

    def handle_user_update(self, data):
        success = db.update_user_by_admin(
            data.get('user_id'), data.get('name'), data.get('phone')
        )
        self._send_response(200 if success else 400, {'success': success})

    def handle_publisher_update(self, data):
        success = db.update_publisher_by_admin(
            data.get('publisher_id'), data.get('name'), data.get('phone'),
            data.get('address'), data.get('description')
        )
        self._send_response(200 if success else 400, {'success': success})

    def handle_user_add_subscription(self, data):
        success = db.add_subscription_for_user(
            data.get('user_id'), data.get('category_id')
        )
        self._send_response(200 if success else 400, {'success': success})

    def handle_user_remove_subscription(self, data):
        success = db.remove_subscription_for_user(
            data.get('user_id'), data.get('category_id')
        )
        self._send_response(200 if success else 400, {'success': success})

    def handle_user_delete(self, data):
        success = db.delete_user_by_admin(data.get('user_id'))
        self._send_response(200 if success else 400, {'success': success})

    def handle_publisher_delete(self, data):
        files = db.delete_publisher_by_admin(data.get('publisher_id'))
        if files:
            for img in files.get('publisher_images', []):
                if img: os.remove(os.path.join(UPLOADS_DIR, img))
            self._send_response(200, {'success': True, 'message': 'Publisher deleted'})
        else:
            self._send_response(400, {'success': False})

    def handle_category_add(self, data):
        success = db.add_category(data.get('name'))
        self._send_response(201 if success else 400, {'success': success})

    def handle_category_delete(self, data):
        success = db.delete_category(data.get('category_id'))
        self._send_response(200 if success else 400, {'success': success})

    def handle_book_delete(self, data):
        paths = db.delete_book(data.get('book_id'))
        if paths:
            self._send_response(200, {'message': 'Book deleted'})
        else:
            self._send_response(404, {'error': 'Book not found'})

    # --- HELPER METHODS ---

    def _send_response(self, status_code, data, content_type='application/json'):
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        if data is not None:
            response_data = json.dumps(data, cls=DateTimeEncoder).encode('utf-8')
            self.wfile.write(response_data)

    def _get_auth_admin(self):
        auth_header = self.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return db.get_entity_by_token(auth_header.split(' ')[1], 'admin')
        return None
        
    def handle_static_file(self, path):
        filepath = path.lstrip('/')
        if os.path.exists(filepath) and not os.path.isdir(filepath):
            mime_map = {'.css': 'text/css', '.js': 'application/javascript'}
            ext = os.path.splitext(filepath)[1]
            mime_type = mime_map.get(ext, 'text/plain')

            self.send_response(200)
            self.send_header('Content-type', mime_type)
            self.end_headers()
            with open(filepath, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self._send_response(404, {'error': f'Static file not found: {filepath}'})

    def serve_admin_html(self):
        try:
            with open('templates/admin.html', 'rb') as f:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self._send_response(404, {'error': 'admin.html not found'})

if __name__ == "__main__":
    with socketserver.TCPServer(("", ADMIN_PORT), AdminHTTPRequestHandler) as httpd:
        print(f"Admin server running at http://localhost:{ADMIN_PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping admin server...")
            httpd.shutdown()