# db/publisher_queries.py
# Contains all database operations related to publishers.

import cx_Oracle
from db.connection import get_db_connection, _fetch_as_dict
from db.user_queries import set_session_token

def create_publisher(name, email, phone, address, description, image_path, password):
    """Inserts a new publisher into the 'publishers' table."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            # SQL statement to insert a new publisher
            sql = """
                INSERT INTO publishers (name, email, phone, address, description, image_path, password)
                VALUES (:name, :email, :phone, :address, :description_val, :img, :pass_val)
            """
            cursor.execute(sql, name=name, email=email, phone=phone, address=address,
                           description_val=description, img=image_path, pass_val=password)
            conn.commit()
            return True
    except cx_Oracle.Error as e:
        print(f"Database error in create_publisher: {e}")
        return False
    finally:
        if conn:
            conn.close()

def verify_publisher_login(email, password):
    """
    Verifies publisher credentials and returns publisher data with a new session token.
    """
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            # SQL query to find a publisher by email and password
            sql = "SELECT publisher_id, name, email FROM publishers WHERE email = :email AND password = :password"
            cursor.execute(sql, email=email, password=password)
            pub_data = _fetch_as_dict(cursor)

            if pub_data:
                publisher = pub_data[0]
                # Generate a session token upon successful login
                token = set_session_token(publisher['publisher_id'], 'publisher')
                if token:
                    publisher['session_token'] = token
                    publisher['type'] = 'publisher'
                    return publisher
            return None
    except cx_Oracle.Error as e:
        print(f"Database error in verify_publisher_login: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_publisher_details(publisher_id):
    """Fetches public details for a single publisher by their ID."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            # SQL query to get public-facing publisher details
            sql = "SELECT name, email, phone, address, description, image_path FROM publishers WHERE publisher_id = :id"
            cursor.execute(sql, id=publisher_id)
            data = _fetch_as_dict(cursor)
            return data[0] if data else None
    except cx_Oracle.Error as e:
        print(f"Database error in get_publisher_details: {e}")
        return None
    finally:
        if conn:
            conn.close()
