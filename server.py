#
import http.server
import socketserver
import json
import os
import cgi
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

    # HELPER METHODS

    def _send_response(self, status_code, data, content_type='application/json'):
        """Helper to send a standardized HTTP response."""
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        # Add CORS headers to allow requests from any origin
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        if data is not None:
            # Use the custom encoder for datetime objects
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
                
                file_paths[key] = os.path.join(os.path.basename(save_dir), filename).replace("\\", "/")

        return parsed_data, file_paths

    # --- HTTP METHOD HANDLERS ---

    def do_OPTIONS(self):
        """Handle pre-flight CORS requests."""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        """Handles all GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query = parse_qs(parsed_path.query)

        # --- API Routes ---
        if path.startswith('/api/'):
            if path.startswith('/api/books/read/'):
                user, user_type = self._get_authenticated_entity()
                if not (user and user_type == 'user'):
                    self._send_response(401, {'error': 'Authentication required to read books'})
                    return
                
                try:
                    book_id = int(path.split('/')[-1])
                    is_subscribed = db.check_user_subscription_for_book(user['user_id'], book_id)
                    
                    if not is_subscribed:
                        self._send_response(403, {'error': 'Subscription required for this category'})
                        return
                    
                    pdf_relative_path = db.get_book_pdf_path(book_id)
                    if not pdf_relative_path:
                        self._send_response(404, {'error': 'PDF file not found for this book'})
                        return
                        
                    pdf_full_path = os.path.join(UPLOADS_DIR, pdf_relative_path)
                    if os.path.exists(pdf_full_path):
                        self.send_response(200)
                        self.send_header('Content-type', 'application/pdf')
                        self.end_headers()
                        with open(pdf_full_path, 'rb') as f:
                            self.wfile.write(f.read())
                    else:
                        self._send_response(404, {'error': 'PDF file missing from server storage'})

                except (ValueError, IndexError):
                    self._send_response(400, {'error': 'Invalid book ID format'})
                return
            
            # --- MODIFIED: This block now handles category filtering ---
            if path == '/api/books':
                search_term = query.get('search', [''])[0]
                category_id = query.get('category_id', [None])[0]
                books = db.get_all_books(search_term=search_term, category_id=category_id)
                self._send_response(200, books)
            
            elif path == '/api/books/publisher':
                pub, pub_type = self._get_authenticated_entity()
                if pub and pub_type == 'publisher':
                    books = db.get_books_by_publisher(pub['publisher_id'])
                    self._send_response(200, books)
                else:
                    self._send_response(401, {'error': 'Unauthorized'})

            elif path == '/api/categories':
                categories = db.get_all_categories()
                self._send_response(200, categories)

            elif path == '/api/publisher-details':
                pub_id = query.get('id', [None])[0]
                if pub_id:
                    details = db.get_publisher_details(int(pub_id))
                    self._send_response(200, details)
                else:
                    self._send_response(400, {'error': 'Publisher ID is required'})

            elif path == '/api/user/bookmarks':
                user, user_type = self._get_authenticated_entity()
                if user and user_type == 'user':
                    bookmarks = db.get_user_bookmarks(user['user_id'])
                    self._send_response(200, bookmarks)
                else:
                    self._send_response(401, {'error': 'Unauthorized'})

            elif path == '/api/user/history':
                user, user_type = self._get_authenticated_entity()
                if user and user_type == 'user':
                    history = db.get_reading_history(user['user_id'])
                    self._send_response(200, history)
                else:
                    self._send_response(401, {'error': 'Unauthorized'})
            
            else:
                self._send_response(404, {'error': 'API endpoint not found'})

        # --- Static File Serving ---
        elif path.startswith('/static/'):
            filepath = path.lstrip('/')
            
            normalized_path = os.path.normpath(filepath).replace('\\', '/')
            if 'uploads/pdfs' in normalized_path:
                self._send_response(403, {'error': 'Direct access to PDF files is forbidden'})
                return

            if os.path.exists(filepath) and not os.path.isdir(filepath):
                mime_type = 'text/plain'
                if filepath.endswith('.html'): mime_type = 'text/html'
                if filepath.endswith('.css'): mime_type = 'text/css'
                if filepath.endswith(('.js', '.mjs')): mime_type = 'application/javascript'
                if filepath.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    ext = filepath.split('.')[-1]
                    mime_type = f'image/{ext}'
                
                self.send_response(200)
                self.send_header('Content-type', mime_type)
                self.end_headers()
                with open(filepath, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self._send_response(404, {'error': 'File not found'})

        # --- Serve the main application shell ---
        else:
            try:
                with open('templates/index.html', 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self._send_response(404, {'error': 'index.html not found'})

    def do_POST(self):
        """Handles all POST requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path.startswith('/api/'):
            content_type = self.headers.get('Content-Type', '')

            if 'application/json' in content_type:
                content_length = int(self.headers['Content-Length'])
                post_data = json.loads(self.rfile.read(content_length))

                if path == '/api/login':
                    email = post_data.get('email')
                    password = post_data.get('password')
                    user_data = db.verify_user_login(email, password)
                    if user_data:
                        self._send_response(200, user_data)
                        return
                    pub_data = db.verify_publisher_login(email, password)
                    if pub_data:
                        self._send_response(200, pub_data)
                        return
                    self._send_response(401, {'error': 'Invalid credentials'})

                elif path == '/api/user/register':
                    success = db.create_user(post_data.get('name'), post_data.get('email'), post_data.get('phone'), post_data.get('password'))
                    if success: self._send_response(201, {'message': 'User created successfully'})
                    else: self._send_response(400, {'error': 'Failed to create user, email may already exist'})
                
                elif path == '/api/user/profile':
                    user, user_type = self._get_authenticated_entity()
                    if user and user_type == 'user':
                        # FIX: Password update should be optional
                        current_user_data = db.get_user_by_id(user['user_id']) # You'll need to create this helper in db
                        new_password = post_data.get('password') if post_data.get('password') else current_user_data['password']
                        success = db.update_user_profile(user['user_id'], post_data.get('name'), new_password)
                        if success: self._send_response(200, {'message': 'Profile updated'})
                        else: self._send_response(500, {'error': 'Failed to update profile'})
                    else:
                        self._send_response(401, {'error': 'Unauthorized'})

                elif path == '/api/user/subscribe':
                    user, user_type = self._get_authenticated_entity()
                    if not (user and user_type == 'user'):
                        self._send_response(401, {'error': 'Unauthorized'})
                        return
                    
                    category_id = post_data.get('category_id')
                    if not category_id:
                        self._send_response(400, {'error': 'Category ID is required'})
                        return

                    success = db.add_subscription_for_user(user['user_id'], category_id, 30)
                    if success:
                        self._send_response(200, {'message': f'Successfully subscribed to category {category_id}'})
                    else:
                        self._send_response(500, {'error': 'Failed to add subscription'})
                
                elif path == '/api/books/delete':
                    pub, pub_type = self._get_authenticated_entity()
                    if pub and pub_type == 'publisher':
                        book_id = post_data.get('book_id')
                        file_paths = db.delete_book(book_id)
                        if file_paths:
                            if file_paths.get('cover_path'): 
                                cover_file = os.path.join(UPLOADS_DIR, file_paths['cover_path'])
                                if os.path.exists(cover_file): os.remove(cover_file)
                            if file_paths.get('pdf_path'): 
                                pdf_file = os.path.join(UPLOADS_DIR, file_paths['pdf_path'])
                                if os.path.exists(pdf_file): os.remove(pdf_file)
                            self._send_response(200, {'message': 'Book deleted'})
                        else:
                            self._send_response(404, {'error': 'Book not found or failed to delete'})
                    else:
                        self._send_response(401, {'error': 'Unauthorized'})
                
                elif path in ['/api/user/bookmarks/add', '/api/user/bookmarks/remove', '/api/user/history/add']:
                    user, user_type = self._get_authenticated_entity()
                    if user and user_type == 'user':
                        book_id = post_data.get('book_id')
                        if path == '/api/user/bookmarks/add': db.add_bookmark(user['user_id'], book_id)
                        elif path == '/api/user/bookmarks/remove': db.remove_bookmark(user['user_id'], book_id)
                        elif path == '/api/user/history/add': db.add_to_reading_history(user['user_id'], book_id)
                        self._send_response(200, {'message': 'Action successful'})
                    else:
                        self._send_response(401, {'error': 'Unauthorized'})

                else:
                    self._send_response(404, {'error': 'API endpoint not found for JSON POST'})

            elif 'multipart/form-data' in content_type:
                form_data, file_paths = self._parse_multipart_form()

                if path == '/api/publisher/register':
                    image_file = file_paths.get('image')
                    image_path_for_db = image_file if image_file else None
                    success = db.create_publisher(form_data.get('name'), form_data.get('email'), form_data.get('phone'), form_data.get('address'), form_data.get('description'), image_path_for_db, form_data.get('password'))
                    if success: self._send_response(201, {'message': 'Publisher created'})
                    else: self._send_response(400, {'error': 'Failed to create publisher'})

                elif path == '/api/books/add':
                    pub, pub_type = self._get_authenticated_entity()
                    if pub and pub_type == 'publisher':
                        cover_file = file_paths.get('cover')
                        pdf_file = file_paths.get('pdf')
                        cover_path_for_db = cover_file if cover_file else None
                        
                        success = db.add_book(
                            form_data.get('name'),
                            form_data.get('author_name'),
                            form_data.get('description'),
                            form_data.get('category_id'),
                            cover_path_for_db,
                            pdf_file,
                            pub['publisher_id']
                        )
                        if success: self._send_response(201, {'message': 'Book added'})
                        else: self._send_response(400, {'error': 'Failed to add book'})
                    else:
                        self._send_response(401, {'error': 'Unauthorized'})

                elif path == '/api/books/update':
                    pub, pub_type = self._get_authenticated_entity()
                    if pub and pub_type == 'publisher':
                        new_cover_file = file_paths.get('cover')
                        cover_path = new_cover_file if new_cover_file else form_data.get('existing_cover_path')
                        
                        success = db.update_book(
                            form_data.get('book_id'),
                            form_data.get('name'),
                            form_data.get('author_name'),
                            form_data.get('description'),
                            form_data.get('category_id'),
                            cover_path
                        )
                        if success: self._send_response(200, {'message': 'Book updated'})
                        else: self._send_response(400, {'error': 'Failed to update book'})
                    else:
                        self._send_response(401, {'error': 'Unauthorized'})

                else:
                    self._send_response(404, {'error': 'API endpoint not found for multipart POST'})
            
            else:
                self._send_response(415, {'error': 'Unsupported Media Type'})
        else:
            self._send_response(404, {'error': 'Endpoint not found'})


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