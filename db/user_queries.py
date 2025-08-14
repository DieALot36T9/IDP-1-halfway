# db/user_queries.py
# Contains all database operations related to users and sessions.

import datetime
import random
import string
import cx_Oracle
from db.connection import get_db_connection, _fetch_as_dict
from db.subscription_queries import get_user_active_subscriptions

def _generate_session_token(length=40):
    """Generates a random alphanumeric string to use as a session token."""
    # Define the characters to choose from for the token
    alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    # Randomly select characters to form the token
    return ''.join(random.choices(alphabet, k=length))

def set_session_token(entity_id, entity_type, expiry_minutes=60):
    """
    Sets a new session token for a given entity (user, publisher, or admin)
    and stores it in the database.
    """
    # Establish a database connection
    conn = get_db_connection()
    if not conn:
        return None

    # Determine the correct table and column based on the entity type
    if entity_type == 'user':
        table, id_column = 'users', 'user_id'
    elif entity_type == 'publisher':
        table, id_column = 'publishers', 'publisher_id'
    elif entity_type == 'admin':
        table, id_column = 'admins', 'admin_id'
    else:
        return None  # Invalid entity type

    # Generate a new token and calculate its expiry time
    token = _generate_session_token()
    expiry_time = datetime.datetime.now() + datetime.timedelta(minutes=expiry_minutes)

    try:
        with conn.cursor() as cursor:
            # SQL statement to update the session token and expiry
            sql = f"UPDATE {table} SET session_token = :token, token_expiry = :expiry WHERE {id_column} = :id"
            cursor.execute(sql, token=token, expiry=expiry_time, id=entity_id)
            conn.commit()
            return token
    except cx_Oracle.Error as e:
        # Log any database errors that occur
        print(f"Database error in set_session_token for type {entity_type}: {e}")
        return None
    finally:
        # Ensure the database connection is closed
        if conn:
            conn.close()

def get_entity_by_token(token, entity_type):
    """
    Retrieves an entity's data from the database using their session token.
    The token is only valid if it has not expired.
    """
    conn = get_db_connection()
    if not conn:
        return None

    # Determine which table to query based on the entity type
    if entity_type == 'user':
        table = 'users'
    elif entity_type == 'publisher':
        table = 'publishers'
    elif entity_type == 'admin':
        table = 'admins'
    else:
        return None  # Invalid entity type

    try:
        with conn.cursor() as cursor:
            # SQL query to find the entity with a valid session token
            sql = f"SELECT * FROM {table} WHERE session_token = :token AND token_expiry > :current_time"
            cursor.execute(sql, token=token, current_time=datetime.datetime.now())
            entity_data = _fetch_as_dict(cursor)
            # Return the first result if found, otherwise None
            return entity_data[0] if entity_data else None
    except cx_Oracle.Error as e:
        print(f"Database error in get_entity_by_token for type {entity_type}: {e}")
        return None
    finally:
        if conn:
            conn.close()

def create_user(name, email, phone, password):
    """Inserts a new user record into the 'users' table."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            # SQL statement to insert a new user
            sql = "INSERT INTO users (name, email, phone, password) VALUES (:name, :email, :phone, :password)"
            cursor.execute(sql, name=name, email=email, phone=phone, password=password)
            conn.commit()
            return True
    except cx_Oracle.Error as e:
        print(f"Database error in create_user: {e}")
        return False
    finally:
        if conn:
            conn.close()

def verify_user_login(email, password):
    """
    Verifies user credentials, fetches their active subscriptions, and returns user data
    along with a new session token.
    """
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            # SQL query to find a user by email and password
            sql = "SELECT user_id, name, email FROM users WHERE email = :email AND password = :password"
            cursor.execute(sql, email=email, password=password)
            user_data = _fetch_as_dict(cursor)

            if user_data:
                user = user_data[0]
                # Generate a new session token for the user
                token = set_session_token(user['user_id'], 'user')
                if token:
                    user['session_token'] = token
                    user['type'] = 'user'
                    # Fetch and attach the user's active subscriptions
                    user['subscriptions'] = get_user_active_subscriptions(user['user_id'], conn)
                    return user
            return None
    except cx_Oracle.Error as e:
        print(f"Database error in verify_user_login: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_user_profile(user_id, name, password):
    """Updates a user's name and password in the database."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            # SQL statement to update user details
            sql = "UPDATE users SET name = :name, password = :password WHERE user_id = :user_id"
            cursor.execute(sql, name=name, password=password, user_id=user_id)
            conn.commit()
            # Return True if the update was successful
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in update_user_profile: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_user_by_id(user_id):
    """Fetches a single user's details, including their password, by user ID."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            # SQL query to get a user by their ID
            sql = "SELECT user_id, name, email, phone, password FROM users WHERE user_id = :id"
            cursor.execute(sql, id=user_id)
            users = _fetch_as_dict(cursor)
            # Return the first result if found
            return users[0] if users else None
    finally:
        if conn:
            conn.close()
