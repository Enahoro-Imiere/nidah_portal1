import streamlit as st
import pandas as pd
import sqlite3
import os, time
import os
import psycopg2
import bcrypt
import plotly.express as px
import plotly.graph_objects as go
import json
from PIL import Image
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

from database.db import get_connection


st.set_page_config(page_title="NiDAH-P Portal", layout="wide")


DB_PATH = os.path.join(os.path.dirname(__file__), "nidah.db")

from utils import generate_verification_token, send_verification_email

from database.auth import authenticate_facility

from database.db import create_tables, get_connection, authenticate_user

from auth.auth_utils import register_user

from database.db import get_facility_needs_by_program_type

from auth.program_utils import get_programs

from database.db import get_connection

# app.py (Streamlit part)


if "page" not in st.session_state:
    st.session_state.page = "home"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_role" not in st.session_state:
    st.session_state.user_role = None

if "username" not in st.session_state:
    st.session_state.username = None

if "full_name" not in st.session_state:
    st.session_state.full_name = ""

if "username" not in st.session_state:
    st.session_state.username = ""

if "user_role" not in st.session_state:
    st.session_state.user_role = ""


def match_users_to_facilities():
    """
    Assign users to facilities based on their skills vs facility needs.
    Matches are inserted as 'Pending' in the database.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Get users and their specializations
        cur.execute("""
            SELECT id, specialization
            FROM users
            WHERE role IN ('individual','association')
        """)
        users = cur.fetchall()
        user_skills = {user[0]: [s.strip() for s in user[1].split(",")] for user in users}

        # Get facilities and their needs
        cur.execute("""
            SELECT id, need
            FROM facilities
        """)
        facilities = cur.fetchall()
        facility_needs = {f[0]: [n.strip() for n in f[1].split(",")] for f in facilities}

        assignments = []

        # Calculate matches
        for user_id, skills in user_skills.items():
            best_match = None
            best_score = 0
            for facility_id, need in facility_needs.items():
                score = len(set(skills) & set(needs))
                if score > best_score:
                    best_score = score
                    best_match = facility_id

            if best_match:
                # Insert match as pending
                cur.execute("""
                    INSERT INTO user_assignments (user_id, facility_id, score, assigned_at, status)
                    VALUES (%s, %s, %s, NOW(), 'Pending')
                    ON CONFLICT (user_id) DO UPDATE
                    SET facility_id = EXCLUDED.facility_id,
                        score = EXCLUDED.score,
                        assigned_at = EXCLUDED.assigned_at,
                        status = 'Pending'
                """, (user_id, best_match, best_score))

                assignments.append({
                    "user_id": user_id,
                    "facility_id": best_match,
                    "score": best_score
                })

        conn.commit()
        cur.close()
        conn.close()

        return assignments  # return list of proposed matches

    except Exception as e:
        return f"❌ Error matching users to facilities: {e}"




# -------------------------------------------------
# INITIAL SETUP
# -------------------------------------------------

create_tables()


# -------------------- HOME PAGE --------------------
def home_page():
    st.markdown("""
    <style>
    /* Full-page background */
    .stApp {
        background-image: url('https://images.unsplash.com/photo-1588776814546-2a80230252c5?auto=format&fit=crop&w=1950&q=80');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    /* Gradient overlay for readability */
    .overlay {
        background: rgba(255, 255, 255, 0.85);
        border-radius: 12px;
        padding: 10rem;
        box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    }

    /* Header style */
    .header {
        background-color: rgba(11, 60, 93, 0.9);
        color: white;
        padding: 1rem;
        text-align: center;
        font-size: 2rem;
        font-weight: 700;
        border-radius: 0 0 12px 12px;
    }

    /* Footer style */
    .footer {
        background-color: rgba(11, 60, 93, 0.9);
        color: white;
        padding: 1rem;
        text-align: center;
        font-size: 0.9rem;
        border-radius: 12px 12px 0 0;
        margin-top: 2rem;
    }

    /* Titles and subtitles */
    .title { color: #0b3c5d; font-size: 2.2rem; font-weight: 700; }
    .subtitle { color: #1f4e79; font-size: 1.2rem; margin-bottom: 1rem; }

    /* Cards for login/register section */
    .card { background-color: white; padding: 2rem; border-radius: 12px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08); }
    </style>
    
    <!-- HEADER -->
    <div class="header">
        Nigerians in Diaspora Advanced Health Programme (NiDAH-P)
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([3,1])

    # Left: Overview
    with left:
        st.markdown("""
        <div class="overlay">
            <div class="title">NiDAH Programme</div>
            <div class="subtitle">Harnessing diaspora expertise to strengthen Nigeria’s health system</div>
            <p>
            The NiDAH Programme, designed by the Federal Ministry of Health and Social Welfare, provides a structured framework for engaging Nigerian health professionals in the diaspora to support national health objectives. The initiative strengthens service delivery, specialist care, training, and workforce capacity by enabling short- and medium-term engagements. NiDAH-P facilitates skills transfer, knowledge exchange, and the introduction of advanced clinical services across health facilities nationwide.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Right: Login/Register
    with right:
        st.markdown("""
        <div class="card" style="text-align:center;">
            <h3>Portal Access</h3>
            <p>Please sign in or register to continue</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("###")
        st.markdown("""
        <style>
        .streamlit-button>button {
            background-color: transparent;
            color: #0b3c5d;
            font-weight: bold;
            text-decoration: underline;
            border: none;
        }
        </style>
        """, unsafe_allow_html=True)
        st.markdown("Don't have an account? ", unsafe_allow_html=True)
        if st.button("Register", key="home_register_btn"):
            st.session_state.page = "register"


        if st.button("🔐 Sign in as Individual/Association", use_container_width=True):
            st.session_state.page = "login_user"

        if st.button("🔐 Sign in as Facility", use_container_width=True):
            st.session_state.page = "login_facility"

        


    # FOOTER
    st.markdown("""
    <div class="footer">
        &copy; 2026 Federal Ministry of Health and Social Welfare | PPP/Diaspora Unit | NiDAH Programme | Contact: info@nidah.health.gov.ng
    </div>
    """, unsafe_allow_html=True)



# -------------------------------------------------
# LOGIN PAGE
# -------------------------------------------------
def login_facility_page():
    # CSS for centered card
    st.markdown("""
    <style>
    .centered-card {
        max-width: 300px;
        margin: 100px auto;
        padding: 2rem;
        border-radius: 12px;
        background-color: #f7f9fc;
        text-align: center;
    }
    .login-header {
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        color: #0b3c5d;
    }
    .login-button {
        width: 100%;
        background-color: #0b3c5d;
        color: white;
        font-weight: 600;
        margin-top: 1rem;
    }
    .back-button {
        width: 100%;
        margin-top: 0.5rem;
        background-color: #ccc;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown('<div class="centered-card">', unsafe_allow_html=True)
        st.markdown('<div class="login-header">Facility Sign in</div>', unsafe_allow_html=True)

        facility_code = st.text_input("Facility Code", key="facility_code")
        password = st.text_input("Password", type="password", key="facility_password")

        if st.button("Login", key="facility_login_btn"):
            facility = authenticate_facility(facility_code, password)
            if facility:
                st.session_state.logged_in = True
                st.session_state.user_role = "facility"
                st.session_state.user_id = facility["id"]          # match dashboard
                st.session_state.facility_name = facility["facility_name"]
                st.session_state.full_name = facility["facility_name"]  # for consistency
                st.session_state.page = "facility_dashboard"
                st.rerun()
            else:
                st.error("Invalid facility code or password")
   
        if st.button("Forgot Password?"):
            forgot_password()
        if st.button("🔐 Sign in as User", key="facility_to_user_btn"):
            st.session_state.page = "login_user"
            st.rerun() 
        if st.button("Back to Home", key="facility_back_btn"):
            st.session_state.page = "home"
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
    


def login_user():
    # CSS for centered card
    st.markdown("""
    <style>
    .centered-card {
        max-width: 200px;
        margin: 100px auto;
        padding: 0rem;
        border-radius: 12px;
        background-color: #f7f9fc;
        text-align: center;
    }
    .login-header {
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        color: #0b3c5d;
    }
    .login-button {
        width: 100%;
        background-color: #0b3c5d;
        color: white;
        font-weight: 600;
        margin-top: 1rem;
    }
    .back-button {
        width: 100%;
        margin-top: 0.5rem;
        background-color: #ccc;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

    # Use 3 columns to center horizontally
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown('<div class="centered-card">', unsafe_allow_html=True)
        st.markdown('<div class="login-header">User / Association Sign in</div>', unsafe_allow_html=True)

        username = st.text_input("Username / Association", key="user_login_input")
        password = st.text_input("Password", type="password", key="user_login_pass")

        if st.button("Sign in", key="user_login_btn_user_page"):
            user = authenticate_user(username, password)

            if user:
                st.session_state.logged_in = True
                st.session_state.user_id = user["id"]
                st.session_state.full_name = user["full_name"]
                st.session_state.role = user["role"].strip().lower()
                st.session_state.username = user["username"]
                

                
                # Route based on role
                if user["role"] == "admin":
                    st.session_state.page = "admin_dashboard"
                else:
                    st.session_state.page = "user_dashboard"
               
                st.success(f"Welcome {st.session_state.full_name}")
                st.rerun()
            else:
                st.error("Invalid username or password")
        
        if st.button("Forgot Password?"):
            forgot_password()
        if st.button("🔐 Sign in as Facility", key="user_to_facility_btn"):
            st.session_state.page = "login_facility"
            st.rerun()        
        if st.button("Back to Home", key="user_back_btn_user_page"):
            st.session_state.page = "home"
            st.rerun()       


        st.markdown('</div>', unsafe_allow_html=True)


def forgot_password():
    st.subheader("Forgot Password")

    email_or_username = st.text_input("Enter your registered email or username")

    if st.button("Send Reset Link"):
        import secrets
        import datetime

        try:
            conn = get_connection()

            cur = conn.cursor()

            # Check if user exists
            cur.execute("""
                SELECT id FROM users
                WHERE username = %s OR email = %s
            """, (email_or_username, email_or_username))
            user = cur.fetchone()

            if not user:
                st.error("User not found")
                return

            user_id = user[0]
            # Generate secure token
            token = secrets.token_urlsafe(16)
            expiry = datetime.datetime.now() + datetime.timedelta(hours=1)

            # Insert token into user_password_reset table (create this table in PostgreSQL)
            cur.execute("""
                INSERT INTO user_password_reset (user_id, token, expiry)
                VALUES (%s, %s, %s)
            """, (user_id, token, expiry))

            conn.commit()
            cur.close()
            conn.close()

            # For local testing, show the reset link
            st.success("Password reset link generated!")
            st.info(f"Reset link (for local testing): http://localhost:8501/reset_password?token={token}")

        except Exception as e:
            st.error("Could not generate reset link.")
            st.exception(e)

def reset_password_page():
    st.subheader("Reset Password")

    token = st.text_input("Enter your reset token")
    new_password = st.text_input("Enter your new password", type="password")

    if st.button("Reset Password"):
        import psycopg2
        import datetime

        try:
            conn = get_connection()

            cur = conn.cursor()

            # Verify token
            cur.execute("""
                SELECT user_id, expiry
                FROM user_password_reset
                WHERE token = %s
            """, (token,))
            row = cur.fetchone()

            if not row:
                st.error("Invalid token")
                return

            user_id, expiry = row
            if datetime.datetime.now() > expiry:
                st.error("Token has expired")
                return

            # Update password (hash using crypt)
            cur.execute("""
                UPDATE users
                SET password_hash = crypt(%s, gen_salt('bf'))
                WHERE id = %s
            """, (new_password, user_id))

            # Delete token
            cur.execute("DELETE FROM user_password_reset WHERE token = %s", (token,))

            conn.commit()
            cur.close()
            conn.close()

            st.success("Password has been reset successfully! You can now log in.")

        except Exception as e:
            st.error("Could not reset password.")
            st.exception(e)




# -------------------------------------------------
# USER DASHBOARD
# -------------------------------------------------
def user_dashboard():
    role = st.session_state.get("role", "")
    
    menu_choice = st.sidebar.selectbox(
        "Select Option",
        [
            "Dashboard Overview",
            "Profile",
            "Programs",
            "Settings",
            "Logout"
        ]
    )

    program_category = None  # default
    programs_dict = get_programs()  # your function returning {category: [programs]}
    program_category = st.selectbox("Select Program Category", list(programs_dict.keys()))


    TRAINING_MODES = [
        "Select one",
        "On-site (Physical)",
        "Virtual",
        "Hybrid"
    ]

    if "user_id" not in st.session_state:
        st.error("Session expired. Please log in again.")
        st.session_state.clear()
        st.session_state.page = "login"
        st.rerun()

    st.title(f"Welcome, {st.session_state.full_name}")
    role = st.session_state.get("role", "diaspora")  # default to diaspora if role missing
    
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # ================= DASHBOARD OVERVIEW =================
    if menu_choice == "Dashboard Overview":
        st.subheader("Dashboard Overview")

        # --- Approved interests (show need + facility) ---
        cur.execute("""
            SELECT f.facility_name, n.need
            FROM facility_needs n
            JOIN user_interests ui ON n.id = ui.need_id
            JOIN facilities f ON n.facility_id = f.id
            WHERE ui.user_id = %s AND ui.status = 'Approved'
            ORDER BY f.facility_name
        """, (st.session_state.user_id,))
        approved_interests = cur.fetchall()

        # --- Pending / awaiting approval ---
        cur.execute("""
            SELECT DISTINCT f.facility_name
            FROM facility_needs n
            JOIN user_interests ui ON n.id = ui.need_id
            JOIN facilities f ON n.facility_id = f.id
            WHERE ui.user_id = %s AND ui.status = 'Pending'
            ORDER BY f.facility_name
        """, (st.session_state.user_id,))
        pending_facilities = cur.fetchall()

        if not approved_interests and not pending_facilities:
            st.info("You have not engaged in any program yet.")
        else:
            if approved_interests:
                st.success("Programs you have engaged in (Approved):")
                for facility, need in approved_interests:
                    st.write(f"• {need} @ {facility}")

            if pending_facilities:
                st.warning("Awaiting approval:")
                for facility_tuple in pending_facilities:
                    st.write(f"• {facility_tuple[0]}")

        # ==================================================
        #                TRAINING LIST
        # ==================================================
        training_list = []  # ✅ always initialize

        cur.execute("""
            SELECT
                ui.training_title,
                ui.training_status
            FROM user_interests ui
            JOIN facility_needs n ON ui.need_id = n.id
            WHERE ui.user_id = %s
              AND n.program_type = 'Training'
              AND ui.status = 'Approved'
            ORDER BY ui.training_status
        """, (st.session_state.user_id,))
        training_list = cur.fetchall()

        st.markdown("### 📘 List of Training(s)")

        if not training_list:
            st.info("No training records yet.")
        else:
            for title, status in training_list:
                if status == "Done":
                    st.success(f"✅ {title} — {status}")
                elif status == "Ongoing":
                    st.warning(f"⏳ {title} — {status}")
                else:
                    st.info(f"🕒 {title} — {status}")

        cur.close()
        conn.close()


    # ================= PROGRAMS =================
    if menu_choice == "Programs":

         programs_list = ["Training", "Services"]
         program_category = st.selectbox("Select Program Category", programs_list)

         if program_category:
             st.subheader(f"{program_category} Programs")

             # Open connection
             conn = get_connection()
             cur = conn.cursor()

             try:
                 # Fetch facility needs from PostgreSQL
                 cur.execute(
                     "SELECT facility_id, facility_name, need_id, need, number "
                     "FROM facility_needs WHERE program_type = %s",
                     (program_category,)
                 )
                 needs = cur.fetchall()

                 if not needs:
                     st.info(f"No facilities found under {program_category}.")
                 else:
                     import pandas as pd
                     df = pd.DataFrame(
                         needs,
                         columns=["facility_id", "facility_name", "need_id", "need", "number"]
                     )
                     st.write(df)  # quick demo for presentation

             finally:
                 cur.close()
                 conn.close()


            
    # ---------------- UPLOAD DOCUMENTS ----------------
    if menu_choice == "Upload Documents":
        st.write("Current role:", role)

        st.subheader("Upload Your Qualifications")
        st.info("Accepted formats: PDF, PNG, JPEG")
        


        if role != "association":

            # ---- License Number ----
            license_number = st.text_input(
                "Enter your Medical License Number",
                key="license_number_input"
            )

            # ---- Registration status ----
            col1, col2 = st.columns(2)

            with col1:
                renew_license = st.radio(
                    "Would you want to renew your license?",
                    ["No", "Yes"],
                    horizontal=True
                )

            with col2:
                not_registered_ng = st.radio(
                    "Not registered in Nigeria?",
                    ["No", "Yes"],
                    horizontal=True
                )

            # ---- Main license upload ----
            uploaded_file = st.file_uploader(
                "Are you registered in Nigeria? Upload Supporting Document(s)",
                type=["pdf", "png", "jpeg"]
            )

            
        else:
            # Associations do not need license
            license_number = None
            uploaded_file = None
            renew_license = "No"
            not_registered_ng = "No"
        
            # ---- Temporary license option ----
            temp_license = st.radio(
                "Need a temporary license(s)?",
                ["No", "Yes"],
                horizontal=True,
                key="temp_license"
            )

        # ---- Additional qualifications ----
        additional_files = st.file_uploader(
            "Upload Additional Qualification(s)",
            type=["pdf", "png", "jpeg"],
            accept_multiple_files=True
        )

        # ---- Submit ----
        if st.button("Submit Documents"):

            # --- User validation ---
            if role != "association":
                if not license_number:
                    st.error("Please enter your license number.")
                    st.stop()
                if not uploaded_file:
                    st.error("Please upload your medical license file.")
                    st.stop()

            # --- File saving ---
            BASE_DIR = os.getcwd()
            LICENSE_DIR = os.path.join(BASE_DIR, "uploads/licenses")
            EXTRA_DIR = os.path.join(BASE_DIR, "uploads/qualifications")
            os.makedirs(LICENSE_DIR, exist_ok=True)
            os.makedirs(EXTRA_DIR, exist_ok=True)

            # ---- License file ----
            license_path = None
            if uploaded_file:
                ext = uploaded_file.name.split(".")[-1].lower()
                license_filename = f"user_{st.session_state.user_id}_license_{int(time.time())}.{ext}"
                license_path = os.path.join(LICENSE_DIR, license_filename)
                with open(license_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

            # ---- Additional qualifications ----
            extra_paths = []
            if additional_files:
                for file in additional_files:
                    ext = file.name.split(".")[-1].lower()
                    fname = f"user_{st.session_state.user_id}_qual_{int(time.time())}_{file.name}"
                    fpath = os.path.join(EXTRA_DIR, fname)
                    with open(fpath, "wb") as f:
                        f.write(file.getbuffer())
                    extra_paths.append(fpath)

                conn = get_connection()
                cur = conn.cursor()

                if role != "association":
                    # ===== NORMAL USER INSERT =====
                    cur.execute("""
                        INSERT INTO user_documents (
                            user_id,
                            license_number,
                            file_path,
                            renew_license,
                            not_registered_nigeria,
                            additional_files,
                            uploaded_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (user_id, license_number) DO UPDATE
                        SET file_path = EXCLUDED.file_path,
                            renew_license = EXCLUDED.renew_license,
                            not_registered_nigeria = EXCLUDED.not_registered_nigeria,
                            additional_files = EXCLUDED.additional_files,
                            uploaded_at = NOW()
                    """, (
                        st.session_state.user_id,
                        license_number,
                        license_path,
                        renew_license == "Yes",
                        not_registered_ng == "Yes",
                        extra_paths if extra_paths else None
                    ))

                else:
                    # ===== ASSOCIATION INSERT =====
                    cur.execute("""
                        INSERT INTO association_documents (
                            user_id,
                            additional_files,
                            temp_license,
                            uploaded_at
                        )
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (user_id) DO UPDATE
                        SET additional_files = EXCLUDED.additional_files,
                            temp_license = EXCLUDED.temp_license,
                            uploaded_at = NOW()
                    """, (
                        st.session_state.user_id,
                        extra_paths if extra_paths else None,
                        True if temp_license == "Yes" else False
                    ))

                conn.commit()
                cur.close()
                conn.close()

                st.success("Documents uploaded successfully ✅")







    # ================= LOGOUT =================
    elif menu_choice == "Logout":
        conn.close()
        st.session_state.clear()
        st.session_state.page = "login_user"
        st.rerun()

    conn.close()

# ---------------- Database Helpers / KPI Functions ----------------

def get_facility_count():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) 
        FROM facility_accounts 
        WHERE is_active = TRUE
    """)
    count = cur.fetchone()[0]
    conn.close()
    return count

# ---------------- New: Facilities with Needs ----------------
def get_facilities_with_needs():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.facility_name, n.need, n.quantity, n.timestamp
        FROM facility_accounts f
        LEFT JOIN facility_needs n
        ON f.id = n.facility_id
        WHERE f.is_active = TRUE
        ORDER BY f.facility_name, n.timestamp DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


# ------------------ CONFIG ------------------
conn = get_connection()
cur = conn.cursor()
cur = conn.cursor()

# Keywords to classify as training
training_keywords = [
    "training", "capacity building", "workshop", "mentorship",
    "skills development", "clinical training", "orientation", "coaching"
]

# ------------------ FETCH NEEDS ------------------
conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT id, need FROM facility_needs")

needs = cur.fetchall()

updated_count = 0

for need_id, need_text in needs:
    if not need_text or need_text.strip() == "":
        program_type = "Services"  # empty needs default to Services
    else:
        need_lower = need_text.lower()
        if any(keyword in need_lower for keyword in training_keywords):
            program_type = "Training"
        else:
            program_type = "Services"

    cur.execute("""
        UPDATE facility_needs
        SET program_type = %s
        WHERE id = %s
    """, (program_type, need_id))
    updated_count += 1

# Commit changes
conn.commit()
print(f"✅ Program types updated for {updated_count} needs.")

# Close connection
cur.close()
conn.close()


# -------------------------------------------------
# ADMIN DASHBOARD
# -------------------------------------------------
def admin_dashboard():
    st.set_page_config(layout="wide")

    st.sidebar.title("NIDAH Admin Panel")
    st.sidebar.markdown("---")

    menu = st.sidebar.radio(
        "Navigation",
        [
            "Overview",
            "Users",
            "List of Trainings concluded",
            "Documents",
            "Reports",
            "Approvals",
            "Logout"
        ]
    )

    st.title("Admin Dashboard")
    st.markdown("---")
    st.info("Welcome to the NIDAH Administration Dashboard")


    # ---------------- LOGOUT ----------------
    if menu == "Logout":
        st.session_state.clear()
        st.session_state.page = "login_user"
        st.rerun()

    # ---------------- OVERVIEW ----------------
    if menu == "Overview":
        st.subheader("System Overview")
    
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Facilities Registered", get_facility_count())
        with col2:
            st.metric("Needs Submitted", get_needs_count())
        with col3:
            st.metric("Diaspora Professionals Placed", 45)  # dummy for now

        col4, col5, col6 = st.columns(3)
        with col4:
            st.metric("Local Health Workers Trained", 120)  # dummy
        with col5:
            st.metric("New Clinical Services Introduced", 8)  # dummy
        with col6:
            st.metric("Programs Active", get_program_count())

        st.markdown("---")

        # --- Dummy Data for Charts ---
        kpi_data = pd.DataFrame({
            "Facility": ["NHA", "LUTH", "ABUTH", "JUTH", "FMC Ebute-Metta"],
            "Diaspora_Professionals_Placed": [5, 3, 4, 2, 6],
            "Local_Health_Workers_Trained": [20, 15, 10, 12, 18],
            "New_Clinical_Services": [2, 1, 3, 0, 2],
            "Patient_Feedback_Score": [4.5, 4.2, 4.8, 4.1, 4.6],
            "State": ["FCT","Lagos","Zaria","Jos","Lagos"]
        })

        # --- 1. Diaspora Professionals Placed ---
        fig1 = px.bar(kpi_data, x="Facility", y="Diaspora_Professionals_Placed",
                      title="Diaspora Professionals Placed", color="Diaspora_Professionals_Placed")

        # --- 2. Local Health Workers Trained ---
        fig2 = px.bar(kpi_data, x="Facility", y="Local_Health_Workers_Trained",
                      title="Local Health Workers Trained", color="Local_Health_Workers_Trained")

        # --- 3. New Clinical Services Introduced ---
        fig3 = px.bar(kpi_data, x="Facility", y="New_Clinical_Services",
                      title="New Clinical Services Introduced", color="New_Clinical_Services")


        # --- Display in 2x2 Grid ---
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig1, use_container_width=True)
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            st.plotly_chart(fig3, use_container_width=True)

        # ------ Feedback Analytics ---
        st.markdown("---")
        st.subheader("Programme Feedback Analytics")

        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT 
                    AVG(content_quality),
                    AVG(trainer_effectiveness),
                    AVG(relevance_to_practice),
                    AVG(organisation_logistics),
                    AVG(overall_satisfaction)
                FROM program_feedback
            """)

            result = cur.fetchone()
            conn.close()

            if result and any(result):
                content_avg, trainer_avg, relevance_avg, org_avg, overall_avg = result

                col1, col2, col3 = st.columns(3)
                col4, col5 = st.columns(2)

                col1.metric("Content Quality", f"{round(content_avg,2)}/5")
                col2.metric("Trainer Effectiveness", f"{round(trainer_avg,2)}/5")
                col3.metric("Relevance to Practice", f"{round(relevance_avg,2)}/5")
                col4.metric("Organisation & Logistics", f"{round(org_avg,2)}/5")
                col5.metric("Overall Satisfaction", f"{round(overall_avg,2)}/5")

                # ---- Calculate Automated Overall Programme Score ----
                overall_program_score = (
                    content_avg +
                    trainer_avg +
                    relevance_avg +
                    org_avg +
                    overall_avg
                ) / 5

                st.markdown("### 🏆 Overall Programme Performance Score")
                st.success(f"{round(overall_program_score,2)} / 5")

            else:
                st.info("No feedback submitted yet.")

        except Exception as e:
            st.error("Could not load feedback analytics.")
            st.exception(e)



    # ---------------- USERS ----------------
    if menu == "Users":
        st.subheader("Registered Users")

        try:
            conn = get_connection()
            cur = conn.cursor()

            # ---------------- Facilities ----------------
            cur.execute("""
                SELECT facility_code, facility_name, state
                FROM facilities
                ORDER BY facility_name
            """)
            facilities = cur.fetchall()

            if facilities:
                st.markdown("### Facilities")
                df_facilities = pd.DataFrame(facilities, columns=["Username", "Facility Name", "State"])
                st.dataframe(df_facilities, use_container_width=True)
            else:
                st.info("No registered facilities yet.")

            st.markdown("---")  # separator

            # ---------------- Individuals / Associations ----------------
            cur.execute("""
                SELECT username, full_name, role, country
                FROM users
                WHERE role IN ('individual','association')
                ORDER BY role, username
            """)
            users = cur.fetchall()

            if users:
                st.markdown("### Individuals / Associations")
                df_users = pd.DataFrame(users, columns=["Username", "Full Name", "Role", "Country"])
                st.dataframe(df_users, use_container_width=True)
            else:
                st.info("No registered individual or association users yet.")

            conn.close()

        except Exception as e:
            st.error("Could not load users.")
            st.exception(e)

    # ---------------- VIEW USER DOCUMENTS ----------------
    if menu == "Documents":
        st.subheader("Uploaded User Documents")

        uploaded_file = st.file_uploader("Upload a document", type=["pdf", "docx", "jpg", "png"])
        doc_type = st.selectbox("Document Type", ["License", "Certification", "Other"])
        renew_license = st.checkbox("Renew License?")
        not_registered_nigeria = st.checkbox("Not Registered in Nigeria?")
        additional_files = st.text_input("Additional Files (comma-separated)")

        if uploaded_file:
            file_path = f"uploads/{uploaded_file.name}"  # ensure 'uploads' folder exists
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_documents (
                        user_id, document_type, document_name, document_path,
                        renew_license, not_registered_nigeria, additional_files, uploaded_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    st.session_state.user_id,
                    doc_type,
                    uploaded_file.name,
                    file_path,
                    renew_license,
                    not_registered_nigeria,
                    additional_files
                ))
                conn.commit()
                conn.close()
                st.success(f"Document '{uploaded_file.name}' uploaded successfully!")
            except Exception as e:
                st.error("Failed to upload document.")
                st.exception(e)

        # ---------------- Display uploaded documents ----------------
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.full_name, d.document_type, d.document_name, d.document_path,
                       d.renew_license, d.not_registered_nigeria, d.additional_files, d.uploaded_at
                FROM user_documents d
                JOIN users u ON d.user_id = u.id
                ORDER BY d.uploaded_at DESC
            """)
            rows = cursor.fetchall()
            conn.close()
  
            if rows:
                for full_name, doc_type, doc_name, doc_path, renew, not_registered, additional, uploaded_at in rows:
                    st.markdown(f"**{full_name}** - {doc_type} ({uploaded_at.strftime('%Y-%m-%d %H:%M')})")
                    st.write("Renew License:", renew)
                    st.write("Not Registered in Nigeria:", not_registered)
                    st.write("Additional Files:", additional)

                    if doc_path and os.path.exists(doc_path):
                        with open(doc_path, "rb") as f:
                            st.download_button(f"Download {doc_name}", f.read(), file_name=doc_name)
                    else:
                        st.warning(f"File not found: {doc_name}")
                    st.markdown("---")
            else:
                st.info("No documents uploaded yet.")

        except Exception as e:
            st.error("Failed to fetch documents.")
            st.exception(e)



    # ---------------- REPORTS ----------------
    if menu == "Reports":
        st.subheader("Program Reports & Data Upload")
        st.markdown(
            "Upload files for review, or download reports for analysis."
        )

        report_type = st.selectbox(
            "Select Report to View/Download",
            [
                "Facility Needs",
                "User Registrations",
                "Matched Users",
                "Uploaded Documents",
                "Program Activities"
            ]
        )

        conn = get_connection()
        cur = conn.cursor()

        try:
            if report_type == "Facility Needs":
                cur.execute("""
                    SELECT f.facility_name, f.state, n.need, n.quantity, n.timestamp
                    FROM facility_needs n
                    JOIN facilities f ON n.facility_id = f.id
                    ORDER BY f.facility_name, n.timestamp
                """)
                rows = cur.fetchall()
                columns = ["Facility", "State", "Need", "Quantity", "Submitted At"]

            elif report_type == "User Registrations":
                cur.execute("""
                    SELECT username, full_name, role, email, country, created_at
                    FROM users
                    ORDER BY role, username
                """)
                rows = cur.fetchall()
                columns = ["Username", "Full Name", "Role", "Email", "Country", "Registered At"]

            elif report_type == "Matched Users":
                cur.execute("""
                    SELECT m.user_id, u.full_name, m.facility_id, f.facility_name, m.matched_at
                    FROM user_facility_matches m
                    JOIN users u ON m.user_id = u.id
                    JOIN facilities f ON m.facility_id = f.id
                    ORDER BY m.matched_at DESC
                """)
                rows = cur.fetchall()
                columns = ["User ID", "User Name", "Facility ID", "Facility Name", "Matched At"]

            elif report_type == "Uploaded Documents":
                cur.execute("""
                    SELECT u.full_name, d.document_type, d.document_name, d.renew_license,
                           d.not_registered_nigeria, d.additional_files, d.uploaded_at
                    FROM user_documents d
                    JOIN users u ON d.user_id = u.id
                    ORDER BY d.uploaded_at DESC
                """)
                rows = cur.fetchall()
                columns = ["Full Name", "Document Type", "Document Name", "Renew License",
                           "Not Registered in Nigeria", "Additional Files", "Uploaded At"]

            elif report_type == "Program Activities":
                cur.execute("""
                    SELECT program_name, start_date, end_date, participants, status
                    FROM programs
                    ORDER BY start_date DESC
                """)
                rows = cur.fetchall()
                columns = ["Program Name", "Start Date", "End Date", "Participants", "Status"]

                conn.close()

            if rows:
                df_report = pd.DataFrame(rows, columns=columns)
                st.dataframe(df_report, use_container_width=True)

                # CSV download
                csv = df_report.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{report_type.replace(' ','_').lower()}.csv",
                    mime="text/csv"
                )

                # Excel download
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_report.to_excel(writer, index=False, sheet_name=report_type[:31])
                excel_data = output.getvalue()
                st.download_button(
                    label="Download Excel",
                    data=excel_data,
                    file_name=f"{report_type.replace(' ','_').lower()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("No data available for this report.")

        except Exception as e:
            st.error("Could not generate report.")
            st.exception(e)



        st.markdown("---")
        st.subheader("Download Feedback Report")

        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT 
                    p.name AS program_name,
                    u.full_name,
                    f.content_quality,
                    f.trainer_effectiveness,
                    f.relevance_to_practice,
                    f.organisation_logistics,
                    f.overall_satisfaction,
                    f.comments,
                    f.submitted_at
                FROM program_feedback f
                JOIN programs p ON f.program_id = p.id
                JOIN users u ON f.user_id = u.id
                ORDER BY f.submitted_at DESC
            """)

            rows = cur.fetchall()
            conn.close()

            if rows:
                df_feedback = pd.DataFrame(rows, columns=[
                    "Program",
                    "Participant",
                    "Content Quality",
                    "Trainer Effectiveness",
                    "Relevance",
                    "Organisation",
                    "Overall Satisfaction",
                    "Comments",
                    "Submitted At"
                ])

                st.dataframe(df_feedback, use_container_width=True)

                # CSV download
                csv = df_feedback.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download Feedback (CSV)",
                    data=csv,
                    file_name="program_feedback.csv",
                    mime="text/csv"
                )

                # Excel download
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_feedback.to_excel(writer, index=False)
                excel_data = output.getvalue()

                st.download_button(
                    "Download Feedback (Excel)",
                    data=excel_data,
                    file_name="program_feedback.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            else:
                st.info("No feedback records found.")

        except Exception as e:
            st.error("Could not generate feedback report.")
            st.exception(e)



    # ---------------- APPROVALS ----------------
    if menu == "Approvals":
        st.subheader("Approvals Dashboard")

        try:
            conn = get_connection()
            cur = conn.cursor()

            # --------------------- Section 1: User-selected Interests ---------------------
            st.markdown("## Pending Diaspora Interests")
            cur.execute("""
                SELECT ui.id, u.full_name, f.facility_name
                FROM user_interests ui
                JOIN users u ON ui.user_id = u.id
                JOIN facility_needs n ON ui.need_id = n.id
                JOIN facilities f ON n.facility_id = f.id
                WHERE ui.status = 'Pending'
                ORDER BY u.full_name, f.facility_name
            """)
            pending_interests = cur.fetchall()

            if not pending_interests:
                st.info("No pending user interests.")
            else:
                for ui_id, user_name, facility_name in pending_interests:
                    col1, col2, col3 = st.columns([3, 4, 2])
                    with col1:
                        st.write(user_name)
                    with col2:
                        st.write(facility_name)
                    with col3:
                        if st.button(f"Approve Interest {ui_id}", key=f"approve_interest_{ui_id}"):
                            cur.execute("""
                                UPDATE user_interests
                                SET status = 'Approved'
                                WHERE id = %s
                            """, (ui_id,))
                            conn.commit()
                            st.success(f"User interest for {user_name} → {facility_name} approved!")
                            st.experimental_rerun()

            st.markdown("---")

            # --------------------- Section 2: Auto-Matched Users ---------------------
            st.markdown("## Pending System Matches")
            cur.execute("""
                SELECT ua.user_id, u.full_name, ua.facility_id, f.facility_name, ua.score, ua.assigned_at
                FROM user_assignments ua
                JOIN users u ON ua.user_id = u.id
                JOIN facilities f ON ua.facility_id = f.id
                WHERE ua.status = 'Pending'
                ORDER BY ua.assigned_at DESC
            """)
            pending_matches = cur.fetchall()

            if not pending_matches:
                st.info("No pending system matches.")
            else:
                for user_id, user_name, facility_id, facility_name, score, assigned_at in pending_matches:
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.markdown(f"**{user_name}** → **{facility_name}** | Score: {score} | Proposed: {assigned_at.strftime('%Y-%m-%d %H:%M')}")
                    with col2:
                        if st.button(f"Approve Match {user_id}", key=f"approve_match_{user_id}"):
                            cur.execute("""
                                UPDATE user_assignments
                                SET status = 'Approved'
                                WHERE user_id = %s
                            """, (user_id,))
                            conn.commit()
                            st.success(f"System match for {user_name} → {facility_name} approved!")
                            st.experimental_rerun()

            cur.close()
            conn.close()

        except Exception as e:
            st.error("Could not load approvals.")
            st.exception(e)


        # ---------------- MATCH USERS TO FACILITIES ----------------
        st.markdown("---")
        st.subheader("Assignments")

        if st.button("Match Users to Facilities"):
            result = match_users_to_facilities()
            st.success(result)




def get_facility_count():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) 
        FROM facilities
        WHERE is_active = TRUE
    """)
    count = cur.fetchone()[0]
    conn.close()
    return count



def get_needs_count():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM facility_needs")
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_user_count():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_program_count():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM programs WHERE is_active = TRUE")  # <- fix here
    count = cur.fetchone()[0]
    conn.close()
    return count





# -------------------------------------------------
# REGISTRATION PAGE
# -------------------------------------------------
def register_page():
    st.title("Create Your NiDAH-P Account")

    # Styles
    st.markdown("""
    <style>
    .header {background-color: rgba(11, 60, 93, 0.9); color: white; padding: 1rem; text-align: center;
        font-size: 2rem; font-weight: 700; border-radius: 0 0 12px 12px; margin-bottom: 1rem;}
    .footer {background-color: rgba(11, 60, 93, 0.9); color: white; padding: 1rem; text-align: center;
        font-size: 0.9rem; border-radius: 12px 12px 0 0; margin-top: 2rem;}
    </style>

    <div class="header">
        Nigerians In Diaspora Advanced Health Programme (NiDAH-P)
    </div>
    """, unsafe_allow_html=True)

    # ------------------- SIDEBAR -------------------
    st.sidebar.subheader("Register As")
    if "reg_type" not in st.session_state:
        st.session_state.reg_type = "Individual"

    reg_type = st.sidebar.radio(
        "",
        ["Individual", "Association", "Facility"],
        index=["Individual", "Association", "Facility"].index(st.session_state.reg_type)
    )
    st.session_state.reg_type = reg_type

    
    st.markdown('<div class="card-register">', unsafe_allow_html=True)

    # ---------------- Individual Registration ----------------
    if reg_type == "Individual":
        st.subheader("Individual Registration")
        full_name = st.text_input("Full Name")
        username = st.text_input("Username")
        email = st.text_input("Email")
        country = st.text_input("Country of Residence")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        cadre = st.selectbox(
            "Cadre", ["Select one", "Doctor", "Nurse", "Laboratory Scientist", "Pharmacist", "Other"]
        )
        if cadre == "Other":
            cadre = st.text_input("Please specify your Cadre")
        specialization = st.selectbox(
            "Specialty", ["Select one", "Urology", "Neurology", "Cardiology", "General Surgery",
                          "Gynaecology", "Nephrology", "Radiology", "Other"]
        )
        if specialization == "Other":
            specialization = st.text_input("Please specify ypur Specialty")

        from auth.auth_utils import register_user
        if st.button("Register as Individual", key="register_individual_btn"):
            if not full_name or not username or not email or not password or not confirm_password:
                st.error("All fields are required.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            elif cadre == "Select one" or specialization == "Select one":
                st.error("Please select a valid Cadre and Specialty.")
            else:
                success, msg = register_user(
                    username=username,
                    full_name=full_name,
                    email=email,
                    password=password,
                    country=country,
                    cadre=cadre,
                    specialization=specialization,
                    role="individual"
                )
                if success:
                    st.success(msg)
                    st.session_state.page = "login_user"
                else:
                    st.error(msg)

    # ---------------- Association Registration ----------------
    elif reg_type == "Association":
        st.subheader("Association Registration")
        association_name = st.text_input("Association Name")
        contact_person = st.text_input("Contact Person")
        username = st.text_input("Username")
        email = st.text_input("Official Email")
        country = st.text_input("Country of Residence")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        cadres = st.multiselect("Cadre(s)", ["Doctor","Nurse","Laboratory Scientist","Pharmacist", "Other"])
        other_cadres = []
        if "Other" in cadres:
            other_text = st.text_input("Please specify other Cadre(s) (comma separated)")
            if other_text:
                other_cadres = [x.strip() for x in other_text.split(",")]
        specializations = st.multiselect("Specialty", ["Urology","Neurology","Cardiology","General Surgery",
                                                       "Gynaecology","Nephrology","Radiology", "Other"])
        other_specs = []
        if "Other" in specializations:
            other_text = st.text_input("Please specify other Specialty(ies) (comma separated)")
            if other_text:
                other_specs = [x.strip() for x in other_text.split(",")]

        from auth.auth_utils import register_user
        if st.button("Register as Association", key="register_association_btn"):
            if not association_name or not contact_person or not username or not email or not password or not confirm_password:
                st.error("All fields are required.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            elif not cadres or not specializations:
                st.error("Please select at least one Cadre and Specialty.")
            else:
                success, msg = register_user(
                    full_name=association_name,
                    username=username,
                    password=password,
                    email=email,
                    country=country,
                    role="association",
                    cadre=", ".join(cadres),
                    specialization=", ".join(specializations)
                )
                if success:
                    st.success(msg)
                    st.session_state.page = "login_user"
                else:
                    st.error(msg)

    # ---------------- Facility Registration ----------------
    elif reg_type == "Facility":
        st.subheader("Facility Registration")
        facility_name = st.selectbox("Facility Name", [
            "Select one","Abubakar Tafawa Balewa University Teaching Hospital, Bauchi",
            "Ahmadu Bello University Teaching Hospital, Zaria",
            "Aminu Kano Teaching Hospital, Kano",
            "Federal Medical Centre, Asaba",
            "Federal Medical Centre, Ebute-Metta",
            "Federal Teaching Hospital, Gombe",
            "Federal University Teaching Hospital, Katsina",
            "Federal University Teaching Hospital, Owerri",
            "Jos University Teaching Hospital, Jos",
            "Lagos University Teaching Hospital, Lagos",
            "National Hospital, Abuja",
            "Nnmandi Azikiwe University Teaching Hospital, Anambra",
            "University of Benin Teaching Hospital, Benin",
            "University of Ilorin Teaching Hospital, Ilorin",
            "University of Maiduguri Teaching Hospital, Maiduguri",
            "University of Nigeria Teaching Hospital, Enugu",
            "University of Port Harcourt Teaching Hospital, Port Harcourt",
            "Usmanu Danfodiyo Teaching Hospital, Sokoto",
            "Federal Medical Centre, Umuahia", 
            "Federal Medical Centre, Hong",
            "Federal Medical Centre, Mubi",
            "Federal Medical Centre, Onitsha",
            "Federal Medical Centre, Misau, Bauchi",
            "National Obstetric Fistula Centre, Ningi",
            "Federal Medical Centre, Yenagoa",
            "Federal Medical Centre, Makurdi",
            "Federal Neuro-Psychiatric Hospital, Maiduguri",
            "National Orthopaedic Hospital, Azare-Hawul",
            "Federal Neuro-Psychiatric Hospital, Calabar",
            "Federal Medical Centre, Ovwian",
            "National Obstetric Fistula Centre, Abakaliki",
            "Federal Neuro-Psychiatric Hospital, Uselu-Benin", 
            "National Orthopaedic Hospital, Benin",
            "National Obstetric Fistula Centre, Benin",
            "Federal Medical Centre, Ikole-Ekiti",
            "Federal Neuro-Psychiatric Hospital, Enugu", 
            "National Orthopaedic Hospital, Enugu",
            "Federal Medical Centre, Jabi",
            "Federal Medical Centre, Kumo",
            "Federal Medical Centre, Okigwe",
            "Federal Medical Centre, Birnin Kudu",
            "Federal Medical Centre, Kafanchan",
            "Federal Neuro-Psychiatric Hospital, Kaduna", 
            "National Eye Centre, Kaduna", 
            "National Ear Centre, Kaduna",
            "Federal Neuro-Psychiatric Hospital, Dawanau", 
            "National Orthopaedic Hospital, Dala",
            "Federal Medical Centre, Daura",
            "National Obstetric Fistula Centre, Katsina",
            "Federal Neuro-Psychiatric Hospital, Budo-Egba",
            "Federal Medical Centre, Epe",
            "Federal Neuro-Psychiatric Hospital, Yaba", 
            "National Orthopaedic Hospital, Igbobi",
            "Federal Medical Centre, Keffi",
            "Federal Medical Centre, Bida",
            "Federal Neuro-Psychiatric Hospital, Aro",
            "Federal Medical Centre, Owo",
            "Federal Medical Centre, Wase",
            "National Orthopaedic Hospital, Jos",
            "Federal Neuro-Psychiatric Hospital, Kware",
            "Federal Medical Centre, Jalingo", 
            "National Orthopaedic Hospital, Jalingo",
            "Federal Medical Centre, Nguru", 
            "Federal Medical Centre, Gusau"

        ])
        facility_type = st.selectbox("Facility Type", ["Select one","Tertiary Hospital","Secondary Hospital","Primary Hospital"])
        state = st.selectbox("State", ["Select one","Abia","Abuja","Adamawa","Akwa Ibom","Anambra","Bauchi","Bayelsa","Benue","Borno","Cross River","Delta","Ebonyi","Edo","Ekiti","Enugu","Gombe","Imo","Jigawa","Kaduna","Kano","Katsina","Kebbi","Kogi","Kwara","Lagos","Nassarawa","Niger","Ogun","Ondo","Osun","Oyo","Plateau","Rivers","Sokoto","Taraba","Yobe","Zamfara"])
        username = st.text_input("Username")
        email = st.text_input("Official Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        from auth.auth_utils import register_user
        if st.button("Register as Facility", key="register_facility_btn"):
            if not facility_name or not username or not email or not password or not confirm_password or not state:
                st.error("All fields are required.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            else:
                success, msg = register_user(
                    full_name=facility_name,
                    username=username,
                    password=password,
                    email=email,
                    country=state,
                    role="facility",
                    cadre="",
                    specialization=""
                )
                if success:
                    st.success(msg)
                    st.session_state.page = "login_user"
                else:
                    st.error(msg)

    st.markdown("---")
    if st.button("Already have an account? Sign In", key="register_signin_btn"):
        st.session_state.page = "login_user"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
   

    # ---------------- Footer ----------------

    st.markdown("""
    <div class="footer">
        &copy; 2026 Federal Ministry of Health and Social Welfare | PPP/Diaspora Unit | NiDAH-P | Contact: info@nidah.health.gov.ng
    </div>
    """, unsafe_allow_html=True)



#---------------------------------------------------
# FACILITY DASHBOARD
#---------------------------------------------------
def facility_dashboard_page():

    # --- Session check ---
    if "user_id" not in st.session_state or st.session_state.get("user_role") != "facility":
        st.error("Session expired. Please log in again.")
        st.session_state.page = "login_facility"
        st.rerun()

    st.write(st.session_state.user_id)

    st.title(f"🏥 Facility Dashboard")
    st.subheader(st.session_state.facility_name)

    # --- Sidebar ---
    st.sidebar.title("Facility Menu")
    menu_choice = st.sidebar.radio(
        "Navigate",
        ["Register Need", "View Submitted Needs", "Logout"]
    )

    # --- Logout ---
    if menu_choice == "Logout":
        st.session_state.clear()
        st.session_state.page = "login_facility"
        st.rerun()


    # ---------------- Register Need ----------------
    if menu_choice == "Register Need":
        st.subheader("Submit Your Facility Need")

        need = st.text_input("Need Description")
        number = st.number_input("Number", min_value=1, value=1)

        if st.button("Submit Need", key="submit_facility_need"):
            if not need.strip():
                st.error("Please enter a valid need.")
            else:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO facility_needs (facility_id, need, number)
                        VALUES (%s, %s, %s)
                    """, (st.session_state.user_id, need.strip(), number))
                    conn.commit()
                    st.success("Need submitted successfully!")
                except Exception as e:
                    st.error("Failed to submit need.")
                    st.exception(e)
                finally:
                    if 'cursor' in locals():
                        cursor.close()
                    if 'conn' in locals():
                        conn.close()


    # ---------------- View Submitted Needs ----------------
    elif menu_choice == "View Submitted Needs":
        st.subheader("Your Submitted Needs")

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT need, quantity, timestamp
                FROM facility_needs
                WHERE facility_id = %s
                ORDER BY timestamp DESC
            """, (st.session_state.user_id,))
            needs = cursor.fetchall()
            conn.close()

            if not needs:
                st.info("No needs submitted yet.")
            else:
                df_needs = pd.DataFrame(
                    needs,
                    columns=["Need", "Number", "Submitted At"]
                )
                st.dataframe(df_needs, use_container_width=True)

        except Exception as e:
            st.error("Could not load submitted needs.")
            st.exception(e)
    
    st.markdown("### 🗑️ Manage Submitted Needs")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, need, number, created_at
        FROM facility_needs
        WHERE facility_id = %s
        ORDER BY created_at DESC
    """, (st.session_state.user_id,))

    needs = cursor.fetchall()

    if not needs:
        st.info("No needs submitted yet.")
    else:
        for need_id, need_text, number, created_at in needs:
            hours_passed = (datetime.now() - created_at).total_seconds() / 3600
            editable = hours_passed <= 24

            st.divider()
            col1, col2, col3 = st.columns([5, 2, 3])

            # ================= DISPLAY =================
            with col1:
                st.write(f"**{need_text}** (x{number})")
                st.caption(f"Submitted: {created_at.strftime('%Y-%m-%d %H:%M')}")

            with col2:
                if editable:
                    st.success("Editable")
                else:
                    st.error("Locked")

            # ================= ACTIONS =================
            with col3:
                if editable:
                    edit_key = f"edit_{need_id}"
                    delete_key = f"delete_{need_id}"

                    if st.button("✏️ Edit", key=edit_key):
                        st.session_state.editing_need_id = need_id
                        st.session_state.edit_need_text = need_text
                        st.session_state.edit_number = number

                    if st.button("🗑️ Delete", key=delete_key):
                        cursor.execute(
                            "DELETE FROM facility_needs WHERE id = %s",
                            (need_id,)
                        )
                        conn.commit()
                        st.success("Need deleted successfully.")
                        st.rerun()
                else:
                    st.write("—")

            # ================= EDIT FORM =================
            if st.session_state.get("editing_need_id") == need_id:
                st.markdown("#### ✏️ Edit Need")

                new_need = st.text_input(
                    "Need Description",
                    st.session_state.edit_need_text,
                    key=f"need_input_{need_id}"
                )

                new_number = st.number_input(
                    "Number",
                    min_value=1,
                    value=st.session_state.edit_number,
                    key=f"number_input_{need_id}"
                )

                save_col, cancel_col = st.columns(2)

                with save_col:
                    if st.button("💾 Save", key=f"save_{need_id}"):
                        cursor.execute("""
                            UPDATE facility_needs
                            SET need = %s, number = %s
                            WHERE id = %s
                        """, (new_need.strip(), new_number, need_id))

                        conn.commit()
                        st.success("Need updated successfully.")
                        st.session_state.editing_need_id = None
                        st.rerun()

                with cancel_col:
                    if st.button("❌ Cancel", key=f"cancel_{need_id}"):
                        st.session_state.editing_need_id = None
                        st.rerun()

    cursor.close()
    conn.close()



# ---------------- Routing / Page Display ----------------

def main():
    if "page" not in st.session_state:
        st.session_state.page = "home"

    pages = {
        "home": home_page,
        "login_user": login_user,
        "login_facility": login_facility_page,
        "register": register_page,
        "user_dashboard": user_dashboard,
        "facility_dashboard": facility_dashboard_page,
        "admin_dashboard": admin_dashboard
    }

    if st.session_state.page in pages:
        pages[st.session_state.page]()
    else:
        st.session_state.page = "home"
        pages["home"]()

if __name__ == "__main__":
    main()



