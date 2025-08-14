# db/bookmark_queries.py
# Contains all database operations related to user bookmarks and reading history.

import cx_Oracle
import datetime
from db.connection import get_db_connection, _fetch_as_dict

def get_user_bookmarks(user_id):
    """Retrieves all bookmarked books for a specific user."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            # SQL query to get all books bookmarked by the user
            sql = """
                SELECT b.book_id, b.name, b.author_name, b.description, b.cover_path,
                       b.publisher_id, b.category_id, p.name as publisher_name, c.category_name
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
    finally:
        if conn:
            conn.close()

def add_bookmark(user_id, book_id):
    """Adds a book to a user's bookmarks, avoiding duplicates."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            # Use MERGE to insert a bookmark only if it doesn't already exist
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
    finally:
        if conn:
            conn.close()

def remove_bookmark(user_id, book_id):
    """Removes a book from a user's bookmarks."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            # SQL statement to delete a specific bookmark
            sql = "DELETE FROM bookmarks WHERE user_id = :user_id AND book_id = :book_id"
            cursor.execute(sql, user_id=user_id, book_id=book_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in remove_bookmark: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_reading_history(user_id, limit=10):
    """Gets the most recently read books for a user, up to a specified limit."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            # SQL query to get the user's reading history, ordered by the last read timestamp
            sql = """
                SELECT b.book_id, b.name, b.author_name, b.description, b.cover_path,
                       b.publisher_id, b.category_id, p.name as publisher_name, c.category_name,
                       rh.last_read_timestamp
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
    finally:
        if conn:
            conn.close()

def add_to_reading_history(user_id, book_id):
    """Adds or updates a book in the user's reading history."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            # Use MERGE to either update the timestamp of an existing entry or insert a new one
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
    finally:
        if conn:
            conn.close()
