# db/subscription_queries.py
# Contains all database operations related to user subscriptions.

import datetime
import cx_Oracle
from db.connection import get_db_connection, _fetch_as_dict

def get_user_active_subscriptions(user_id, conn_or_none=None):
    """
    Fetches a list of active subscriptions for a user.
    Returns a dictionary with category_id as key and expiry_date as value.
    Can use an existing database connection for efficiency.
    """
    # Use the provided connection or establish a new one
    conn = conn_or_none if conn_or_none else get_db_connection()
    if not conn:
        return {}

    subscriptions = {}
    try:
        with conn.cursor() as cursor:
            # SQL query to get active subscriptions for a user
            sql = "SELECT category_id, expiry_date FROM user_subscriptions WHERE user_id = :id AND expiry_date >= :today"
            cursor.execute(sql, id=user_id, today=datetime.date.today())
            # Populate the subscriptions dictionary
            for row in _fetch_as_dict(cursor):
                subscriptions[row['category_id']] = row['expiry_date']
        return subscriptions
    except cx_Oracle.Error as e:
        print(f"Database error in get_user_active_subscriptions: {e}")
        return {}
    finally:
        # Close the connection only if it was created within this function
        if not conn_or_none and conn:
            conn.close()

def check_user_subscription_for_book(user_id, book_id):
    """
    Checks if a user has an active subscription for a specific book's category.
    Returns True if a valid subscription exists, otherwise False.
    """
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            # SQL query to check for an active subscription for the book's category
            sql = """
                SELECT 1 FROM books b
                JOIN user_subscriptions us ON b.category_id = us.category_id
                WHERE b.book_id = :book_id
                  AND us.user_id = :user_id
                  AND us.expiry_date >= :today
            """
            cursor.execute(sql, book_id=book_id, user_id=user_id, today=datetime.date.today())
            # If a row is returned, the user is subscribed
            return cursor.fetchone() is not None
    except cx_Oracle.Error as e:
        print(f"Database error in check_user_subscription_for_book: {e}")
        return False
    finally:
        if conn:
            conn.close()

def add_subscription_for_user(user_id, category_id, duration_days=30):
    """
    Adds a new subscription or extends an existing one for a user to a specific category.
    """
    conn = get_db_connection()
    if not conn:
        return False

    # Calculate the new expiry date for the subscription
    new_expiry_date = datetime.date.today() + datetime.timedelta(days=duration_days)

    try:
        with conn.cursor() as cursor:
            # Use MERGE to either insert a new subscription or update an existing one
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
    finally:
        if conn:
            conn.close()

def remove_subscription_for_user(user_id, category_id):
    """Removes a specific subscription from a user's account."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            # SQL statement to delete a subscription
            sql = "DELETE FROM user_subscriptions WHERE user_id = :user_id AND category_id = :cat_id"
            cursor.execute(sql, user_id=user_id, cat_id=category_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in remove_subscription_for_user: {e}")
        return False
    finally:
        if conn:
            conn.close()
