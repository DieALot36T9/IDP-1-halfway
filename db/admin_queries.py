# db/admin_queries.py
# Contains all database operations restricted to admin users.

import cx_Oracle
import datetime
from db.connection import get_db_connection, _fetch_as_dict
from db.user_queries import set_session_token

def verify_admin_login(email, password):
    """Verifies admin credentials and returns admin data with a new session token."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            # SQL query to find an admin by email and password
            sql = "SELECT admin_id, name, email FROM admins WHERE email = :email AND password = :password"
            cursor.execute(sql, email=email, password=password)
            admin_data = _fetch_as_dict(cursor)

            if admin_data:
                admin = admin_data[0]
                # Generate a session token upon successful login
                token = set_session_token(admin['admin_id'], 'admin')
                if token:
                    admin['session_token'] = token
                    admin['type'] = 'admin'
                    return admin
            return None
    except cx_Oracle.Error as e:
        print(f"Database error in verify_admin_login: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_users_for_admin():
    """
    Gets all users and a list of their active subscriptions for the admin panel.
    """
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            # SQL query to get all users and their active subscriptions
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
    finally:
        if conn:
            conn.close()

def delete_user_by_admin(user_id):
    """
    Deletes a user and their associated data (subscriptions, bookmarks, history)
    from the admin panel.
    """
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            # Manually delete related data before deleting the user
            cursor.execute("DELETE FROM bookmarks WHERE user_id = :id", id=user_id)
            cursor.execute("DELETE FROM reading_history WHERE user_id = :id", id=user_id)
            # The 'ON DELETE CASCADE' constraint will handle subscriptions
            cursor.execute("DELETE FROM users WHERE user_id = :id", id=user_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in delete_user_by_admin: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_all_publishers_for_admin():
    """Gets all publishers for the admin panel."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            # SQL query to get all publishers
            sql = "SELECT publisher_id, name, email, phone, address, image_path FROM publishers ORDER BY publisher_id"
            cursor.execute(sql)
            return _fetch_as_dict(cursor)
    except cx_Oracle.Error as e:
        print(f"Database error in get_all_publishers_for_admin: {e}")
        return []
    finally:
        if conn:
            conn.close()

def delete_publisher_by_admin(publisher_id):
    """
    Deletes a publisher and all of their associated books and files.
    Returns a dictionary of file paths to be deleted from the server.
    """
    conn = get_db_connection()
    if not conn:
        return None

    files_to_delete = {'covers': [], 'pdfs': [], 'publisher_images': []}

    try:
        with conn.cursor() as cursor:
            # Get the publisher's image path
            cursor.execute("SELECT image_path FROM publishers WHERE publisher_id = :id", id=publisher_id)
            pub_image = cursor.fetchone()
            if pub_image and pub_image[0]:
                files_to_delete['publisher_images'].append(pub_image[0])

            # Get the paths of all book covers and PDFs associated with the publisher
            cursor.execute("SELECT cover_path, pdf_path FROM books WHERE publisher_id = :id", id=publisher_id)
            for row in cursor.fetchall():
                if row[0]: files_to_delete['covers'].append(row[0])
                if row[1]: files_to_delete['pdfs'].append(row[1])

            # Delete all books by the publisher, then delete the publisher
            cursor.execute("DELETE FROM books WHERE publisher_id = :id", id=publisher_id)
            cursor.execute("DELETE FROM publishers WHERE publisher_id = :id", id=publisher_id)

            conn.commit()
            return files_to_delete
    except cx_Oracle.Error as e:
        print(f"Database error in delete_publisher_by_admin: {e}")
        conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def get_user_by_id_for_admin(user_id):
    """Fetches a single user's details for editing in the admin panel."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            # SQL query to get user details, excluding the password
            sql = "SELECT user_id, name, email, phone FROM users WHERE user_id = :id"
            cursor.execute(sql, id=user_id)
            users = _fetch_as_dict(cursor)
            return users[0] if users else None
    except cx_Oracle.Error as e:
        print(f"Database error in get_user_by_id_for_admin: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_user_by_admin(user_id, name, phone):
    """Updates a user's details from the admin panel."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            # SQL statement to update user's name and phone
            sql = "UPDATE users SET name = :name, phone = :phone WHERE user_id = :id"
            cursor.execute(sql, name=name, phone=phone, id=user_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in update_user_by_admin: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_publisher_by_id_for_admin(publisher_id):
    """Fetches a single publisher's details for editing in the admin panel."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            # SQL query to get publisher details
            sql = "SELECT publisher_id, name, email, phone, address, description FROM publishers WHERE publisher_id = :id"
            cursor.execute(sql, id=publisher_id)
            publishers = _fetch_as_dict(cursor)
            return publishers[0] if publishers else None
    except cx_Oracle.Error as e:
        print(f"Database error in get_publisher_by_id_for_admin: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_publisher_by_admin(pub_id, name, phone, address, description):
    """Updates a publisher's details from the admin panel."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            # SQL statement to update publisher details
            sql = """UPDATE publishers SET name = :name, phone = :phone, address = :address, description = :desc
                     WHERE publisher_id = :id"""
            cursor.execute(sql, name=name, phone=phone, address=address, desc=description, id=pub_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in update_publisher_by_admin: {e}")
        return False
    finally:
        if conn:
            conn.close()
