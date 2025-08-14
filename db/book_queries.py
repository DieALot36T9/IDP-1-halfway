# db/book_queries.py
# Contains all database operations related to books.

import cx_Oracle
from db.connection import get_db_connection, _fetch_as_dict

def add_book(name, author, desc, category_id, cover_path, pdf_path, pub_id):
    """Adds a new book to the database, linking it to a category and publisher."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            # SQL statement to insert a new book
            sql = """
                INSERT INTO books (name, author_name, description, category_id, cover_path, pdf_path, publisher_id)
                VALUES (:name, :author, :desc_val, :cat_id, :cover, :pdf, :pub_id)
            """
            cursor.execute(sql, name=name, author=author, desc_val=desc, cat_id=category_id,
                           cover=cover_path, pdf=pdf_path, pub_id=pub_id)
            conn.commit()
            return True
    except cx_Oracle.Error as e:
        print(f"Database error in add_book: {e}")
        return False
    finally:
        if conn:
            conn.close()

def update_book(book_id, name, author, desc, category_id, cover_path):
    """Updates an existing book's details in the database."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            # SQL statement to update book information
            sql = """
                UPDATE books SET
                    name = :name,
                    author_name = :author,
                    description = :desc_val,
                    category_id = :cat_id,
                    cover_path = :cover
                WHERE book_id = :book_id
            """
            cursor.execute(sql, name=name, author=author, desc_val=desc, cat_id=category_id,
                           cover=cover_path, book_id=book_id)
            conn.commit()
            return cursor.rowcount > 0
    except cx_Oracle.Error as e:
        print(f"Database error in update_book: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_all_books(search_term="", category_id=None):
    """
    Gets all books, with optional search and category filters.
    The pdf_path is excluded for security reasons.
    """
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            # Base SQL query to select books and join with publishers and categories
            base_sql = """
                SELECT b.book_id, b.name, b.author_name, b.description, b.cover_path,
                       b.publisher_id, b.category_id, p.name as publisher_name, c.category_name
                FROM books b
                JOIN publishers p ON b.publisher_id = p.publisher_id
                LEFT JOIN categories c ON b.category_id = c.category_id
            """

            where_clauses = []
            params = {}

            # Add a search filter if a search term is provided
            if search_term:
                where_clauses.append("(UPPER(b.name) LIKE :term OR UPPER(b.author_name) LIKE :term OR UPPER(c.category_name) LIKE :term)")
                params['term'] = f"%{search_term.upper()}%"

            # Add a category filter if a category ID is provided
            try:
                if category_id and int(category_id) > 0:
                    where_clauses.append("b.category_id = :cat_id")
                    params['cat_id'] = int(category_id)
            except (ValueError, TypeError):
                pass  # Ignore invalid category IDs

            # Combine the base query with any filters
            if where_clauses:
                sql = base_sql + " WHERE " + " AND ".join(where_clauses)
            else:
                sql = base_sql

            cursor.execute(sql, params)
            return _fetch_as_dict(cursor)
    except cx_Oracle.Error as e:
        print(f"Database error in get_all_books: {e}")
        return []
    finally:
        if conn:
            conn.close()

def delete_book(book_id):
    """Deletes a book from the database and returns the paths of its associated files."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            # First, select the file paths to return them for deletion from the server
            cursor.execute("SELECT cover_path, pdf_path FROM books WHERE book_id = :id", id=book_id)
            paths = _fetch_as_dict(cursor)
            # Then, delete the book record
            cursor.execute("DELETE FROM books WHERE book_id = :id", id=book_id)
            conn.commit()
            return paths[0] if paths else None
    except cx_Oracle.Error as e:
        print(f"Database error in delete_book: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_books_by_publisher(publisher_id):
    """Gets all books published by a specific publisher."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            # SQL query to get all books for a given publisher
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
    finally:
        if conn:
            conn.close()

def get_book_pdf_path(book_id):
    """
    Securely retrieves just the PDF path for a given book.
    This is intended for use by the protected download endpoint.
    """
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            # SQL query to get only the PDF path
            cursor.execute("SELECT pdf_path FROM books WHERE book_id = :id", id=book_id)
            result = cursor.fetchone()
            return result[0] if result else None
    except cx_Oracle.Error as e:
        print(f"Database error in get_book_pdf_path: {e}")
        return None
    finally:
        if conn:
            conn.close()
