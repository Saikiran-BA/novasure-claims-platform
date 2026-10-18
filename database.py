"""Database layer for secure_catalog_app.py (MySQL / Amazon Aurora MySQL).

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
    """Create or safely extend the tables used by the secure catalog app."""
    conn = db_connect()
    try:
        cur = conn.cursor()
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
        # Upgrade the earlier demo products table without dropping existing rows.
        cur.execute("SHOW COLUMNS FROM products LIKE 'created_by'")
        if cur.fetchone() is None:
            cur.execute("ALTER TABLE products ADD COLUMN created_by BIGINT NULL")
        cur.execute("SHOW COLUMNS FROM products LIKE 'created_at'")
        if cur.fetchone() is None:
            cur.execute(
                "ALTER TABLE products ADD COLUMN created_at "
                "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
            )
        conn.commit()
        cur.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # Bootstrap only when both variables are deliberately supplied. Never use
    # a hard-coded/default administrator password.
    admin_username = os.getenv("ADMIN_USERNAME", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if bool(admin_username) != bool(admin_password):
        raise RuntimeError("Set both ADMIN_USERNAME and ADMIN_PASSWORD, or neither.")
    if admin_username and admin_password:
        import re
        from werkzeug.security import generate_password_hash

        if len(admin_password) < 12:
            raise RuntimeError("ADMIN_PASSWORD must be at least 12 characters.")
        if not re.fullmatch(r"[A-Za-z0-9_.@-]{3,80}", admin_username):
            raise RuntimeError("ADMIN_USERNAME must be 3-80 characters using letters, numbers, dot, underscore, @, or hyphen.")
        existing = query_one("SELECT id FROM app_users WHERE username = %s", (admin_username,))
        if not existing:
            execute(
                "INSERT INTO app_users (username, display_name, password_hash, role, is_active) "
                "VALUES (%s, %s, %s, 'admin', TRUE)",
                (admin_username, admin_username, generate_password_hash(admin_password)),
            )


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
