# handlers/admin_handler.py
# Contains the request handling logic for the admin server.

import json
import os
from urllib.parse import urlparse

# Import database functions
from db.user_queries import get_entity_by_token
from db.admin_queries import (
    verify_admin_login, get_all_users_for_admin, delete_user_by_admin,
    get_all_publishers_for_admin, delete_publisher_by_admin,
    get_user_by_id_for_admin, update_user_by_admin,
    get_publisher_by_id_for_admin, update_publisher_by_admin
)
from db.book_queries import get_all_books, delete_book
from db.category_queries import get_all_categories, add_category, delete_category
from db.subscription_queries import add_subscription_for_user, remove_subscription_for_user

# Constants
UPLOADS_DIR = os.path.join("static", "uploads")

def handle_admin_get_request(handler):
    """Handles all GET requests for the admin server."""
    path = urlparse(handler.path).path

    if path.startswith('/api/admin/'):
        # Admin API routes require authentication
        admin = handler._get_auth_admin()
        if not admin:
            handler._send_response(401, {'error': 'Unauthorized: Admin access required'})
            return

        if path.startswith('/api/admin/users/'):
            handle_get_user_by_id(handler, path)
        elif path.startswith('/api/admin/publishers/'):
            handle_get_publisher_by_id(handler, path)
        elif path == '/api/admin/users':
            users = get_all_users_for_admin()
            handler._send_response(200, users)
        elif path == '/api/admin/publishers':
            publishers = get_all_publishers_for_admin()
            handler._send_response(200, publishers)
        elif path == '/api/admin/books':
            books = get_all_books()
            handler._send_response(200, books)
        elif path == '/api/admin/categories':
            categories = get_all_categories()
            handler._send_response(200, categories)
        else:
            handler._send_response(404, {'error': 'Admin API endpoint not found'})

    elif path.startswith('/static/'):
        # Serve static files for the admin panel
        handle_admin_static_files(handler, path)

    else:
        # Serve the main admin.html file
        serve_admin_index(handler)

def handle_admin_post_request(handler):
    """Handles all POST requests for the admin server."""
    path = urlparse(handler.path).path

    try:
        content_length = int(handler.headers['Content-Length'])
        post_data = json.loads(handler.rfile.read(content_length))
    except (TypeError, json.JSONDecodeError):
        handler._send_response(400, {'error': 'Invalid JSON'})
        return

    if path == '/api/admin/login':
        handle_admin_login(handler, post_data)
        return

    # All other POST routes require admin authentication
    admin = handler._get_auth_admin()
    if not admin:
        handler._send_response(401, {'error': 'Unauthorized: Admin access required'})
        return

    route_map = {
        '/api/admin/users/update': handle_update_user,
        '/api/admin/publishers/update': handle_update_publisher,
        '/api/admin/users/add_subscription': handle_add_subscription,
        '/api/admin/users/remove_subscription': handle_remove_subscription,
        '/api/admin/users/delete': handle_delete_user,
        '/api/admin/publishers/delete': handle_delete_publisher,
        '/api/admin/categories/add': handle_add_category,
        '/api/admin/categories/delete': handle_delete_category,
        '/api/admin/books/delete': handle_admin_delete_book
    }

    if path in route_map:
        route_map[path](handler, post_data)
    else:
        handler._send_response(404, {'error': 'Admin API endpoint not found'})

# --- GET Request Handlers ---

def handle_get_user_by_id(handler, path):
    """Gets a single user's details for editing."""
    try:
        user_id = int(path.split('/')[-1])
        user_data = get_user_by_id_for_admin(user_id)
        if user_data:
            handler._send_response(200, user_data)
        else:
            handler._send_response(404, {'error': 'User not found'})
    except (ValueError, IndexError):
        handler._send_response(400, {'error': 'Invalid User ID format'})

def handle_get_publisher_by_id(handler, path):
    """Gets a single publisher's details for editing."""
    try:
        pub_id = int(path.split('/')[-1])
        pub_data = get_publisher_by_id_for_admin(pub_id)
        if pub_data:
            handler._send_response(200, pub_data)
        else:
            handler._send_response(404, {'error': 'Publisher not found'})
    except (ValueError, IndexError):
        handler._send_response(400, {'error': 'Invalid Publisher ID format'})

def handle_admin_static_files(handler, path):
    """Serves static files for the admin panel."""
    filepath = path.lstrip('/')
    if os.path.exists(filepath):
        mime_type = 'text/plain'
        if filepath.endswith('.html'): mime_type = 'text/html'
        elif filepath.endswith('.css'): mime_type = 'text/css'
        elif filepath.endswith('.js'): mime_type = 'application/javascript'

        handler.send_response(200)
        handler.send_header('Content-type', mime_type)
        handler.end_headers()
        with open(filepath, 'rb') as f:
            handler.wfile.write(f.read())
    else:
        handler._send_response(404, {'error': f'Static file not found: {filepath}'})

def serve_admin_index(handler):
    """Serves the main admin.html file."""
    try:
        with open('templates/admin.html', 'rb') as f:
            handler.send_response(200)
            handler.send_header('Content-type', 'text/html')
            handler.end_headers()
            handler.wfile.write(f.read())
    except FileNotFoundError:
        handler._send_response(404, {'error': 'admin.html not found'})

# --- POST Request Handlers ---

def handle_admin_login(handler, post_data):
    """Handles admin login."""
    admin_data = verify_admin_login(post_data.get('email'), post_data.get('password'))
    if admin_data:
        handler._send_response(200, admin_data)
    else:
        handler._send_response(401, {'error': 'Invalid admin credentials'})

def handle_update_user(handler, post_data):
    """Updates user details from the admin panel."""
    success = update_user_by_admin(
        post_data.get('user_id'),
        post_data.get('name'),
        post_data.get('phone')
    )
    handler._send_response(200 if success else 400, {'success': success})

def handle_update_publisher(handler, post_data):
    """Updates publisher details from the admin panel."""
    success = update_publisher_by_admin(
        post_data.get('publisher_id'),
        post_data.get('name'),
        post_data.get('phone'),
        post_data.get('address'),
        post_data.get('description')
    )
    handler._send_response(200 if success else 400, {'success': success})

def handle_add_subscription(handler, post_data):
    """Adds a subscription for a user."""
    success = add_subscription_for_user(
        post_data.get('user_id'),
        post_data.get('category_id')
    )
    handler._send_response(200 if success else 400, {'success': success})

def handle_remove_subscription(handler, post_data):
    """Removes a subscription from a user."""
    success = remove_subscription_for_user(
        post_data.get('user_id'),
        post_data.get('category_id')
    )
    handler._send_response(200 if success else 400, {'success': success})

def handle_delete_user(handler, post_data):
    """Deletes a user."""
    success = delete_user_by_admin(post_data.get('user_id'))
    handler._send_response(200 if success else 400, {'success': success})

def handle_delete_publisher(handler, post_data):
    """Deletes a publisher and their assets."""
    files_to_delete = delete_publisher_by_admin(post_data.get('publisher_id'))
    if files_to_delete:
        if files_to_delete.get('publisher_images'):
            for img in files_to_delete['publisher_images']:
                if img:
                    try:
                        os.remove(os.path.join(UPLOADS_DIR, img))
                    except OSError as e:
                        print(f"Error deleting file {img}: {e}")
        handler._send_response(200, {'success': True, 'message': 'Publisher and assets deleted'})
    else:
        handler._send_response(400, {'success': False})

def handle_add_category(handler, post_data):
    """Adds a new category."""
    success = add_category(post_data.get('name'))
    handler._send_response(201 if success else 400, {'success': success})

def handle_delete_category(handler, post_data):
    """Deletes a category."""
    success = delete_category(post_data.get('category_id'))
    handler._send_response(200 if success else 400, {'success': success})

def handle_admin_delete_book(handler, post_data):
    """Deletes a book from the admin panel."""
    file_paths = delete_book(post_data.get('book_id'))
    if file_paths:
        handler._send_response(200, {'message': 'Book deleted'})
    else:
        handler._send_response(404, {'error': 'Book not found'})
