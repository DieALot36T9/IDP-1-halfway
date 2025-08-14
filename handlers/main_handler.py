# handlers/main_handler.py
# Contains the request handling logic for the main server.

import json
import os
from urllib.parse import urlparse, parse_qs

# Import database functions
from db.user_queries import (get_entity_by_token, verify_user_login, create_user,
                             get_user_by_id, update_user_profile)
from db.publisher_queries import verify_publisher_login, get_publisher_details, create_publisher
from db.book_queries import (get_all_books, get_books_by_publisher, get_book_pdf_path,
                             add_book, update_book, delete_book)
from db.category_queries import get_all_categories
from db.subscription_queries import check_user_subscription_for_book, add_subscription_for_user
from db.bookmark_queries import (get_user_bookmarks, add_bookmark, remove_bookmark,
                                 get_reading_history, add_to_reading_history)

# Constants
UPLOADS_DIR = os.path.join("static", "uploads")

def handle_get_request(handler):
    """Handles all GET requests for the main server."""
    parsed_path = urlparse(handler.path)
    path = parsed_path.path
    query = parse_qs(parsed_path.query)

    if path.startswith('/api/'):
        # API routes
        if path.startswith('/api/books/read/'):
            handle_read_book(handler, path)
        elif path == '/api/books':
            handle_get_all_books(handler, query)
        elif path == '/api/books/publisher':
            handle_get_publisher_books(handler)
        elif path == '/api/categories':
            handle_get_all_categories(handler)
        elif path == '/api/publisher-details':
            handle_get_publisher_details(handler, query)
        elif path == '/api/user/bookmarks':
            handle_get_user_bookmarks(handler)
        elif path == '/api/user/history':
            handle_get_user_history(handler)
        else:
            handler._send_response(404, {'error': 'API endpoint not found'})
    elif path.startswith('/static/'):
        # Serve static files
        handle_static_files(handler, path)
    else:
        # Serve the main index.html file
        serve_index(handler)

def handle_post_request(handler):
    """Handles all POST requests for the main server."""
    parsed_path = urlparse(handler.path)
    path = parsed_path.path
    content_type = handler.headers.get('Content-Type', '')

    if not path.startswith('/api/'):
        handler._send_response(404, {'error': 'Endpoint not found'})
        return

    if 'application/json' in content_type:
        handle_json_post(handler, path)
    elif 'multipart/form-data' in content_type:
        handle_multipart_post(handler, path)
    else:
        handler._send_response(415, {'error': 'Unsupported Media Type'})

# --- GET Request Handlers ---

def handle_read_book(handler, path):
    """Handles requests to read a book's PDF."""
    user, user_type = handler._get_authenticated_entity()
    if not (user and user_type == 'user'):
        handler._send_response(401, {'error': 'Authentication required to read books'})
        return

    try:
        book_id = int(path.split('/')[-1])
        if not check_user_subscription_for_book(user['user_id'], book_id):
            handler._send_response(403, {'error': 'Subscription required for this category'})
            return

        pdf_relative_path = get_book_pdf_path(book_id)
        if not pdf_relative_path:
            handler._send_response(404, {'error': 'PDF file not found for this book'})
            return

        pdf_full_path = os.path.join(UPLOADS_DIR, pdf_relative_path)
        if os.path.exists(pdf_full_path):
            handler.send_response(200)
            handler.send_header('Content-type', 'application/pdf')
            handler.end_headers()
            with open(pdf_full_path, 'rb') as f:
                handler.wfile.write(f.read())
        else:
            handler._send_response(404, {'error': 'PDF file missing from server storage'})

    except (ValueError, IndexError):
        handler._send_response(400, {'error': 'Invalid book ID format'})

def handle_get_all_books(handler, query):
    """Handles requests to get all books with optional filters."""
    search_term = query.get('search', [''])[0]
    category_id = query.get('category_id', [None])[0]
    books = get_all_books(search_term=search_term, category_id=category_id)
    handler._send_response(200, books)

def handle_get_publisher_books(handler):
    """Handles requests to get books by a specific publisher."""
    pub, pub_type = handler._get_authenticated_entity()
    if pub and pub_type == 'publisher':
        books = get_books_by_publisher(pub['publisher_id'])
        handler._send_response(200, books)
    else:
        handler._send_response(401, {'error': 'Unauthorized'})

def handle_get_all_categories(handler):
    """Handles requests to get all book categories."""
    categories = get_all_categories()
    handler._send_response(200, categories)

def handle_get_publisher_details(handler, query):
    """Handles requests to get details for a specific publisher."""
    pub_id = query.get('id', [None])[0]
    if pub_id:
        details = get_publisher_details(int(pub_id))
        handler._send_response(200, details)
    else:
        handler._send_response(400, {'error': 'Publisher ID is required'})

def handle_get_user_bookmarks(handler):
    """Handles requests to get a user's bookmarked books."""
    user, user_type = handler._get_authenticated_entity()
    if user and user_type == 'user':
        bookmarks = get_user_bookmarks(user['user_id'])
        handler._send_response(200, bookmarks)
    else:
        handler._send_response(401, {'error': 'Unauthorized'})

def handle_get_user_history(handler):
    """Handles requests to get a user's reading history."""
    user, user_type = handler._get_authenticated_entity()
    if user and user_type == 'user':
        history = get_reading_history(user['user_id'])
        handler._send_response(200, history)
    else:
        handler._send_response(401, {'error': 'Unauthorized'})

def handle_static_files(handler, path):
    """Handles serving static files."""
    filepath = path.lstrip('/')
    normalized_path = os.path.normpath(filepath).replace('\\', '/')

    if 'uploads/pdfs' in normalized_path:
        handler._send_response(403, {'error': 'Direct access to PDF files is forbidden'})
        return

    if os.path.exists(filepath) and not os.path.isdir(filepath):
        mime_type = 'text/plain'
        if filepath.endswith('.html'): mime_type = 'text/html'
        elif filepath.endswith('.css'): mime_type = 'text/css'
        elif filepath.endswith(('.js', '.mjs')): mime_type = 'application/javascript'
        elif filepath.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            ext = filepath.split('.')[-1]
            mime_type = f'image/{ext}'

        handler.send_response(200)
        handler.send_header('Content-type', mime_type)
        handler.end_headers()
        with open(filepath, 'rb') as f:
            handler.wfile.write(f.read())
    else:
        handler._send_response(404, {'error': 'File not found'})

def serve_index(handler):
    """Serves the main index.html file."""
    try:
        with open('templates/index.html', 'rb') as f:
            handler.send_response(200)
            handler.send_header('Content-type', 'text/html')
            handler.end_headers()
            handler.wfile.write(f.read())
    except FileNotFoundError:
        handler._send_response(404, {'error': 'index.html not found'})

# --- POST Request Handlers ---

def handle_json_post(handler, path):
    """Handles POST requests with JSON data."""
    content_length = int(handler.headers['Content-Length'])
    post_data = json.loads(handler.rfile.read(content_length))

    if path == '/api/login':
        handle_login(handler, post_data)
    elif path == '/api/user/register':
        handle_user_register(handler, post_data)
    elif path == '/api/user/profile':
        handle_user_profile_update(handler, post_data)
    elif path == '/api/user/subscribe':
        handle_user_subscribe(handler, post_data)
    elif path == '/api/books/delete':
        handle_book_delete(handler, post_data)
    elif path in ['/api/user/bookmarks/add', '/api/user/bookmarks/remove', '/api/user/history/add']:
        handle_bookmark_and_history(handler, path, post_data)
    else:
        handler._send_response(404, {'error': 'API endpoint not found for JSON POST'})

def handle_login(handler, post_data):
    """Handles user and publisher login."""
    email = post_data.get('email')
    password = post_data.get('password')

    user_data = verify_user_login(email, password)
    if user_data:
        handler._send_response(200, user_data)
        return

    pub_data = verify_publisher_login(email, password)
    if pub_data:
        handler._send_response(200, pub_data)
        return

    handler._send_response(401, {'error': 'Invalid credentials'})

def handle_user_register(handler, post_data):
    """Handles new user registration."""
    success = create_user(post_data.get('name'), post_data.get('email'),
                          post_data.get('phone'), post_data.get('password'))
    if success:
        handler._send_response(201, {'message': 'User created successfully'})
    else:
        handler._send_response(400, {'error': 'Failed to create user, email may already exist'})

def handle_user_profile_update(handler, post_data):
    """Handles user profile updates."""
    user, user_type = handler._get_authenticated_entity()
    if user and user_type == 'user':
        current_user_data = get_user_by_id(user['user_id'])
        new_password = post_data.get('password') or current_user_data['password']
        success = update_user_profile(user['user_id'], post_data.get('name'), new_password)
        if success:
            handler._send_response(200, {'message': 'Profile updated'})
        else:
            handler._send_response(500, {'error': 'Failed to update profile'})
    else:
        handler._send_response(401, {'error': 'Unauthorized'})

def handle_user_subscribe(handler, post_data):
    """Handles user subscription requests."""
    user, user_type = handler._get_authenticated_entity()
    if not (user and user_type == 'user'):
        handler._send_response(401, {'error': 'Unauthorized'})
        return

    category_id = post_data.get('category_id')
    if not category_id:
        handler._send_response(400, {'error': 'Category ID is required'})
        return

    success = add_subscription_for_user(user['user_id'], category_id, 30)
    if success:
        handler._send_response(200, {'message': f'Successfully subscribed to category {category_id}'})
    else:
        handler._send_response(500, {'error': 'Failed to add subscription'})

def handle_book_delete(handler, post_data):
    """Handles book deletion requests."""
    pub, pub_type = handler._get_authenticated_entity()
    if pub and pub_type == 'publisher':
        book_id = post_data.get('book_id')
        file_paths = delete_book(book_id)
        if file_paths:
            if file_paths.get('cover_path'):
                cover_file = os.path.join(UPLOADS_DIR, file_paths['cover_path'])
                if os.path.exists(cover_file): os.remove(cover_file)
            if file_paths.get('pdf_path'):
                pdf_file = os.path.join(UPLOADS_DIR, file_paths['pdf_path'])
                if os.path.exists(pdf_file): os.remove(pdf_file)
            handler._send_response(200, {'message': 'Book deleted'})
        else:
            handler._send_response(404, {'error': 'Book not found or failed to delete'})
    else:
        handler._send_response(401, {'error': 'Unauthorized'})

def handle_bookmark_and_history(handler, path, post_data):
    """Handles adding/removing bookmarks and adding to reading history."""
    user, user_type = handler._get_authenticated_entity()
    if user and user_type == 'user':
        book_id = post_data.get('book_id')
        if path == '/api/user/bookmarks/add':
            add_bookmark(user['user_id'], book_id)
        elif path == '/api/user/bookmarks/remove':
            remove_bookmark(user['user_id'], book_id)
        elif path == '/api/user/history/add':
            add_to_reading_history(user['user_id'], book_id)
        handler._send_response(200, {'message': 'Action successful'})
    else:
        handler._send_response(401, {'error': 'Unauthorized'})

def handle_multipart_post(handler, path):
    """Handles POST requests with multipart/form-data."""
    form_data, file_paths = handler._parse_multipart_form()

    if path == '/api/publisher/register':
        handle_publisher_register(handler, form_data, file_paths)
    elif path == '/api/books/add':
        handle_book_add(handler, form_data, file_paths)
    elif path == '/api/books/update':
        handle_book_update(handler, form_data, file_paths)
    else:
        handler._send_response(404, {'error': 'API endpoint not found for multipart POST'})

def handle_publisher_register(handler, form_data, file_paths):
    """Handles new publisher registration."""
    image_file = file_paths.get('image')
    image_path_for_db = image_file if image_file else None
    success = create_publisher(
        form_data.get('name'), form_data.get('email'), form_data.get('phone'),
        form_data.get('address'), form_data.get('description'),
        image_path_for_db, form_data.get('password')
    )
    if success:
        handler._send_response(201, {'message': 'Publisher created'})
    else:
        handler._send_response(400, {'error': 'Failed to create publisher'})

def handle_book_add(handler, form_data, file_paths):
    """Handles adding a new book."""
    pub, pub_type = handler._get_authenticated_entity()
    if pub and pub_type == 'publisher':
        cover_path_for_db = file_paths.get('cover')
        pdf_file = file_paths.get('pdf')

        success = add_book(
            form_data.get('name'), form_data.get('author_name'),
            form_data.get('description'), form_data.get('category_id'),
            cover_path_for_db, pdf_file, pub['publisher_id']
        )
        if success:
            handler._send_response(201, {'message': 'Book added'})
        else:
            handler._send_response(400, {'error': 'Failed to add book'})
    else:
        handler._send_response(401, {'error': 'Unauthorized'})

def handle_book_update(handler, form_data, file_paths):
    """Handles updating an existing book."""
    pub, pub_type = handler._get_authenticated_entity()
    if pub and pub_type == 'publisher':
        new_cover_file = file_paths.get('cover')
        cover_path = new_cover_file or form_data.get('existing_cover_path')

        success = update_book(
            form_data.get('book_id'), form_data.get('name'),
            form_data.get('author_name'), form_data.get('description'),
            form_data.get('category_id'), cover_path
        )
        if success:
            handler._send_response(200, {'message': 'Book updated'})
        else:
            handler._send_response(400, {'error': 'Failed to update book'})
    else:
        handler._send_response(401, {'error': 'Unauthorized'})
