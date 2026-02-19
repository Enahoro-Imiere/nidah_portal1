# auth_utils.py
import psycopg2
import os
import bcrypt
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


def get_connection():
    return psycopg2.connect(
        "postgresql://postgres.emriuutnqdvufycgiarf:Ena%40101%23oro@aws-1-eu-west-2.pooler.supabase.com:5432/postgres",
        sslmode="require"
    )



# ---------------- Facility Authentication ----------------
def authenticate_facility(facility_code, password):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT id, facility_name, facility_code, password_hash
        FROM facilities
        WHERE LOWER(facility_code) = %s
          AND is_registered = TRUE
    """, (facility_code.lower(),))

    facility = cur.fetchone()
    cur.close()
    conn.close()

    if facility and facility['password_hash']:
        if bcrypt.checkpw(password.encode(), facility['password_hash'].encode()):
            return {
                "id": facility["id"],
                "full_name": facility["facility_name"],
                "facility_code": facility["facility_code"],
                "role": "facility"
            }
    return None


# ---------------- User Authentication ----------------
def authenticate_user(username, password):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT id, full_name, username, password_hash, role
        FROM users
        WHERE LOWER(username) = %s
    """, (username,))
    
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user and user["password_hash"]:
        if bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            return {
                "id": user["id"],
                "full_name": user["full_name"],
                "username": user["username"],
                "role": user["role"].lower()
            }
    return None


# ---------------- Admin Authentication ----------------
def authenticate_admin(username, password):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT id, full_name, username, password_hash
        FROM users
        WHERE username = %s AND role = 'admin'
    """, (username,))
    
    admin = cur.fetchone()
    cur.close()
    conn.close()

    if admin and admin['password_hash']:
        if bcrypt.checkpw(password.encode('utf-8'), admin['password_hash'].encode('utf-8')):
            return {
                "id": admin['id'],
                "full_name": admin['full_name'],
                "username": admin['username'],
                "role": "admin"
            }
    return None


# ---------------- User Registration ----------------
from psycopg2 import errors

def register_user(username, full_name, email, password, role="user",
                  country=None, cadre=None, specialization=None):

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Hash password
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        cur.execute("""
            INSERT INTO users 
            (username, full_name, email, password_hash, role, country, cadre, specialization)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (username.lower(), full_name, email.lower(), hashed_pw,
              role, country, cadre, specialization))

        conn.commit()
        return True, "Registration successful"

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return False, "Username or email already exists."

    except Exception as e:
        conn.rollback()
        return False, "Something went wrong. Please try again."

    finally:
        cur.close()
        conn.close()


# ---------------- Email Verification ----------------
def verify_email(token):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT user_id FROM verification_tokens WHERE token = %s", (token,))
    result = cur.fetchone()

    if result:
        user_id = result['user_id']
        cur.execute("UPDATE users SET is_verified = TRUE WHERE id = %s", (user_id,))
        cur.execute("DELETE FROM verification_tokens WHERE token = %s", (token,))
        conn.commit()
        cur.close()
        conn.close()
        return "Email verified! You can now log in."
    else:
        cur.close()
        conn.close()
        return "Invalid or expired token."
