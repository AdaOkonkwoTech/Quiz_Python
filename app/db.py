import os
import psycopg

# Flag to determine storage method
USE_JSON_FALLBACK = False


def test_database_connection():
    """Test if PostgreSQL is available, set fallback flag if not"""
    global USE_JSON_FALLBACK
    try:
        conn = psycopg.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            dbname=os.getenv("DB_NAME", "postgres"),
            port=int(os.getenv("DB_PORT", 5432)),
            timeout=5
        )
        conn.close()
        USE_JSON_FALLBACK = False
        print("✓ PostgreSQL connection successful")
        return True
    except Exception as e:
        USE_JSON_FALLBACK = True
        print(f"✗ PostgreSQL connection failed: {e}")
        print("→ Switching to JSON file-based storage as fallback")
        return False


def connect_to_database():
    if USE_JSON_FALLBACK:
        return None  # Return None when using JSON fallback
    
    conn = psycopg.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dbname=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 5432)),  # default PostgreSQL port
    )
    return conn
    

def create_database_if_not_exists():
    if USE_JSON_FALLBACK:
        print("Using JSON storage, skipping database creation")
        return
    
    db_name = os.getenv("DB_NAME")

    # Connect to default 'postgres' database
    try:
        conn = psycopg.connect(
            dbname="postgres",
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 5432))
        )
        conn.autocommit = True  # required to CREATE DATABASE

        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f"CREATE DATABASE {db_name}")
            print(f"Database '{db_name}' created.")
        else:
            print(f"Database '{db_name}' already exists.")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")


def initialize_tables():
    if USE_JSON_FALLBACK:
        print("Using JSON storage, initializing JSON files instead")
        import json_storage
        json_storage.ensure_json_files()
        return
    
    # Connect to PostgreSQL
    db = connect_to_database()
    if db is None:
        return
    
    cursor = db.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        first_name VARCHAR(255) NOT NULL,
        last_name VARCHAR(255) NOT NULL,
        username VARCHAR(255) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS quiz_scores (
        id SERIAL PRIMARY KEY,
        user_id INT,
        score INT,
        total_questions INT,
        quiz_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS quiz_attempted (
        id SERIAL PRIMARY KEY,
        user_id INT,
        quiz_score_id INT,
        question VARCHAR(255),
        user_answer VARCHAR(255),
        correct_answer VARCHAR(255),
        quiz_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (quiz_score_id) REFERENCES quiz_scores(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS images (
        id SERIAL PRIMARY KEY,
        user_id INT,
        profile_image BYTEA,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id SERIAL PRIMARY KEY,
        user_id INT NOT NULL,
        reset_token VARCHAR(100) NOT NULL,
        token_expiry TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    db.commit()
    cursor.close()
    db.close()


# Test connection on module import
test_database_connection()
