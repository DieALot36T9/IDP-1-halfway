#
import http.server
import socketserver
import json
import os
import cgi
import re
from urllib.parse import urlparse, parse_qs
import datetime

# Import the database functions we created
import database as db

# Define the server port
PORT = 8000
# Define the base directory for static files
STATIC_DIR = "static"
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

#  Main Request Handler
class SimpleHTTPRequestHandler(http.server.BaseHTTPRequestHandler):

    # --- ROUTING ---

    def get_routes(self):
        return {
            r'^/api/books/read/(\d+)$': self.handle_get_book_content,
            r'^/api/books$': self.handle_get_all_books,
            r'^/api/books/publisher$': self.handle_get_publisher_books,
            r'^/api/categories$': self.handle_get_categories,
            r'^/api/publisher-details$': self.handle_get_publisher_details,
            r'^/api/user/bookmarks$': self.handle_get_user_bookmarks,
            r'^/api/user/history$': self.handle_get_user_history,
        }

    def post_routes_json(self):
        return {
            '/api/login': self.handle_login,
            '/api/user/register': self.handle_user_register,
            '/api/user/profile': self.handle_user_profile_update,
            '/api/user/subscribe': self.handle_user_subscribe,
            '/api/books/delete': self.handle_book_delete,
            '/api/user/bookmarks/add': self.handle_bookmark_action,
            '/api/user/bookmarks/remove': self.handle_bookmark_action,
            '/api/user/history/add': self.handle_history_add,
        }

    def post_routes_form(self):
        return {
            '/api/publisher/register': self.handle_publisher_register,
            '/api/books/add': self.handle_book_add,
            '/api/books/update': self.handle_book_update,
        }

    # --- CORE HTTP HANDLERS ---

    def do_OPTIONS(self):
        """Handle pre-flight CORS requests."""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        """Handles all GET requests by routing them."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query = parse_qs(parsed_path.query)

        if path.startswith('/api/'):
            routes = self.get_routes()
            for route, handler in routes.items():
                match = re.match(route, path)
                if match:
                    handler(*match.groups(), query=query)
                    return
            self._send_response(404, {'error': 'API GET endpoint not found'})

        elif path.startswith('/static/'):
            self.handle_static_file(path)

        else:
            self.serve_index_html()

    def do_POST(self):
        """Handles all POST requests by routing them based on content type."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if not path.startswith('/api/'):
            self._send_response(404, {'error': 'Endpoint not found'})
            return

        content_type = self.headers.get('Content-Type', '')

        if 'application/json' in content_type:
            routes = self.post_routes_json()
            if path in routes:
                content_length = int(self.headers['Content-Length'])
                post_data = json.loads(self.rfile.read(content_length))
                routes[path](post_data)
            else:
                self._send_response(404, {'error': 'API JSON POST endpoint not found'})

        elif 'multipart/form-data' in content_type:
            routes = self.post_routes_form()
            if path in routes:
                form_data, file_paths = self._parse_multipart_form()
                routes[path](form_data, file_paths)
            else:
                self._send_response(404, {'error': 'API multipart POST endpoint not found'})

        else:
            self._send_response(415, {'error': 'Unsupported Media Type'})

    # --- GET REQUEST HANDLERS ---

    def handle_get_book_content(self, book_id_str, query):
        user, user_type = self._get_authenticated_entity()
        if not (user and user_type == 'user'):
            self._send_response(401, {'error': 'Authentication required to read books'})
            return

        try:
            book_id = int(book_id_str)
            if not db.check_user_subscription_for_book(user['user_id'], book_id):
                self._send_response(403, {'error': 'Subscription required for this category'})
                return

            pdf_path = db.get_book_pdf_path(book_id)
            if not pdf_path:
                self._send_response(404, {'error': 'PDF file not found for this book'})
                return

            pdf_full_path = os.path.join(UPLOADS_DIR, pdf_path)
            if os.path.exists(pdf_full_path):
                self.send_response(200)
                self.send_header('Content-type', 'application/pdf')
                self.end_headers()
                with open(pdf_full_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self._send_response(404, {'error': 'PDF file missing from server storage'})

        except ValueError:
            self._send_response(400, {'error': 'Invalid book ID format'})

    def handle_get_all_books(self, query):
        search_term = query.get('search', [''])[0]
        category_id = query.get('category_id', [None])[0]
        books = db.get_all_books(search_term=search_term, category_id=category_id)
        self._send_response(200, books)

    def handle_get_publisher_books(self, query):
        pub, pub_type = self._get_authenticated_entity()
        if pub and pub_type == 'publisher':
            books = db.get_books_by_publisher(pub['publisher_id'])
            self._send_response(200, books)
        else:
            self._send_response(401, {'error': 'Unauthorized'})

    def handle_get_categories(self, query):
        self._send_response(200, db.get_all_categories())

    def handle_get_publisher_details(self, query):
        pub_id = query.get('id', [None])[0]
        if pub_id:
            self._send_response(200, db.get_publisher_details(int(pub_id)))
        else:
            self._send_response(400, {'error': 'Publisher ID is required'})

    def handle_get_user_bookmarks(self, query):
        user, user_type = self._get_authenticated_entity()
        if user and user_type == 'user':
            self._send_response(200, db.get_user_bookmarks(user['user_id']))
        else:
            self._send_response(401, {'error': 'Unauthorized'})

    def handle_get_user_history(self, query):
        user, user_type = self._get_authenticated_entity()
        if user and user_type == 'user':
            self._send_response(200, db.get_reading_history(user['user_id']))
        else:
            self._send_response(401, {'error': 'Unauthorized'})

    # --- POST REQUEST HANDLERS ---

    def handle_login(self, data):
        email, password = data.get('email'), data.get('password')
        user_data = db.verify_user_login(email, password)
        if user_data:
            self._send_response(200, user_data)
            return
        pub_data = db.verify_publisher_login(email, password)
        if pub_data:
            self._send_response(200, pub_data)
            return
        self._send_response(401, {'error': 'Invalid credentials'})

    def handle_user_register(self, data):
        success = db.create_user(data.get('name'), data.get('email'), data.get('phone'), data.get('password'))
        if success:
            self._send_response(201, {'message': 'User created successfully'})
        else:
            self._send_response(400, {'error': 'Failed to create user, email may already exist'})

    def handle_user_profile_update(self, data):
        user, user_type = self._get_authenticated_entity()
        if not (user and user_type == 'user'):
            self._send_response(401, {'error': 'Unauthorized'})
            return

        current_user = db.get_user_by_id(user['user_id'])
        if not current_user:
            self._send_response(404, {'error': 'User not found'})
            return

        new_password = data.get('password') or current_user['password']
        success = db.update_user_profile(user['user_id'], data.get('name'), new_password)
        if success:
            self._send_response(200, {'message': 'Profile updated'})
        else:
            self._send_response(500, {'error': 'Failed to update profile'})

    def handle_user_subscribe(self, data):
        user, user_type = self._get_authenticated_entity()
        if not (user and user_type == 'user'):
            self._send_response(401, {'error': 'Unauthorized'})
            return

        category_id = data.get('category_id')
        if not category_id:
            self._send_response(400, {'error': 'Category ID is required'})
            return

        success = db.add_subscription_for_user(user['user_id'], category_id, 30)
        if success:
            self._send_response(200, {'message': f'Successfully subscribed to category {category_id}'})
        else:
            self._send_response(500, {'error': 'Failed to add subscription'})

    def handle_book_delete(self, data):
        pub, pub_type = self._get_authenticated_entity()
        if not (pub and pub_type == 'publisher'):
            self._send_response(401, {'error': 'Unauthorized'})
            return

        book_id = data.get('book_id')
        file_paths = db.delete_book(book_id)
        if file_paths:
            for key in ['cover_path', 'pdf_path']:
                if file_paths.get(key):
                    filepath = os.path.join(UPLOADS_DIR, file_paths[key])
                    if os.path.exists(filepath):
                        os.remove(filepath)
            self._send_response(200, {'message': 'Book deleted'})
        else:
            self._send_response(404, {'error': 'Book not found or failed to delete'})

    def handle_bookmark_action(self, data):
        user, user_type = self._get_authenticated_entity()
        if not (user and user_type == 'user'):
            self._send_response(401, {'error': 'Unauthorized'})
            return

        action_map = {
            '/api/user/bookmarks/add': db.add_bookmark,
            '/api/user/bookmarks/remove': db.remove_bookmark,
        }
        action = action_map.get(self.path)
        if action:
            action(user['user_id'], data.get('book_id'))
            self._send_response(200, {'message': 'Action successful'})
        else:
            self._send_response(400, {'error': 'Invalid bookmark action'})

    def handle_history_add(self, data):
        user, user_type = self._get_authenticated_entity()
        if user and user_type == 'user':
            db.add_to_reading_history(user['user_id'], data.get('book_id'))
            self._send_response(200, {'message': 'Action successful'})
        else:
            self._send_response(401, {'error': 'Unauthorized'})

    def handle_publisher_register(self, form_data, file_paths):
        image_path = file_paths.get('image')
        success = db.create_publisher(
            form_data.get('name'), form_data.get('email'), form_data.get('phone'),
            form_data.get('address'), form_data.get('description'),
            image_path, form_data.get('password')
        )
        if success:
            self._send_response(201, {'message': 'Publisher created'})
        else:
            self._send_response(400, {'error': 'Failed to create publisher'})

    def handle_book_add(self, form_data, file_paths):
        pub, pub_type = self._get_authenticated_entity()
        if not (pub and pub_type == 'publisher'):
            self._send_response(401, {'error': 'Unauthorized'})
            return

        success = db.add_book(
            form_data.get('name'), form_data.get('author_name'),
            form_data.get('description'), form_data.get('category_id'),
            file_paths.get('cover'), file_paths.get('pdf'),
            pub['publisher_id']
        )
        if success:
            self._send_response(201, {'message': 'Book added'})
        else:
            self._send_response(400, {'error': 'Failed to add book'})

    def handle_book_update(self, form_data, file_paths):
        pub, pub_type = self._get_authenticated_entity()
        if not (pub and pub_type == 'publisher'):
            self._send_response(401, {'error': 'Unauthorized'})
            return

        cover_path = file_paths.get('cover') or form_data.get('existing_cover_path')
        success = db.update_book(
            form_data.get('book_id'), form_data.get('name'),
            form_data.get('author_name'), form_data.get('description'),
            form_data.get('category_id'), cover_path
        )
        if success:
            self._send_response(200, {'message': 'Book updated'})
        else:
            self._send_response(400, {'error': 'Failed to update book'})

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
        
        user = db.get_entity_by_token(token, 'user')
        if user:
            return user, 'user'
        
        publisher = db.get_entity_by_token(token, 'publisher')
        if publisher:
            return publisher, 'publisher'
            
        return None, None

    def _parse_multipart_form(self):
        """Parses multipart/form-data and saves uploaded files."""
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST'}
        )
        
        parsed_data = {}
        for key in form.keys():
            if form[key].filename:
                continue
            parsed_data[key] = form[key].value

        file_paths = {}
        for key in form.keys():
            if form[key].filename:
                file_item = form[key]
                filename = os.path.basename(file_item.filename)
                
                if 'cover' in key.lower() or 'image' in key.lower():
                    save_dir = os.path.join(UPLOADS_DIR, "covers")
                elif 'pdf' in key.lower():
                    save_dir = os.path.join(UPLOADS_DIR, "pdfs")
                else:
                    continue # Skip unknown file types

                os.makedirs(save_dir, exist_ok=True)
                filepath = os.path.join(save_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(file_item.file.read())
                
                # Store the relative path for the database
                file_paths[key] = os.path.join(os.path.basename(save_dir), filename).replace("\\", "/")

        return parsed_data, file_paths

    def handle_static_file(self, path):
        """Serves a static file."""
        filepath = path.lstrip('/')

        # Security: Prevent directory traversal and access to sensitive files
        normalized_path = os.path.normpath(filepath).replace('\\', '/')
        if '..' in normalized_path or 'uploads/pdfs' in normalized_path:
            self._send_response(403, {'error': 'Access denied'})
            return

        if os.path.exists(filepath) and not os.path.isdir(filepath):
            mime_map = {
                '.html': 'text/html',
                '.css': 'text/css',
                '.js': 'application/javascript',
                '.mjs': 'application/javascript',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
            }
            ext = os.path.splitext(filepath)[1]
            mime_type = mime_map.get(ext, 'text/plain')
            
            self.send_response(200)
            self.send_header('Content-type', mime_type)
            self.end_headers()
            with open(filepath, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self._send_response(404, {'error': 'File not found'})

    def serve_index_html(self):
        """Serves the main application shell."""
        try:
            with open('templates/index.html', 'rb') as f:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self._send_response(404, {'error': 'index.html not found'})


# --- Main Execution Block ---
if __name__ == "__main__":
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