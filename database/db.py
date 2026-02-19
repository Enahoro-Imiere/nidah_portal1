# database/db.py
import psycopg2
import bcrypt
from psycopg2.extras import RealDictCursor



# ---------------- CONNECTION ----------------

import psycopg2

def get_connection():
    return psycopg2.connect(
        host="aws-1-eu-west-2.pooler.supabase.com",
        port=5432,
        dbname="postgres",
        user="postgres.emriuutnqdvufycgiarf",
        password="Ena@101#oro",  # use your real password
        sslmode="require"
    )




# ---------------- CREATE TABLES ----------------
def create_tables():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            full_name TEXT,
            association_name TEXT,
            facility_name TEXT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            country TEXT,
            role TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            cadre TEXT,
            specialization TEXT,
            status TEXT DEFAULT 'active'
        )
        """)

        # Programs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS programs (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            active BOOLEAN DEFAULT TRUE
        )
        """)

        # Interests table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS interests (
            id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(id),
            program_id INT REFERENCES programs(id),
            period TEXT DEFAULT '',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()
    finally:
        conn.close()

# ---------------- AUTHENTICATION ----------------

def authenticate_user(username, password):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT id, username, password_hash, role, full_name
        FROM users
        WHERE username = %s
    """, (username,))

    user = cur.fetchone()
    conn.close()

    if user:
        stored_hash = user['password_hash'].encode('utf-8')
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            return {
                "id": user['id'],
                "full_name": user['full_name'],
                "username": user['username'],
                "role": user['role']
            }

    return None


def get_facility_needs_by_program_type(program_type):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            f.id AS facility_id,
            f.facility_name,
            n.id AS need_id,
            n.need,
            n.number
        FROM facility_needs n
        JOIN facilities f ON n.facility_id = f.id
        WHERE n.program_type = %s
        ORDER BY f.facility_name
    """, (program_type,))

    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return results



