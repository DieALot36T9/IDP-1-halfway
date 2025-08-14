import cx_Oracle

# Database connection parameters
DB_USER = "EBOOK_SITE"
DB_PASSWORD = "1124"
DB_DSN = "localhost:1521/XEPDB1"

def get_db_connection():
    """Establishes and returns a connection to the Oracle database."""
    try:
        # Create a connection using the specified credentials and DSN
        connection = cx_Oracle.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN,
            encoding="UTF-8"
        )
        return connection
    except cx_Oracle.Error as e:
        # Print an error message if the connection fails
        print(f"Database connection error: {e}")
        return None

def _fetch_as_dict(cursor):
    """
    Fetches query results from the cursor and returns them as a list of dictionaries.
    This helper function makes it easier to convert database rows to a structured format like JSON.
    """
    # Get column names from the cursor description
    columns = [col[0].lower() for col in cursor.description]
    # Create a dictionary for each row, mapping column names to row values
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
