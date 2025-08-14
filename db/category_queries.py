# db/category_queries.py
# Contains all database operations related to book categories.

import cx_Oracle
from db.connection import get_db_connection, _fetch_as_dict

def get_all_categories():
    """Gets all book categories from the database, ordered by name."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            # SQL query to select all categories
            sql = "SELECT category_id, category_name FROM categories ORDER BY category_name"
            cursor.execute(sql)
            return _fetch_as_dict(cursor)
    except cx_Oracle.Error as e:
        print(f"Database error in get_all_categories: {e}")
        return []
    finally:
        if conn:
            conn.close()

def add_category(category_name):
    """Adds a new book category to the database."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            # SQL statement to insert a new category
            sql = "INSERT INTO categories (category_name) VALUES (:name)"
            cursor.execute(sql, name=category_name)
            conn.commit()
            return True
    except cx_Oracle.IntegrityError:
        # Handle cases where the category already exists
        print(f"Category '{category_name}' already exists.")
        return False
    except cx_Oracle.Error as e:
        print(f"Database error in add_category: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_category(category_id):
    """
    Deletes a category if it is not currently in use by any books.
    The ON DELETE CASCADE constraint handles associated user subscriptions.
    """
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            # Check if any books are using this category before deleting
            cursor.execute("SELECT COUNT(*) FROM books WHERE category_id = :id", id=category_id)
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"Cannot delete category_id {category_id}: it is currently in use by books.")
                return False

            # If not in use, proceed with deletion
            cursor.execute("DELETE FROM categories WHERE category_id = :id", id=category_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in delete_category: {e}")
        return False
    finally:
        if conn:
            conn.close()
