import streamlit as st
import pandas as pd
import datetime
import io
import os
import matplotlib.pyplot as plt
import database as db
import bcrypt

# --- Initialize Backend Database (Supports MySQL & SQLite) ---
db.init_db()

# --- Enterprise Layout Configuration ---
st.set_page_config(
    page_title="NovaSure Claims Platform | Enterprise Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State for Authentication ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None

# --- Login Page ---
def login_page():
    st.title("🔐 NovaSure Secure Login")
    st.caption("Access restricted to registered users in Security Zone")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Fetch user from Security Zone DB
        user_record = db.get_user_by_username(username)
        if user_record:
            stored_hash = user_record["password_hash"].encode("utf-8")
            if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success(f"✅ Welcome {username}! Redirecting to NovaSure Claims Platform...")
                st.experimental_rerun()
            else:
                st.error("❌ Invalid password. Please try again.")
        else:
            st.error("❌ User not found in Security Zone.")

# --- Logout Function ---
def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.experimental_rerun()

# --- Main Application Wrapper ---
def main_app():
    st.sidebar.success(f"🔒 Authenticated as {st.session_state.username}")
    if st.sidebar.button("Logout"):
        logout()

    # Fetch current live database status
    kpis = db.get_dashboard_kpis()
    active_engine_name = "🟢 MySQL Enterprise (3306)" if kpis.get("active_backend") == "mysql" else "📁 SQLite Engine (Local)"

    # --- Global Sidebar (System Metadata & Navigation Zones) ---
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/shield.png", width=64)
        st.title("NovaSure Suite")
        st.caption("Core Claims Intake & Adjudication System")
        st.caption(f"Release: `v3.0-Production` | Engine: `{active_engine_name}`")

        st.divider()
        app_zone = st.radio(
            "Application Zones",
            [
                "📁 Claims Zone",
                "🏢 Maintenance Zone",
                "🔐 Security Zone",
                "📊 Dashboard Zone"
            ]
        )

        st.divider()
        st.caption(f"📁 Claims in Backend DB: **{kpis['total_claims']}**")
        st.caption(f"📎 Registered Attachments: **{kpis['total_docs']}**")
        st.caption(f"🏢 Linked Entities: **{kpis['total_entities']}**")
        st.caption(f"👥 Active Users: **{kpis['active_users']}**")
        st.caption(f"🗄️ Connected Engine: **{kpis.get('active_backend', 'sqlite').upper()}**")
        st.divider()
        st.caption(f"🔒 Session Authenticated: {st.session_state.username}")
        st.caption("Tenant: Global Commercial Casualty Ops")

    # --- Existing Zones (Claims, Dashboard, etc.) ---
    # Keep your existing Claims Zone, Maintenance Zone, Security Zone, Dashboard Zone code here
    # (unchanged from your original file, except now gated behind login)

    # Example: Claims Zone
    if app_zone == "📁 Claims Zone":
        st.subheader("Claims Operations Zone")
        st.caption("Manage claims lifecycle: intake, search, bulk upload, attachments.")
        # Existing Claims Zone code continues...

# --- Entry Point ---
if not st.session_state.authenticated:
    login_page()
else:
    main_app()
