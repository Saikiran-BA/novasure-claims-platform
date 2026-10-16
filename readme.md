# NovaSure Claims Platform — Python Application Concept

A prototype application in Python that simulates an enterprise commercial claims intake and adjudication platform. The solution demonstrates **SDLC, STLC, CI/CD**, and **Business Analysis** activities around digital claims intake, automated triage, and operational risk mitigation.

---

## 🛠️ Architecture & Technology Stack

* **Frontend Layer**: Streamlit (Python UI with real-time responsive state and custom SaaS enterprise styling)
* **Backend Database Layer**: SQLite / PostgreSQL with indexed tables and ACID compliance (`database.py`)
* **Storage Engine**: Dedicated physical binary storage directory for evidence, medical records, and policy attachments
* **Data Processing**: Pandas and NumPy for batch ingestion and multi-attribute SQL querying

---

## 📂 Application Zones & Features

### 1. 📁 Claims Zone
* **New Claims**: Full manual intake form covering **Section 1: Policy & Classification**, **Section 2: Claimant & Exposure Details**, and **Section 3: Incident Narrative**. Directly creates indexed claims in SQLite.
* **Recent Claims**: Grid view fetching the latest claims from the database with active reserve tallies and unique insured counts.
* **Quick Search Criteria**: Real-time SQL keyword search querying Claim IDs, Policy Numbers, Insured Entities, and Claimant Names simultaneously.
* **Advanced Multi-Filter Search**: Granular filtering across Lines of Business (LOB), Claim Status, Jurisdiction States, Triage Priority Tiers, and Incurred Reserve ranges ($).
* **Bulk Upload (CSV FNOL)**:
  * Accepts mass CSV files covering all digital FNOL intake fields.
  * Ingests, validates, and partitions claims directly into their designated Lines of Business (**GL, WC, VA, PD**).
  * Auto-assigns sequential IDs (`NS-2026-XXXX`) and matches specialized adjusters with available capacity.
  * Includes a built-in 1-click **Download Master FNOL CSV Template** button and ready-to-test dataset loader.
* **Attachments Upload & Workbench**:
  * Upload form capturing **Title**, **Class of Document** (*Legal, Medical, Evidence, Financial, Policy, Compliance, Adjuster Notes*), **Type of Document** (*PDF, Image, Spreadsheet, Word Doc, Notice*), **LOB Type**, **Claim Type**, and **Associated Claim ID**.
  * Filterable master grid with 4 operational action workbench tools:
    * **Preview**: Tailored rendering for photographic evidence, certified electronic document canvases, or code/text.
    * **Download**: Direct export preserving original file bytes and MIME types.
    * **Email**: Secure email transmission interface with logging to the database audit trail.
    * **Edit Metadata**: In-place updates for classifications, verification states, and adjuster dossier notes.

### 2. 🏢 Maintenance Zone
* **Entities Management**: Master Data Management (MDM) portal to create and administer external organizations and people linked across claims (*Insured Corporations, Medical Providers & Clinics, Defense Law Firms, Subcontractors, Third-Party Adverse Carriers*).
* **Search Criteria**: Search and query master entities by classification type or live keyword search.

### 3. 🔐 Security Zone
* **User Management & RBAC**: Administer internal staff credentials, roles (*Lead Systems Analyst, Senior Claims Adjuster, Claims Triage Specialist, Legal Counsel Liaison, Compliance Auditor, Claims Admin*), maximum reserve approval authority limits, and active status toggles.

### 4. 📊 Dashboard Zone
* **Analytics & Reporting**: Real-time executive metrics tracking intake cycle time, clerical error rate reduction, total reserve exposure, and active caseload balance.
* **Interactive Visualizations**: Dynamic bar charts and tables breaking down distribution by Line of Business (LOB) and comparing adjuster caseloads against maximum capacity caps.
* **Business Analysis Impact**: Structured comparison showcasing how digital automation eliminates manual keying delays, reduces errors, and prevents adjuster burnout.

---

## 🚀 How to Run the Prototype

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Launch the Application**:
   ```bash
   streamlit run NovaSure_Claims_Platform.py
   ```
   Open `http://localhost:8501` in your browser. All records, entities, and attachments will persist in the backend database.
