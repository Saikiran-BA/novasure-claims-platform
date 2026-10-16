"""
NovaSure Claims Platform - Enterprise Dual-Mode Backend Operations Engine
Seamlessly supports both MySQL and SQLite.
- MySQL: Enterprise production (localhost:3306, AWS RDS, Cloud SQL).
- SQLite: Zero-setup local persistence fallback.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# --- Configuration & Engine Detection ---
# Set DB_TYPE="mysql" to use MySQL, or "sqlite" for zero-setup local SQLite.
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB", "novasure_claims"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
}

SQLITE_FILE = os.getenv("NOVASURE_DB", "/tmp/novasure_claims.db")
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/tmp/novasure_storage/attachments"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Detect if pymysql is available
try:
    import pymysql
    import pymysql.cursors
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False

import sqlite3

# Determine active backend safely
ACTIVE_BACKEND = "sqlite"
if DB_TYPE == "mysql":
    if HAS_PYMYSQL:
        try:
            test_conn = pymysql.connect(
                host=MYSQL_CONFIG["host"],
                user=MYSQL_CONFIG["user"],
                password=MYSQL_CONFIG["password"],
                port=MYSQL_CONFIG["port"]
            )
            test_conn.close()
            ACTIVE_BACKEND = "mysql"
        except Exception:
            ACTIVE_BACKEND = "sqlite"
    else:
        ACTIVE_BACKEND = "sqlite"


def get_connection():
    """Returns an active database connection for either MySQL or SQLite."""
    global ACTIVE_BACKEND
    if ACTIVE_BACKEND == "mysql" and HAS_PYMYSQL:
        try:
            return pymysql.connect(
                host=MYSQL_CONFIG["host"],
                user=MYSQL_CONFIG["user"],
                password=MYSQL_CONFIG["password"],
                database=MYSQL_CONFIG["database"],
                port=MYSQL_CONFIG["port"],
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
        except Exception:
            ACTIVE_BACKEND = "sqlite"
            
    conn = sqlite3.connect(SQLITE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _format_query(sql: str) -> str:
    """Translates parameter placeholders between SQLite (?) and MySQL (%s)."""
    if ACTIVE_BACKEND == "mysql":
        return sql.replace("?", "%s")
    return sql


def _get_val(row, idx=0):
    """Safely extracts a column value from tuple, sqlite3.Row, or MySQL dict."""
    if row is None:
        return 0
    if isinstance(row, dict):
        return list(row.values())[idx]
    return row[idx]


def init_db():
    """Initializes tables, indexes, and enterprise seed records across MySQL or SQLite."""
    global ACTIVE_BACKEND
    
    # If MySQL mode, ensure database exists first
    if ACTIVE_BACKEND == "mysql" and HAS_PYMYSQL:
        try:
            admin_conn = pymysql.connect(
                host=MYSQL_CONFIG["host"],
                user=MYSQL_CONFIG["user"],
                password=MYSQL_CONFIG["password"],
                port=MYSQL_CONFIG["port"],
                autocommit=True
            )
            with admin_conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_CONFIG['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            admin_conn.close()
        except Exception as e:
            print(f"[Warning] Could not initialize MySQL database ({e}). Falling back to SQLite.")
            ACTIVE_BACKEND = "sqlite"

    conn = get_connection()
    is_mysql = (ACTIVE_BACKEND == "mysql")

    auto_inc = "AUTO_INCREMENT" if is_mysql else "AUTOINCREMENT"
    text_type = "TEXT"
    time_def = "CURRENT_TIMESTAMP"

    cursor = conn.cursor()

    # 1. Claims Table
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY {auto_inc},
            claim_id VARCHAR(64) UNIQUE NOT NULL,
            lob VARCHAR(128) NOT NULL,
            policy_number VARCHAR(128) NOT NULL,
            insured_entity VARCHAR(255) NOT NULL,
            claimant_name VARCHAR(255) NOT NULL,
            loss_date VARCHAR(64) NOT NULL,
            total_incurred DOUBLE DEFAULT 0,
            status VARCHAR(128) DEFAULT 'Open - Adjuster Assigned',
            adjuster_id VARCHAR(64),
            subrogation VARCHAR(128) DEFAULT 'None',
            litigation_status VARCHAR(128) DEFAULT 'None',
            priority VARCHAR(64) DEFAULT 'Standard (P3)',
            loss_state VARCHAR(32) DEFAULT 'TX',
            fnol_narrative {text_type},
            created_at TIMESTAMP DEFAULT {time_def}
        )
    """)

    # 2. Entities Table
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY {auto_inc},
            entity_id VARCHAR(64) UNIQUE NOT NULL,
            entity_name VARCHAR(255) NOT NULL,
            entity_type VARCHAR(128) NOT NULL,
            tax_id VARCHAR(64),
            primary_contact VARCHAR(255),
            email VARCHAR(255),
            phone VARCHAR(64),
            city VARCHAR(128),
            state VARCHAR(64),
            status VARCHAR(64) DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT {time_def}
        )
    """)

    # 3. Users Table
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY {auto_inc},
            user_id VARCHAR(64) UNIQUE NOT NULL,
            full_name VARCHAR(255) NOT NULL,
            username VARCHAR(128) UNIQUE NOT NULL,
            email VARCHAR(255) NOT NULL,
            role VARCHAR(128) NOT NULL,
            reserve_authority DOUBLE DEFAULT 25000,
            permissions VARCHAR(255) DEFAULT 'Read, Write',
            status VARCHAR(64) DEFAULT 'Active',
            last_login TIMESTAMP DEFAULT {time_def}
        )
    """)

    # 4. Adjusters Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS adjusters (
            adjuster_id VARCHAR(64) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            specialization VARCHAR(128) NOT NULL,
            active_caseload INTEGER DEFAULT 0,
            max_capacity INTEGER DEFAULT 25,
            email VARCHAR(255) NOT NULL
        )
    """)

    # 5. Document Attachments Table
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS document_attachments (
            document_id VARCHAR(64) PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            class_of_document VARCHAR(128) NOT NULL,
            type_of_document VARCHAR(128) NOT NULL,
            lob_type VARCHAR(128) NOT NULL,
            claim_type VARCHAR(128) NOT NULL,
            claim_id VARCHAR(64) NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            file_path VARCHAR(512) NOT NULL,
            file_size VARCHAR(64) NOT NULL,
            mime_type VARCHAR(128) DEFAULT 'application/octet-stream',
            upload_timestamp TIMESTAMP DEFAULT {time_def},
            status VARCHAR(64) DEFAULT 'Verified & Stamped',
            notes {text_type}
        )
    """)

    # 6. Email Audit Log Table
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS email_audit_logs (
            id INTEGER PRIMARY KEY {auto_inc},
            timestamp TIMESTAMP DEFAULT {time_def},
            recipient VARCHAR(255) NOT NULL,
            document_id VARCHAR(64) NOT NULL,
            claim_id VARCHAR(64) NOT NULL,
            subject VARCHAR(255) NOT NULL,
            status VARCHAR(128) DEFAULT 'Delivered (TLS 1.3)'
        )
    """)

    # Build SQLite indexes safely
    if not is_mysql:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claims_lob ON claims(lob)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claims_policy ON claims(policy_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claims_insured ON claims(insured_entity)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(entity_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_claim ON document_attachments(claim_id)")
        conn.commit()

    # Seed Default Claims if empty
    cursor.execute("SELECT COUNT(*) FROM claims")
    res = cursor.fetchone()
    count_val = _get_val(res, 0)
    
    if count_val == 0:
        default_claims = [
            ("NS-2026-001", "GL (General Liability)", "POL-99214-GL", "Omni Logistics LLC", "Sarah Jenkins", "2026-09-15", 45000, "Open - Adjuster Assigned", "ADJ-101", "Potential (Third-Party Loading Dock)", "Pre-Suit Notice", "Standard (P3)", "TX", "Claimant alleges slip and fall on hydraulic fluid near loading dock bay 4. Loading gate structural fracture identified."),
            ("NS-2026-002", "WC (Workers' Comp)", "POL-77142-WC", "Apex Build Group", "Marcus Vance", "2026-09-28", 18200, "Open - Adjuster Assigned", "ADJ-102", "None", "None", "Standard (P3)", "PA", "Employee suffered lumbar disc strain while lifting heavy scaffolding cross-beams during shift."),
            ("NS-2026-003", "VA (Commercial Vehicle Auto)", "POL-33108-VA", "Metro Fleet Freight", "Express Courier Inc.", "2026-10-02", 73500, "Pending Verification", "ADJ-103", "Active Recovery", "Litigation Formal Hold", "High Exposure (P2)", "TX", "Third-party courier van failed to yield at intersection, colliding with freight truck."),
            ("NS-2026-004", "PD (Commercial Property Damage)", "POL-88391-PD", "Crestview Cold Storage", "Crestview Real Estate Group", "2026-10-06", 64000, "Open - Adjuster Assigned", "ADJ-104", "Defective Product", "None", "High Exposure (P2)", "FL", "Ammonia refrigerant valve ruptured inside freezer room #2, spoiling pallets of inventory.")
        ]
        sql_claims = _format_query("""
            INSERT INTO claims (claim_id, lob, policy_number, insured_entity, claimant_name, loss_date, total_incurred, status, adjuster_id, subrogation, litigation_status, priority, loss_state, fnol_narrative)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)
        cursor.executemany(sql_claims, default_claims)

    cursor.execute("SELECT COUNT(*) FROM adjusters")
    res_adj = cursor.fetchone()
    count_adj = _get_val(res_adj, 0)
    
    if count_adj == 0:
        default_adjusters = [
            ("ADJ-101", "David Chen", "GL / Commercial", 18, 25, "dchen@novasure.internal"),
            ("ADJ-102", "Elena Rostova", "WC / Indemnity", 21, 25, "erostova@novasure.internal"),
            ("ADJ-103", "Marcus Sterling", "VA / Complex Auto", 14, 20, "msterling@novasure.internal"),
            ("ADJ-104", "Rachel Ward", "Property & Casualty", 9, 20, "rward@novasure.internal")
        ]
        sql_adj = _format_query("""
            INSERT INTO adjusters (adjuster_id, name, specialization, active_caseload, max_capacity, email)
            VALUES (?, ?, ?, ?, ?, ?)
        """)
        cursor.executemany(sql_adj, default_adjusters)

    cursor.execute("SELECT COUNT(*) FROM entities")
    res_ent = cursor.fetchone()
    count_ent = _get_val(res_ent, 0)
    
    if count_ent == 0:
        default_entities = [
            ("ENT-101", "Omni Logistics LLC", "Insured Corporation", "EIN-74-8921102", "Arthur Pendelton", "admin@omnilogistics.com", "+1 (555) 432-8900", "Dallas", "TX", "Active"),
            ("ENT-102", "Apex Build Group", "Insured Corporation", "EIN-23-4410982", "Marcus Brogan", "claims@apexbuild.com", "+1 (555) 321-7788", "Pittsburgh", "PA", "Active"),
            ("ENT-103", "Metro Fleet Freight", "Insured Corporation", "EIN-81-2290119", "Cynthia Hayes", "chayes@metrofleet.com", "+1 (555) 889-1234", "Houston", "TX", "Active"),
            ("ENT-104", "Baker & Hostetler LLP", "Defense Law Firm", "EIN-34-1189201", "James T. Vance, Esq.", "jvance@bakerdefense.com", "+1 (555) 998-3322", "Austin", "TX", "Active"),
            ("ENT-105", "Memorial Hermann Orthopedic Institute", "Medical Provider / Clinic", "EIN-74-5512093", "Dr. Katherine Bell, MD", "records@memorialhermann.org", "+1 (555) 443-1200", "Houston", "TX", "Active"),
            ("ENT-106", "Travelers Commercial Lines", "Third-Party Adverse Carrier", "EIN-06-0566000", "Subrogation Unit 4", "subro@travelers.com", "+1 (800) 252-4633", "Hartford", "CT", "Active")
        ]
        sql_ent = _format_query("""
            INSERT INTO entities (entity_id, entity_name, entity_type, tax_id, primary_contact, email, phone, city, state, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)
        cursor.executemany(sql_ent, default_entities)

    cursor.execute("SELECT COUNT(*) FROM users")
    res_usr = cursor.fetchone()
    count_usr = _get_val(res_usr, 0)
    
    if count_usr == 0:
        default_users = [
            ("USR-101", "Sarah Jenkins", "sjenkins", "sjenkins@novasure.internal", "Lead Systems Analyst", 100000, "Full Admin, Reserve Authority, Policy Overrides", "Active"),
            ("USR-102", "David Chen", "dchen", "dchen@novasure.internal", "Senior Claims Adjuster", 50000, "Claims Create, Edit, Reserve Authority P2", "Active"),
            ("USR-103", "Elena Rostova", "erostova", "erostova@novasure.internal", "Senior Claims Adjuster", 50000, "Claims Create, Edit, Reserve Authority P2", "Active"),
            ("USR-104", "James Vance", "jvance", "jvance@bakerdefense.com", "Legal Counsel Liaison", 25000, "Legal Hold Stance, Pleading Upload", "Active"),
            ("USR-105", "Michael Torres", "mtorres", "mtorres@novasure.internal", "Claims Triage Specialist", 10000, "FNOL Intake, Schema Validation", "Active")
        ]
        sql_usr = _format_query("""
            INSERT INTO users (user_id, full_name, username, email, role, reserve_authority, permissions, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """)
        cursor.executemany(sql_usr, default_users)

    cursor.execute("SELECT COUNT(*) FROM document_attachments")
    res_doc = cursor.fetchone()
    count_doc = _get_val(res_doc, 0)
    
    if count_doc == 0:
        doc1_path = STORAGE_DIR / "DOC-2026-001_gate_shear_fracture_site4.jpg"
        doc1_path.write_bytes(b"NOVASURE CLAIMS EVIDENCE DOSSIER - PHOTO ASSET GATE 4")

        doc2_path = STORAGE_DIR / "DOC-2026-002_ime_marcus_vance_lumbar.pdf"
        doc2_path.write_bytes(b"%PDF-1.7 INDEPENDENT MEDICAL EXAM EVALUATION MARCUS VANCE")

        doc3_path = STORAGE_DIR / "DOC-2026-003_txdot_police_crash_report_88291.pdf"
        doc3_path.write_bytes(b"%PDF-1.7 TEXAS DPS POLICE COLLISION REPORT #88291")

        default_docs = [
            ("DOC-2026-001", "Loading Gate Structural Fracture Inspection Photo", "Evidence & Investigation", "Photographic Image", "GL (General Liability)", "Property Damage", "NS-2026-001", "gate_shear_fracture_site4.jpg", str(doc1_path), "2.4 MB", "image/jpeg", "2026-10-14 09:22:15", "Verified & Stamped", "Photographed by field inspector at Omni Logistics Terminal 4."),
            ("DOC-2026-002", "Treating Physician Lumbar IME & Work Capacity Evaluation", "Medical & Health Records", "PDF Document", "WC (Workers' Comp)", "Workers' Indemnity & Lost Time", "NS-2026-002", "ime_marcus_vance_lumbar.pdf", str(doc2_path), "1.1 MB", "application/pdf", "2026-10-14 11:45:00", "Verified & Stamped", "Independent medical evaluation confirming L4-L5 disc protrusion."),
            ("DOC-2026-003", "Texas Dept of Public Safety Highway Crash Report", "Evidence & Investigation", "PDF Document", "VA (Commercial Vehicle Auto)", "Subrogation / Third-Party Recovery", "NS-2026-003", "txdot_police_crash_report_88291.pdf", str(doc3_path), "3.8 MB", "application/pdf", "2026-10-14 14:10:30", "Under Legal Review", "State police crash report #TX-2026-9912. Adverse driver cited.")
        ]
        sql_docs = _format_query("""
            INSERT INTO document_attachments (document_id, title, class_of_document, type_of_document, lob_type, claim_type, claim_id, file_name, file_path, file_size, mime_type, upload_timestamp, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)
        cursor.executemany(sql_docs, default_docs)

    if not is_mysql:
        conn.commit()
    conn.close()


# ==========================================================
# 1. CLAIMS ZONE BACKEND OPERATIONS
# ==========================================================
def create_claim(record: dict) -> str:
    """Inserts a single new claim into the database and updates adjuster caseload."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM claims")
    res = cursor.fetchone()
    count_val = _get_val(res, 0)
    new_claim_id = f"NS-2026-{count_val + 1:03d}"
    
    sql = _format_query("""
        INSERT INTO claims (claim_id, lob, policy_number, insured_entity, claimant_name, loss_date, total_incurred, status, adjuster_id, subrogation, litigation_status, priority, loss_state, fnol_narrative)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)
    cursor.execute(sql, (
        new_claim_id,
        record["lob"],
        record["policy_number"],
        record["insured_entity"],
        record["claimant_name"],
        record["loss_date"],
        record.get("total_incurred", 15000),
        record.get("status", "Open - Adjuster Assigned"),
        record.get("adjuster_id", "ADJ-101"),
        record.get("subrogation", "None"),
        record.get("litigation_status", "None"),
        record.get("priority", "Standard (P3)"),
        record.get("loss_state", "TX"),
        record.get("fnol_narrative", "Standard intake.")
    ))
    
    if record.get("adjuster_id"):
        adj_sql = _format_query("UPDATE adjusters SET active_caseload = active_caseload + 1 WHERE adjuster_id = ?")
        cursor.execute(adj_sql, (record["adjuster_id"],))
        
    if ACTIVE_BACKEND == "sqlite":
        conn.commit()
    conn.close()
    return new_claim_id


def get_recent_claims(limit: int = 50) -> pd.DataFrame:
    """Returns the most recent claims from the backend DB."""
    conn = get_connection()
    sql = _format_query("SELECT * FROM claims ORDER BY id DESC LIMIT ?")
    df = pd.read_sql_query(sql, conn, params=(limit,))
    conn.close()
    return df


def quick_search_claims(search_query: str) -> pd.DataFrame:
    """Fast indexed keyword search across Claim ID, Policy Number, Insured, and Claimant."""
    conn = get_connection()
    pattern = f"%{search_query.strip()}%"
    sql = _format_query("""
        SELECT * FROM claims 
        WHERE claim_id LIKE ? OR policy_number LIKE ? OR insured_entity LIKE ? OR claimant_name LIKE ?
        ORDER BY id DESC
    """)
    df = pd.read_sql_query(sql, conn, params=(pattern, pattern, pattern, pattern))
    conn.close()
    return df


def advanced_search_claims(lob_list=None, status_list=None, state_list=None, priority_list=None, min_reserve=0, max_reserve=1000000, start_date=None, end_date=None) -> pd.DataFrame:
    """Comprehensive multi-filter search against the backend claims repository."""
    conn = get_connection()
    sql = "SELECT * FROM claims WHERE total_incurred >= ? AND total_incurred <= ?"
    params = [min_reserve, max_reserve]
    
    if lob_list:
        placeholders = ",".join(["?"] * len(lob_list))
        sql += f" AND lob IN ({placeholders})"
        params.extend(lob_list)
        
    if status_list:
        placeholders = ",".join(["?"] * len(status_list))
        sql += f" AND status IN ({placeholders})"
        params.extend(status_list)
        
    if state_list:
        placeholders = ",".join(["?"] * len(state_list))
        sql += f" AND loss_state IN ({placeholders})"
        params.extend(state_list)
        
    if priority_list:
        placeholders = ",".join(["?"] * len(priority_list))
        sql += f" AND priority IN ({placeholders})"
        params.extend(priority_list)
        
    if start_date:
        sql += " AND loss_date >= ?"
        params.append(str(start_date))
        
    if end_date:
        sql += " AND loss_date <= ?"
        params.append(str(end_date))
        
    sql += " ORDER BY id DESC"
    sql = _format_query(sql)
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def bulk_import_claims_from_df(df: pd.DataFrame) -> list:
    """Batch imports parsed CSV claims directly into SQL."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM claims")
    res = cursor.fetchone()
    current_count = _get_val(res, 0)
    
    cursor.execute("SELECT adjuster_id, specialization, active_caseload FROM adjusters")
    adjusters = cursor.fetchall()
    
    imported_ids = []
    rows_to_insert = []
    
    for idx, row in df.iterrows():
        new_id = f"NS-2026-{current_count + idx + 1:04d}"
        lob_val = row.get("LOB", "GL (General Liability)")
        
        assigned_adj = "ADJ-101"
        for adj in adjusters:
            adj_spec = adj["specialization"] if isinstance(adj, dict) else adj[1]
            adj_id = adj["adjuster_id"] if isinstance(adj, dict) else adj[0]
            if "GL" in lob_val and "GL" in adj_spec:
                assigned_adj = adj_id
                break
            elif "WC" in lob_val and "WC" in adj_spec:
                assigned_adj = adj_id
                break
            elif "VA" in lob_val and ("VA" in adj_spec or "Auto" in adj_spec):
                assigned_adj = adj_id
                break
            elif "PD" in lob_val and "Property" in adj_spec:
                assigned_adj = adj_id
                break
                
        rep_str = str(row.get("Claimant Representation", ""))
        lit_status = "Litigation Formal Hold" if "Counsel" in rep_str or "Attorney" in rep_str else "None"
        
        rows_to_insert.append((
            new_id,
            lob_val,
            str(row.get("Policy Number", "POL-GEN")),
            str(row.get("Insured Entity", "Commercial Insured")),
            str(row.get("Claimant Name", "Primary Claimant")),
            str(row.get("Loss Date", datetime.now().strftime("%Y-%m-%d"))),
            float(row.get("Total Incurred ($)", 15000)),
            "Open - Adjuster Assigned",
            assigned_adj,
            str(row.get("Subrogation", "None")),
            lit_status,
            str(row.get("Priority", "Standard (P3)")),
            str(row.get("Loss State", "TX")),
            str(row.get("FNOL Narrative", "Mass CSV Ingestion"))
        ))
        imported_ids.append(new_id)

    sql_bulk = _format_query("""
        INSERT INTO claims (claim_id, lob, policy_number, insured_entity, claimant_name, loss_date, total_incurred, status, adjuster_id, subrogation, litigation_status, priority, loss_state, fnol_narrative)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)
    cursor.executemany(sql_bulk, rows_to_insert)

    if ACTIVE_BACKEND == "sqlite":
        conn.commit()
    conn.close()
    return imported_ids


# ==========================================================
# 2. ATTACHMENTS & DOCUMENT OPERATIONS
# ==========================================================
def save_document_attachment(doc_id: str, file_name: str, file_bytes: bytes, mime_type: str, metadata: dict):
    """Stores binary file to storage folder and inserts catalog record."""
    file_path = STORAGE_DIR / f"{doc_id}_{file_name}"
    with open(file_path, "wb") as f:
        f.write(file_bytes)
        
    file_size = f"{len(file_bytes) / 1024:.1f} KB" if len(file_bytes) < 1024*1024 else f"{len(file_bytes) / (1024*1024):.1f} MB"
    
    conn = get_connection()
    cursor = conn.cursor()
    sql = _format_query("""
        INSERT INTO document_attachments (document_id, title, class_of_document, type_of_document, lob_type, claim_type, claim_id, file_name, file_path, file_size, mime_type, upload_timestamp, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)
    cursor.execute(sql, (
        doc_id,
        metadata["title"],
        metadata["class_of_document"],
        metadata["type_of_document"],
        metadata["lob_type"],
        metadata["claim_type"],
        metadata["claim_id"],
        file_name,
        str(file_path),
        file_size,
        mime_type,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        metadata.get("status", "Verified & Stamped"),
        metadata.get("notes", "")
    ))
    if ACTIVE_BACKEND == "sqlite":
        conn.commit()
    conn.close()


def get_all_documents(lob_filter=None, class_filter=None, claim_id=None, search=None) -> pd.DataFrame:
    """Retrieves document attachments with dynamic filtering."""
    conn = get_connection()
    sql = "SELECT * FROM document_attachments WHERE 1=1"
    params = []
    
    if lob_filter:
        placeholders = ",".join(["?"] * len(lob_filter))
        sql += f" AND lob_type IN ({placeholders})"
        params.extend(lob_filter)
        
    if class_filter:
        placeholders = ",".join(["?"] * len(class_filter))
        sql += f" AND class_of_document IN ({placeholders})"
        params.extend(class_filter)
        
    if claim_id and claim_id != "All Claims":
        sql += " AND claim_id = ?"
        params.append(claim_id)
        
    if search:
        p = f"%{search.strip()}%"
        sql += " AND (title LIKE ? OR file_name LIKE ? OR notes LIKE ?)"
        params.extend([p, p, p])
        
    sql += " ORDER BY upload_timestamp DESC"
    sql = _format_query(sql)
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def update_document_metadata(doc_id: str, updates: dict):
    conn = get_connection()
    cursor = conn.cursor()
    sql = _format_query("""
        UPDATE document_attachments 
        SET title = ?, class_of_document = ?, type_of_document = ?, lob_type = ?, claim_type = ?, status = ?, notes = ?
        WHERE document_id = ?
    """)
    cursor.execute(sql, (
        updates["title"],
        updates["class_of_document"],
        updates["type_of_document"],
        updates["lob_type"],
        updates["claim_type"],
        updates["status"],
        updates["notes"],
        doc_id
    ))
    if ACTIVE_BACKEND == "sqlite":
        conn.commit()
    conn.close()


def read_attachment_file(doc_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    sql = _format_query("SELECT file_name, file_path, mime_type FROM document_attachments WHERE document_id = ?")
    cursor.execute(sql, (doc_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        f_path = row["file_path"] if isinstance(row, dict) else row[1]
        f_name = row["file_name"] if isinstance(row, dict) else row[0]
        f_mime = row["mime_type"] if isinstance(row, dict) else row[2]
        if os.path.exists(f_path):
            with open(f_path, "rb") as f:
                return f.read(), f_name, f_mime
    return None, None, None


def log_email_dispatch(recipient: str, doc_id: str, claim_id: str, subject: str):
    conn = get_connection()
    cursor = conn.cursor()
    sql = _format_query("""
        INSERT INTO email_audit_logs (timestamp, recipient, document_id, claim_id, subject, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """)
    cursor.execute(sql, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        recipient,
        doc_id,
        claim_id,
        subject,
        "Delivered (TLS 1.3)"
    ))
    if ACTIVE_BACKEND == "sqlite":
        conn.commit()
    conn.close()


def get_email_audit_logs(limit: int = 25) -> pd.DataFrame:
    conn = get_connection()
    sql = _format_query("SELECT * FROM email_audit_logs ORDER BY id DESC LIMIT ?")
    df = pd.read_sql_query(sql, conn, params=(limit,))
    conn.close()
    return df


# ==========================================================
# 3. MAINTENANCE ZONE (ENTITIES MANAGEMENT)
# ==========================================================
def get_all_entities(type_filter=None, search=None) -> pd.DataFrame:
    conn = get_connection()
    sql = "SELECT * FROM entities WHERE 1=1"
    params = []
    
    if type_filter:
        placeholders = ",".join(["?"] * len(type_filter))
        sql += f" AND entity_type IN ({placeholders})"
        params.extend(type_filter)
        
    if search:
        p = f"%{search.strip()}%"
        sql += " AND (entity_name LIKE ? OR entity_id LIKE ? OR primary_contact LIKE ? OR city LIKE ?)"
        params.extend([p, p, p, p])
        
    sql += " ORDER BY id DESC"
    sql = _format_query(sql)
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def create_entity(record: dict) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM entities")
    res = cursor.fetchone()
    count_val = _get_val(res, 0)
    new_ent_id = f"ENT-{count_val + 101:03d}"
    
    sql = _format_query("""
        INSERT INTO entities (entity_id, entity_name, entity_type, tax_id, primary_contact, email, phone, city, state, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)
    cursor.execute(sql, (
        new_ent_id,
        record["entity_name"],
        record["entity_type"],
        record.get("tax_id", "N/A"),
        record.get("primary_contact", "N/A"),
        record.get("email", "info@entity.org"),
        record.get("phone", "+1 (555) 000-0000"),
        record.get("city", "Dallas"),
        record.get("state", "TX"),
        record.get("status", "Active")
    ))
    if ACTIVE_BACKEND == "sqlite":
        conn.commit()
    conn.close()
    return new_ent_id


# ==========================================================
# 4. SECURITY ZONE (USER MANAGEMENT)
# ==========================================================
def get_all_users() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM users ORDER BY id ASC", conn)
    conn.close()
    return df


def create_user(record: dict) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    res = cursor.fetchone()
    count_val = _get_val(res, 0)
    new_user_id = f"USR-{count_val + 101:03d}"
    
    sql = _format_query("""
        INSERT INTO users (user_id, full_name, username, email, role, reserve_authority, permissions, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """)
    cursor.execute(sql, (
        new_user_id,
        record["full_name"],
        record["username"],
        record["email"],
        record["role"],
        record.get("reserve_authority", 25000),
        record.get("permissions", "Read, Write"),
        record.get("status", "Active")
    ))
    if ACTIVE_BACKEND == "sqlite":
        conn.commit()
    conn.close()
    return new_user_id


# ==========================================================
# 5. DASHBOARD ZONE & ANALYTICS
# ==========================================================
def get_dashboard_kpis() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_incurred), 0) FROM claims")
    res_claims = cursor.fetchone()
    total_claims = _get_val(res_claims, 0)
    total_incurred = _get_val(res_claims, 1)
    
    cursor.execute("SELECT COUNT(*) FROM document_attachments")
    res_d = cursor.fetchone()
    total_docs = _get_val(res_d, 0)
    
    cursor.execute("SELECT COUNT(*) FROM entities")
    res_e = cursor.fetchone()
    total_entities = _get_val(res_e, 0)
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'Active'")
    res_u = cursor.fetchone()
    active_users = _get_val(res_u, 0)
    
    lob_df = pd.read_sql_query("SELECT lob AS LOB, COUNT(*) AS Count, SUM(total_incurred) AS `Total Incurred` FROM claims GROUP BY lob", conn)
    adj_df = pd.read_sql_query("SELECT name AS Name, specialization AS Specialization, active_caseload AS `Active Caseload`, max_capacity AS `Max Capacity` FROM adjusters", conn)
    priority_df = pd.read_sql_query("SELECT priority AS Priority, COUNT(*) AS Count FROM claims GROUP BY priority", conn)
    
    conn.close()
    
    return {
        "total_claims": total_claims,
        "total_incurred": total_incurred,
        "total_docs": total_docs,
        "total_entities": total_entities,
        "active_users": active_users,
        "lob_stats": lob_df,
        "priority_stats": priority_df,
        "adjusters": adj_df,
        "active_backend": ACTIVE_BACKEND
    }


# ==========================================================
# 6. SQLITE TO MYSQL ONE-CLICK MIGRATION UTILITY
# ==========================================================
def migrate_sqlite_to_mysql(host="localhost", user="root", password="", database="novasure_claims", port=3306):
    """Utility to transfer all SQLite claims, entities, and attachments directly into MySQL."""
    if not HAS_PYMYSQL:
        raise ImportError("pymysql is required for MySQL migration. Run: pip install pymysql")
        
    mysql_conn = pymysql.connect(
        host=host,
        user=user,
        password=password,
        port=port,
        autocommit=True
    )
    with mysql_conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    mysql_conn.close()
    
    sqlite_conn = sqlite3.connect(SQLITE_FILE)
    mysql_engine_str = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    
    from sqlalchemy import create_engine
    engine = create_engine(mysql_engine_str)
    
    tables = ["claims", "entities", "users", "adjusters", "document_attachments", "email_audit_logs"]
    migrated_counts = {}
    for table in tables:
        try:
            df = pd.read_sql(f"SELECT * FROM {table}", sqlite_conn)
            df.to_sql(table, con=engine, if_exists="replace", index=False)
            migrated_counts[table] = len(df)
            print(f"✅ Migrated {len(df)} records into MySQL table `{table}`")
        except Exception as e:
            print(f"Skipping table {table}: {e}")
            
    sqlite_conn.close()
    return migrated_counts