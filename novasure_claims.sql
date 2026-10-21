CREATE TABLE app_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE COLLATE NOCASE NOT NULL,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    reserve_authority REAL DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    last_login_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_number TEXT UNIQUE NOT NULL,
    policy_number TEXT NOT NULL,
    insured_entity TEXT NOT NULL,
    claimant_name TEXT NOT NULL,
    claimant_email TEXT,
    claimant_phone TEXT,
    lob TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    jurisdiction_state TEXT NOT NULL,
    incident_date TEXT NOT NULL,
    reported_date TEXT NOT NULL,
    status TEXT DEFAULT 'New',
    priority TEXT DEFAULT 'Medium',
    incident_location TEXT,
    incident_narrative TEXT NOT NULL,
    incurred_reserve REAL DEFAULT 0,
    assigned_adjuster_id INTEGER,
    created_by INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(assigned_adjuster_id) REFERENCES app_users(id),
    FOREIGN KEY(created_by) REFERENCES app_users(id)
);

CREATE TABLE attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    document_class TEXT NOT NULL,
    document_type TEXT NOT NULL,
    lob TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    claim_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_bytes BLOB NOT NULL,
    verification_status TEXT DEFAULT 'Unverified',
    adjuster_notes TEXT,
    uploaded_by INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(claim_id) REFERENCES claims(id) ON DELETE CASCADE,
    FOREIGN KEY(uploaded_by) REFERENCES app_users(id)
);

CREATE TABLE entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    contact_name TEXT,
    email TEXT,
    phone TEXT,
    address TEXT,
    is_active INTEGER DEFAULT 1,
    created_by INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(created_by) REFERENCES app_users(id)
);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action_type TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id INTEGER,
    details TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES app_users(id)
);

CREATE INDEX idx_claim_search ON claims(claim_number, policy_number, insured_entity, claimant_name);