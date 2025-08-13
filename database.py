import cx_Oracle
import datetime
import random
import string
from contextlib import contextmanager

#
DB_USER = "EBOOK_SITE"
DB_PASSWORD =  "1124"
#DSN for Oracle XE: "localhost:1521/XEPDB1"
DB_DSN = "localhost:1521/XEPDB1"

@contextmanager
def get_db_connection():
    """
    A context manager for handling database connections.
    This ensures the connection is always closed, even if errors occur.
    """
    connection = None
    try:
        connection = cx_Oracle.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN, encoding="UTF-8")
        yield connection
    except cx_Oracle.Error as e:
        print(f"Database connection error: {e}")
        # In a real app, you'd want more robust error handling or logging
        raise
    finally:
        if connection:
            connection.close()

def _generate_session_token(length=40):
    
    #random string of 40 letters as a session token.
    
    alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return ''.join(random.choices(alphabet, k=length))

def _fetch_as_dict(cursor):
    """
    Fetches query results from the cursor and returns them as a list of dictionaries.
    This makes it easier to convert the data to JSON later.
    """
    columns = [col[0].lower() for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

# --- HELPER & SESSION FUNCTIONS ---

def set_session_token(entity_id, entity_type, expiry_minutes=60):
    if entity_type not in ['user', 'publisher', 'admin']:
        return None  # Invalid type

    table_map = {'user': 'users', 'publisher': 'publishers', 'admin': 'admins'}
    id_column_map = {'user': 'user_id', 'publisher': 'publisher_id', 'admin': 'admin_id'}
    table = table_map[entity_type]
    id_column = id_column_map[entity_type]

    token = _generate_session_token()
    expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=expiry_minutes)

    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = f"UPDATE {table} SET session_token = :token, token_expiry = :expiry WHERE {id_column} = :id"
            cursor.execute(sql, token=token, expiry=expiry_time, id=entity_id)
            conn.commit()
            return token
    except cx_Oracle.Error as e:
        print(f"Database error in set_session_token for type {entity_type}: {e}")
        return None

def get_entity_by_token(token, entity_type):
    if entity_type not in ['user', 'publisher', 'admin']:
        return None # Invalid type
    
    table = {'user': 'users', 'publisher': 'publishers', 'admin': 'admins'}[entity_type]

    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = f"SELECT * FROM {table} WHERE session_token = :token AND token_expiry > :current_time"
            cursor.execute(sql, token=token, current_time=datetime.datetime.now())
            entity_data = _fetch_as_dict(cursor)
            return entity_data[0] if entity_data else None
    except cx_Oracle.Error as e:
        print(f"Database error in get_entity_by_token for type {entity_type}: {e}")
        return None


# --- USER MANAGEMENT FUNCTIONS ---

def create_user(name, email, phone, password):
    """Inserts a new user into the 'users' table."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "INSERT INTO users (name, email, phone, password) VALUES (:name, :email, :phone, :password)"
            cursor.execute(sql, name=name, email=email, phone=phone, password=password)
            conn.commit()
            return True
    except cx_Oracle.Error as e:
        print(f"Database error in create_user: {e}")
        return False

def verify_user_login(email, password):
    """
    Verifies user, gets active subscriptions, and returns user data.
    """
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "SELECT user_id, name, email FROM users WHERE email = :email AND password = :password"
            cursor.execute(sql, email=email, password=password)
            user_data = _fetch_as_dict(cursor)

            if not user_data:
                return None

            user = user_data[0]
            token = set_session_token(user['user_id'], 'user')
            if token:
                user['session_token'] = token
                user['type'] = 'user'
                user['subscriptions'] = get_user_active_subscriptions(user['user_id'], conn)
                return user
            return None
    except cx_Oracle.Error as e:
        print(f"Database error in verify_user_login: {e}")
        return None

def update_user_profile(user_id, name, password):
    """Updates a user's name and password."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "UPDATE users SET name = :name, password = :password WHERE user_id = :user_id"
            cursor.execute(sql, name=name, password=password, user_id=user_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in update_user_profile: {e}")
        return False

# --- PUBLISHER MANAGEMENT FUNCTIONS ---

def create_publisher(name, email, phone, address, description, image_path, password):
    """Inserts a new publisher into the 'publishers' table."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = """
                INSERT INTO publishers (name, email, phone, address, description, image_path, password)
                VALUES (:name, :email, :phone, :address, :desc_val, :img, :pass_val)
            """
            cursor.execute(sql, name=name, email=email, phone=phone, address=address, description_val=description, img=image_path, pass_val=password)
            conn.commit()
            return True
    except cx_Oracle.Error as e:
        print(f"Database error in create_publisher: {e}")
        return False

def verify_publisher_login(email, password):
    """Verifies publisher credentials and returns publisher data with a new session token."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "SELECT publisher_id, name, email FROM publishers WHERE email = :email AND password = :password"
            cursor.execute(sql, email=email, password=password)
            pub_data = _fetch_as_dict(cursor)
            if pub_data:
                publisher = pub_data[0]
                token = set_session_token(publisher['publisher_id'], 'publisher')
                if token:
                    publisher['session_token'] = token
                    publisher['type'] = 'publisher'
                    return publisher
            return None
    except cx_Oracle.Error as e:
        print(f"Database error in verify_publisher_login: {e}")
        return None

def get_publisher_details(publisher_id):
    """Fetches public details for a single publisher."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "SELECT name, email, phone, address, description, image_path FROM publishers WHERE publisher_id = :id"
            cursor.execute(sql, id=publisher_id)
            data = _fetch_as_dict(cursor)
            return data[0] if data else None
    except cx_Oracle.Error as e:
        print(f"Database error in get_publisher_details: {e}")
        return None

# --- BOOK MANAGEMENT FUNCTIONS ---

def add_book(name, author, desc, category_id, cover_path, pdf_path, pub_id):
    """Adds a new book to the database using category_id."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = """
                INSERT INTO books (name, author_name, description, category_id, cover_path, pdf_path, publisher_id)
                VALUES (:name, :author, :desc_val, :cat_id, :cover, :pdf, :pub_id)
            """
            cursor.execute(sql, name=name, author=author, desc_val=desc, cat_id=category_id, cover=cover_path, pdf=pdf_path, pub_id=pub_id)
            conn.commit()
            return True
    except cx_Oracle.Error as e:
        print(f"Database error in add_book: {e}")
        return False

def update_book(book_id, name, author, desc, category_id, cover_path):
    """Updates an existing book's details using category_id."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = """
                UPDATE books SET
                    name = :name,
                    author_name = :author,
                    description = :desc_val,
                    category_id = :cat_id,
                    cover_path = :cover
                WHERE book_id = :book_id
            """
            cursor.execute(sql, name=name, author=author, desc_val=desc, cat_id=category_id, cover=cover_path, book_id=book_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in update_book: {e}")
        return False

def get_all_books(search_term="", category_id=None):
    """
    Gets all books, with optional search and category filters.
    Does NOT return the pdf_path for security.
    """
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            base_sql = """
                SELECT b.book_id, b.name, b.author_name, b.description, b.cover_path, b.publisher_id, b.category_id,
                       p.name as publisher_name, c.category_name
                FROM books b
                JOIN publishers p ON b.publisher_id = p.publisher_id
                LEFT JOIN categories c ON b.category_id = c.category_id
            """
            
            where_clauses = []
            params = {}

            if search_term:
                where_clauses.append("(UPPER(b.name) LIKE :term OR UPPER(b.author_name) LIKE :term OR UPPER(c.category_name) LIKE :term)")
                params['term'] = f"%{search_term.upper()}%"
            
            try:
                if category_id and int(category_id) > 0:
                    where_clauses.append("b.category_id = :cat_id")
                    params['cat_id'] = int(category_id)
            except (ValueError, TypeError):
                pass

            if where_clauses:
                sql = base_sql + " WHERE " + " AND ".join(where_clauses)
            else:
                sql = base_sql
            
            cursor.execute(sql, params)
            return _fetch_as_dict(cursor)
    except cx_Oracle.Error as e:
        print(f"Database error in get_all_books: {e}")
        return []

def delete_book(book_id):
    """Deletes a book from the database."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT cover_path, pdf_path FROM books WHERE book_id = :id", id=book_id)
            paths = _fetch_as_dict(cursor)
            if not paths:
                return None

            cursor.execute("DELETE FROM books WHERE book_id = :id", id=book_id)
            conn.commit()
            return paths[0]
    except cx_Oracle.Error as e:
        print(f"Database error in delete_book: {e}")
        return None

def get_books_by_publisher(publisher_id):
    """Gets all books published by a specific publisher."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = """
                SELECT b.*, p.name as publisher_name, c.category_name
                FROM books b
                JOIN publishers p ON b.publisher_id = p.publisher_id
                LEFT JOIN categories c ON b.category_id = c.category_id
                WHERE b.publisher_id = :id ORDER BY b.name
            """
            cursor.execute(sql, id=publisher_id)
            return _fetch_as_dict(cursor)
    except cx_Oracle.Error as e:
        print(f"Database error in get_books_by_publisher: {e}")
        return []
        
def get_book_pdf_path(book_id):
    """
    Securely retrieves just the PDF path for a given book.
    To be used by the protected download endpoint.
    """
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT pdf_path FROM books WHERE book_id = :id", id=book_id)
            result = cursor.fetchone()
            return result[0] if result else None
    except cx_Oracle.Error as e:
        print(f"Database error in get_book_pdf_path: {e}")
        return None


# --- BOOKMARK & HISTORY FUNCTIONS ---

def get_user_bookmarks(user_id):
    """Retrieves all bookmarked books for a specific user."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = """
                SELECT b.book_id, b.name, b.author_name, b.description, b.cover_path, b.publisher_id, b.category_id,
                       p.name as publisher_name, c.category_name
                FROM books b
                JOIN bookmarks bm ON b.book_id = bm.book_id
                JOIN publishers p ON b.publisher_id = p.publisher_id
                LEFT JOIN categories c ON b.category_id = c.category_id
                WHERE bm.user_id = :user_id
            """
            cursor.execute(sql, user_id=user_id)
            return _fetch_as_dict(cursor)
    except cx_Oracle.Error as e:
        print(f"Database error in get_user_bookmarks: {e}")
        return []

def add_bookmark(user_id, book_id):
    """Adds a book to a user's bookmarks."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = """
                MERGE INTO bookmarks b
                USING (SELECT :user_id AS user_id, :book_id AS book_id FROM dual) d
                ON (b.user_id = d.user_id AND b.book_id = d.book_id)
                WHEN NOT MATCHED THEN INSERT (user_id, book_id) VALUES (d.user_id, d.book_id)
            """
            cursor.execute(sql, user_id=user_id, book_id=book_id)
            conn.commit()
            return True
    except cx_Oracle.Error as e:
        print(f"Database error in add_bookmark: {e}")
        return False

def remove_bookmark(user_id, book_id):
    """Removes a book from a user's bookmarks."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "DELETE FROM bookmarks WHERE user_id = :user_id AND book_id = :book_id"
            cursor.execute(sql, user_id=user_id, book_id=book_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in remove_bookmark: {e}")
        return False

def get_reading_history(user_id, limit=10):
    """Gets the most recently read books for a user."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = """
                SELECT b.book_id, b.name, b.author_name, b.description, b.cover_path, b.publisher_id, b.category_id,
                       p.name as publisher_name, c.category_name, rh.last_read_timestamp
                FROM books b
                JOIN reading_history rh ON b.book_id = rh.book_id
                JOIN publishers p ON b.publisher_id = p.publisher_id
                LEFT JOIN categories c ON b.category_id = c.category_id
                WHERE rh.user_id = :user_id
                ORDER BY rh.last_read_timestamp DESC
                FETCH FIRST :limit ROWS ONLY
            """
            cursor.execute(sql, user_id=user_id, limit=limit)
            return _fetch_as_dict(cursor)
    except cx_Oracle.Error as e:
        print(f"Database error in get_reading_history: {e}")
        return []

def add_to_reading_history(user_id, book_id):
    """Adds or updates a book in the user's reading history."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = """
                MERGE INTO reading_history rh
                USING (SELECT :user_id AS user_id, :book_id AS book_id FROM dual) d
                ON (rh.user_id = d.user_id AND rh.book_id = d.book_id)
                WHEN MATCHED THEN UPDATE SET last_read_timestamp = :current_time
                WHEN NOT MATCHED THEN INSERT (user_id, book_id, last_read_timestamp)
                                     VALUES (d.user_id, d.book_id, :current_time)
            """
            cursor.execute(sql, user_id=user_id, book_id=book_id, current_time=datetime.datetime.now())
            conn.commit()
            return True
    except cx_Oracle.Error as e:
        print(f"Database error in add_to_reading_history: {e}")
        return False


# --- SUBSCRIPTION FUNCTIONS ---

def get_user_active_subscriptions(user_id, conn_or_none=None):
    """
    Fetches a list of active subscriptions for a user.
    Returns a dictionary with category_id as key and expiry_date as value.
    Can use an existing connection to be more efficient.
    """
    if conn_or_none:
        # Use the existing connection if provided
        try:
            with conn_or_none.cursor() as cursor:
                sql = "SELECT category_id, expiry_date FROM user_subscriptions WHERE user_id = :id AND expiry_date >= :today"
                cursor.execute(sql, id=user_id, today=datetime.date.today())
                return {row['category_id']: row['expiry_date'] for row in _fetch_as_dict(cursor)}
        except cx_Oracle.Error as e:
            print(f"Database error in get_user_active_subscriptions: {e}")
            return {}
    else:
        # Open a new connection if one isn't provided
        try:
            with get_db_connection() as conn, conn.cursor() as cursor:
                sql = "SELECT category_id, expiry_date FROM user_subscriptions WHERE user_id = :id AND expiry_date >= :today"
                cursor.execute(sql, id=user_id, today=datetime.date.today())
                return {row['category_id']: row['expiry_date'] for row in _fetch_as_dict(cursor)}
        except cx_Oracle.Error as e:
            print(f"Database error in get_user_active_subscriptions: {e}")
            return {}

def check_user_subscription_for_book(user_id, book_id):
    """Checks if a user has an active subscription for a specific book's category."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = """
                SELECT 1 FROM books b
                JOIN user_subscriptions us ON b.category_id = us.category_id
                WHERE b.book_id = :book_id
                  AND us.user_id = :user_id
                  AND us.expiry_date >= :today
            """
            cursor.execute(sql, book_id=book_id, user_id=user_id, today=datetime.date.today())
            return cursor.fetchone() is not None
    except cx_Oracle.Error as e:
        print(f"Database error in check_user_subscription_for_book: {e}")
        return False

def add_subscription_for_user(user_id, category_id, duration_days=30):
    """Adds or extends a subscription for a user to a specific category."""
    new_expiry_date = datetime.date.today() + datetime.timedelta(days=duration_days)
    
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = """
                MERGE INTO user_subscriptions us
                USING (
                    SELECT :user_id AS user_id, :cat_id AS category_id, :expiry AS expiry_date FROM dual
                ) d ON (us.user_id = d.user_id AND us.category_id = d.category_id)
                WHEN MATCHED THEN
                    UPDATE SET us.expiry_date = d.expiry_date
                WHEN NOT MATCHED THEN
                    INSERT (user_id, category_id, expiry_date)
                    VALUES (d.user_id, d.category_id, d.expiry_date)
            """
            cursor.execute(sql, user_id=user_id, cat_id=category_id, expiry=new_expiry_date)
            conn.commit()
            return True
    except cx_Oracle.Error as e:
        print(f"Database error in add_subscription_for_user: {e}")
        return False

def remove_subscription_for_user(user_id, category_id):
    """Removes a specific subscription from a user."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "DELETE FROM user_subscriptions WHERE user_id = :user_id AND category_id = :cat_id"
            cursor.execute(sql, user_id=user_id, cat_id=category_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in remove_subscription_for_user: {e}")
        return False


# --- ADMIN MANAGEMENT ---

def verify_admin_login(email, password):
    """Verifies admin credentials and returns admin data with a new session token."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "SELECT admin_id, name, email FROM admins WHERE email = :email AND password = :password"
            cursor.execute(sql, email=email, password=password)
            admin_data = _fetch_as_dict(cursor)
            if admin_data:
                admin = admin_data[0]
                token = set_session_token(admin['admin_id'], 'admin')
                if token:
                    admin['session_token'] = token
                    admin['type'] = 'admin'
                    return admin
            return None
    except cx_Oracle.Error as e:
        print(f"Database error in verify_admin_login: {e}")
        return None

# --- ADMIN-LEVEL CRUD OPERATIONS ---

def get_all_users_for_admin():
    """
    Gets all users and a list of their active subscriptions.
    """
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = """
                SELECT
                    u.user_id,
                    u.name,
                    u.email,
                    u.phone,
                    (
                        SELECT LISTAGG(c.category_name, ', ') WITHIN GROUP (ORDER BY c.category_name)
                        FROM user_subscriptions us
                        JOIN categories c ON us.category_id = c.category_id
                        WHERE us.user_id = u.user_id AND us.expiry_date >= :today
                    ) as active_subscriptions
                FROM users u
                ORDER BY u.user_id
            """
            cursor.execute(sql, today=datetime.date.today())
            return _fetch_as_dict(cursor)
    except cx_Oracle.Error as e:
        print(f"Database error in get_all_users_for_admin: {e}")
        return []

def delete_user_by_admin(user_id):
    """
    Deletes a user, which cascades to delete their subscriptions, bookmarks, and history.
    """
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            # The ON DELETE CASCADE constraint on the tables will handle deletion
            # of related records in bookmarks, reading_history, and user_subscriptions.
            cursor.execute("DELETE FROM users WHERE user_id = :id", id=user_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in delete_user_by_admin: {e}")
        return False

def get_all_publishers_for_admin():
    """Gets all publishers for the admin panel."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "SELECT publisher_id, name, email, phone, address, image_path FROM publishers ORDER BY publisher_id"
            cursor.execute(sql)
            return _fetch_as_dict(cursor)
    except cx_Oracle.Error as e:
        print(f"Database error in get_all_publishers_for_admin: {e}")
        return []

def delete_publisher_by_admin(publisher_id):
    """Deletes a publisher and all of their associated books and files."""
    files_to_delete = {'covers': [], 'pdfs': [], 'publisher_images': []}
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            # Get paths of all files associated with the publisher before deleting
            cursor.execute("SELECT image_path FROM publishers WHERE publisher_id = :id", id=publisher_id)
            pub_image = cursor.fetchone()
            if pub_image and pub_image[0]:
                files_to_delete['publisher_images'].append(pub_image[0])

            cursor.execute("SELECT cover_path, pdf_path FROM books WHERE publisher_id = :id", id=publisher_id)
            for row in cursor.fetchall():
                if row[0]: files_to_delete['covers'].append(row[0])
                if row[1]: files_to_delete['pdfs'].append(row[1])
            
            # ON DELETE CASCADE on the books table will remove associated bookmarks and history
            cursor.execute("DELETE FROM publishers WHERE publisher_id = :id", id=publisher_id)
            conn.commit()
            return files_to_delete
    except cx_Oracle.Error as e:
        print(f"Database error in delete_publisher_by_admin: {e}")
        return None

# --- NEW: Functions for admin to edit users and publishers ---
def get_user_by_id_for_admin(user_id):
    """Fetches a single user's details for editing in the admin panel."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "SELECT user_id, name, email, phone FROM users WHERE user_id = :id"
            cursor.execute(sql, id=user_id)
            users = _fetch_as_dict(cursor)
            return users[0] if users else None
    except cx_Oracle.Error as e:
        print(f"Database error in get_user_by_id_for_admin: {e}")
        return None

def update_user_by_admin(user_id, name, phone):
    """Updates a user's details from the admin panel."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "UPDATE users SET name = :name, phone = :phone WHERE user_id = :id"
            cursor.execute(sql, name=name, phone=phone, id=user_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in update_user_by_admin: {e}")
        return False

def get_publisher_by_id_for_admin(publisher_id):
    """Fetches a single publisher's details for editing in the admin panel."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "SELECT publisher_id, name, email, phone, address, description FROM publishers WHERE publisher_id = :id"
            cursor.execute(sql, id=publisher_id)
            publishers = _fetch_as_dict(cursor)
            return publishers[0] if publishers else None
    except cx_Oracle.Error as e:
        print(f"Database error in get_publisher_by_id_for_admin: {e}")
        return None

def update_publisher_by_admin(pub_id, name, phone, address, description):
    """Updates a publisher's details from the admin panel."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = """UPDATE publishers SET name = :name, phone = :phone, address = :address, description = :desc
                     WHERE publisher_id = :id"""
            cursor.execute(sql, name=name, phone=phone, address=address, desc=description, id=pub_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in update_publisher_by_admin: {e}")
        return False

# --- CATEGORY MANAGEMENT ---

def get_all_categories():
    """Gets all book categories from the database."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "SELECT category_id, category_name FROM categories ORDER BY category_name"
            cursor.execute(sql)
            return _fetch_as_dict(cursor)
    except cx_Oracle.Error as e:
        print(f"Database error in get_all_categories: {e}")
        return []

def add_category(category_name):
    """Adds a new book category."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "INSERT INTO categories (category_name) VALUES (:name)"
            cursor.execute(sql, name=category_name)
            conn.commit()
            return True
    except cx_Oracle.IntegrityError:
        print(f"Category '{category_name}' already exists.")
        return False
    except cx_Oracle.Error as e:
        print(f"Database error in add_category: {e}")
        return False

def delete_category(category_id):
    """
    Deletes a category. This will fail if the category is in use by any books,
    which is a safe default.
    """
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            # Check if any books are using this category
            cursor.execute("SELECT COUNT(*) FROM books WHERE category_id = :id", id=category_id)
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"Cannot delete category_id {category_id}: it is currently in use by {count} books.")
                return False

            # If not in use, proceed with deletion
            cursor.execute("DELETE FROM categories WHERE category_id = :id", id=category_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in delete_category: {e}")
        return False


# --- NEW: Function needed by server.py for the profile page ---
def get_user_by_id(user_id):
    """Fetches a single user's details, including their password."""
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            sql = "SELECT user_id, name, email, phone, password FROM users WHERE user_id = :id"
            cursor.execute(sql, id=user_id)
            users = _fetch_as_dict(cursor)
            return users[0] if users else None
    except cx_Oracle.Error as e:
        print(f"Database error in get_user_by_id: {e}")
        return None