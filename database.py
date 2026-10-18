"""
Database layer (MySQL / Amazon Aurora MySQL).

This module intentionally uses the catalog application's own schema and DB_*
configuration. It does not silently fall back to SQLite: a misconfigured or
unreachable production database must fail closed rather than create a separate
local database and appear to work.
"""
from __future__ import annotations

import os
from typing import Any, Sequence
import mysql.connector
from mysql.connector import IntegrityError
import bcrypt

DB_HOST = os.getenv("DB_HOST", "").strip()
DB_USER = os.getenv("DB_USER", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "catalogdb").strip()
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))


def db_connect():
    """Open a short-lived connection to the configured Aurora/MySQL database."""
    if not all((DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)):
        raise RuntimeError(
            "Database configuration missing. Set DB_HOST, DB_USER, DB_PASSWORD, and DB_NAME."
        )
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        connection_timeout=DB_CONNECT_TIMEOUT,
        autocommit=False,
    )


def init_db() -> None:
    """Create or safely extend the tables used by the app."""
    conn = db_connect()
    try:
        cur = conn.cursor()
        # --- Users table for login/authentication ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
                id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(80) NOT NULL UNIQUE,
                display_name VARCHAR(120) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('admin', 'user') NOT NULL DEFAULT 'user',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        # --- Products table (existing demo) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                created_by BIGINT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_products_created_at (created_at),
                CONSTRAINT fk_products_created_by
                    FOREIGN KEY (created_by) REFERENCES app_users(id)
                    ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        conn.commit()
        cur.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- Generic Query Helpers ---
def query_one(sql: str, params: Sequence[Any] = ()):
    conn = db_connect()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, tuple(params))
        result = cur.fetchone()
        cur.close()
        return result
    finally:
        conn.close()


def query_all(sql: str, params: Sequence[Any] = ()):
    conn = db_connect()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, tuple(params))
        results = cur.fetchall()
        cur.close()
        return results
    finally:
        conn.close()


def execute(sql: str, params: Sequence[Any] = ()) -> int:
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, tuple(params))
        conn.commit()
        result = cur.lastrowid
        cur.close()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- User Management Functions ---
def get_user_by_username(username: str) -> dict | None:
    """Fetch a user record by username."""
    return query_one("SELECT * FROM app_users WHERE username = %s AND is_active = TRUE", (username,))


def create_user(username: str, display_name: str, password: str, role: str = "user") -> int:
    """Create a new user with hashed password."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    try:
        return execute(
            "INSERT INTO app_users (username, display_name, password_hash, role, is_active) VALUES (%s, %s, %s, %s, TRUE)",
            (username, display_name, password_hash, role),
        )
    except IntegrityError:
        raise ValueError("Username already exists.")


def deactivate_user(username: str) -> None:
    """Deactivate a user account (soft delete)."""
    execute("UPDATE app_users SET is_active = FALSE WHERE username = %s", (username,))


def validate_login(username: str, password: str) -> bool:
    """Check if username/password combination is valid."""
    user = get_user_by_username(username)
    if not user:
        return False
    stored_hash = user["password_hash"].encode("utf-8")
    return bcrypt.checkpw(password.encode("utf-8"), stored_hash)
