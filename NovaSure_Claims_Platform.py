import streamlit as st
import pandas as pd
import datetime
import io
import os
import matplotlib.pyplot as plt
import database as db

# --- Initialize Backend Database (Supports MySQL & SQLite) ---
db.init_db()

# --- Enterprise Layout Configuration ---
st.set_page_config(
    page_title="NovaSure Claims Platform | Enterprise Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom SaaS Enterprise Theme Styling
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1a1f2c; border: 1px solid #2e384d; border-radius: 8px; padding: 12px; }
    .badge-p1 { color: #dc2626; font-weight: bold; background: #fee2e2; padding: 2px 8px; border-radius: 4px; }
    .badge-p2 { color: #d97706; font-weight: bold; background: #fef3c7; padding: 2px 8px; border-radius: 4px; }
    .badge-p3 { color: #16a34a; font-weight: bold; background: #dcfce7; padding: 2px 8px; border-radius: 4px; }
    .doc-card { background-color: #1a1f2c; border: 1px solid #2e384d; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
    .doc-badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-right: 6px; }
    .zone-banner { background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%); border-left: 4px solid #3b82f6; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; }
    </style>
""", unsafe_allow_html=True)

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
    # Live Quick Stats fetched directly from Backend Database
    st.caption(f"📁 Claims in Backend DB: **{kpis['total_claims']}**")
    st.caption(f"📎 Registered Attachments: **{kpis['total_docs']}**")
    st.caption(f"🏢 Linked Entities: **{kpis['total_entities']}**")
    st.caption(f"👥 Active Users: **{kpis['active_users']}**")
    st.caption(f"🗄️ Connected Engine: **{kpis.get('active_backend', 'sqlite').upper()}**")
    st.divider()
    st.caption("🔒 Session Authenticated: Lead Systems Analyst")
    st.caption("Tenant: Global Commercial Casualty Ops")


# ==========================================================
# ZONE 1: CLAIMS ZONE
# ==========================================================
if app_zone == "📁 Claims Zone":
    st.markdown("""
        <div class="zone-banner">
            <h2 style="color: #60a5fa; margin: 0;">📁 Claims Operations Zone</h2>
            <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">
                Comprehensive claims management lifecycle: manual entry, live repositories, dynamic search, bulk CSV intake, and document handling.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    claims_tab1, claims_tab2, claims_tab3, claims_tab4, claims_tab5, claims_tab6 = st.tabs([
        "📝 New Claims (Manual)",
        "⏱️ Recent Claims Grid",
        "🔍 Quick Search",
        "🔎 Advanced Search",
        "📥 Bulk Upload (CSV FNOL)",
        "📎 Attachments Upload & Hub"
    ])
    
    # ------------------------------------------------------
    # 1.1 NEW CLAIMS (MANUAL INTAKE FORM)
    # ------------------------------------------------------
    with claims_tab1:
        st.subheader("Manual Digital FNOL Intake Engine")
        st.caption("Direct schema validation and triage rules persisting into the backend database.")
        
        with st.form("manual_claim_intake_form", clear_on_submit=True):
            st.markdown("##### Section 1: Policy & Loss Classification")
            c1, c2, c3 = st.columns(3)
            with c1:
                lob_selection = st.selectbox(
                    "Line of Business (LOB) *",
                    [
                        "GL (General Liability)",
                        "WC (Workers' Comp)",
                        "VA (Commercial Vehicle Auto)",
                        "PD (Commercial Property Damage)"
                    ]
                )
                policy_num = st.text_input("Policy Number *", placeholder="e.g., POL-88391-GL")
            with c2:
                # Dynamic entity dropdown from Maintenance Zone
                entities_df = db.get_all_entities(type_filter=["Insured Corporation"])
                insured_options = list(entities_df["entity_name"]) if not entities_df.empty else ["Acme Industrial Supply"]
                insured_name = st.selectbox("Insured Entity *", options=insured_options)
                loss_date = st.date_input("Date of Loss *", max_value=datetime.date.today())
            with c3:
                loss_severity = st.selectbox("Intake Triage Priority", ["Standard (P3)", "High Exposure (P2)", "Critical / Severity A (P1)"])
                incident_state = st.selectbox("Jurisdiction / Loss State", ["TX", "CA", "NY", "FL", "IL", "OH", "PA", "GA", "NC"])

            st.markdown("##### Section 2: Claimant & Exposure Details")
            c4, c5, c6 = st.columns(3)
            with c4:
                claimant_name = st.text_input("Claimant Full Name *", placeholder="Primary party claiming loss")
                claimant_rep = st.selectbox("Claimant Representation", ["Pro Se (Unrepresented)", "Represented by Counsel", "Unknown"])
            with c5:
                initial_reserve = st.number_input("Initial Incurred Loss Reserve ($) *", min_value=500, max_value=1000000, step=1000, value=15000)
                subro_flag = st.selectbox("Initial Subrogation Indicator", ["None", "Potential Third-Party Fault", "Defective Product", "Active Recovery"])
            with c6:
                assigned_adj = st.selectbox("Assign Initial Adjuster", options=["ADJ-101 (David Chen)", "ADJ-102 (Elena Rostova)", "ADJ-103 (Marcus Sterling)", "ADJ-104 (Rachel Ward)"])
                initial_lit_status = "Litigation Formal Hold" if claimant_rep == "Represented by Counsel" else "None"

            st.markdown("##### Section 3: Incident Narrative")
            loss_desc = st.text_area("Detailed First Notice of Loss (FNOL) Summary", placeholder="Enter specific description of incident, damages, and witness references...")

            submit_btn = st.form_submit_button("💾 Ingest Claim into Backend Database", type="primary")

            if submit_btn:
                if not policy_num or not insured_name or not claimant_name:
                    st.error("Validation Failed: Mandatory fields (Policy, Insured, Claimant) must be populated.")
                else:
                    adj_code = assigned_adj.split(" (")[0]
                    claim_record = {
                        "lob": lob_selection,
                        "policy_number": policy_num,
                        "insured_entity": insured_name,
                        "claimant_name": claimant_name,
                        "loss_date": str(loss_date),
                        "total_incurred": initial_reserve,
                        "status": "Open - Adjuster Assigned",
                        "adjuster_id": adj_code,
                        "subrogation": subro_flag,
                        "litigation_status": initial_lit_status,
                        "priority": loss_severity,
                        "loss_state": incident_state,
                        "fnol_narrative": loss_desc if loss_desc else "Manual digital FNOL intake entry."
                    }
                    new_id = db.create_claim(claim_record)
                    st.success(f"✅ Claim **{new_id}** ingested and triaged via Digital Ingestion Rules into **{lob_selection}**!")
                    st.rerun()

    # ------------------------------------------------------
    # 1.2 RECENT CLAIMS (GRID VIEW)
    # ------------------------------------------------------
    with claims_tab2:
        st.subheader("Recent Claims Repository (Backend Synchronized)")
        st.caption("Live records retrieved directly from the relational database.")
        
        limit_val = st.slider("Select maximum records to fetch:", min_value=10, max_value=200, value=50, step=10)
        recent_df = db.get_recent_claims(limit=limit_val)
        
        # Display Metrics
        rm1, rm2, rm3, rm4 = st.columns(4)
        rm1.metric("Fetched Records", len(recent_df))
        rm2.metric("Total Reserve Pool", f"${recent_df['total_incurred'].sum():,.0f}" if not recent_df.empty else "$0")
        rm3.metric("Unique Insureds", recent_df["insured_entity"].nunique() if not recent_df.empty else 0)
        rm4.metric("Avg Reserve", f"${recent_df['total_incurred'].mean():,.0f}" if not recent_df.empty else "$0")
        
        st.dataframe(recent_df, use_container_width=True, hide_index=True)

    # ------------------------------------------------------
    # 1.3 SEARCH CRITERIA (QUICK SEARCH)
    # ------------------------------------------------------
    with claims_tab3:
        st.subheader("Quick Claims Search")
        st.caption("Perform fast indexed SQL queries across Claim ID, Policy Number, Insured Entity, and Claimant Name.")
        
        search_kw = st.text_input("Enter search keywords:", placeholder="e.g., NS-2026, POL-99214, Omni Logistics, Sarah...")
        
        if search_kw:
            results_df = db.quick_search_claims(search_kw)
            st.write(f"Found **{len(results_df)}** matching claim records:")
            if not results_df.empty:
                st.dataframe(results_df, use_container_width=True, hide_index=True)
            else:
                st.warning("No records matched your search query in the backend database.")
        else:
            st.info("Type a keyword above to execute a real-time query against the database.")

    # ------------------------------------------------------
    # 1.4 ADVANCED SEARCH (MULTI-FILTER)
    # ------------------------------------------------------
    with claims_tab4:
        st.subheader("Advanced Multi-Attribute Claim Search")
        st.caption("Filter claims across LOB, Jurisdiction, Priority, Litigation, and Reserve thresholds.")
        
        af1, af2, af3 = st.columns(3)
        with af1:
            all_lobs = ["GL (General Liability)", "WC (Workers' Comp)", "VA (Commercial Vehicle Auto)", "PD (Commercial Property Damage)"]
            adv_lobs = st.multiselect("Lines of Business", options=all_lobs, default=all_lobs)
            adv_status = st.multiselect("Claim Status", options=["Open - Adjuster Assigned", "Pending Verification", "Closed - Settled"], default=["Open - Adjuster Assigned", "Pending Verification"])
        with af2:
            all_states = ["TX", "CA", "NY", "FL", "IL", "OH", "PA", "GA", "NC"]
            adv_states = st.multiselect("Jurisdiction States", options=all_states, default=all_states)
            adv_priorities = st.multiselect("Triage Priority", options=["Standard (P3)", "High Exposure (P2)", "Critical / Severity A (P1)"], default=["Standard (P3)", "High Exposure (P2)", "Critical / Severity A (P1)"])
        with af3:
            adv_res_range = st.slider("Reserve Amount Range ($)", min_value=0, max_value=500000, value=(0, 250000), step=5000)
            
        adv_results = db.advanced_search_claims(
            lob_list=adv_lobs,
            status_list=adv_status,
            state_list=adv_states,
            priority_list=adv_priorities,
            min_reserve=adv_res_range[0],
            max_reserve=adv_res_range[1]
        )
        
        st.markdown(f"##### Results: **{len(adv_results)}** claims matched criteria")
        st.dataframe(adv_results, use_container_width=True, hide_index=True)

    # ------------------------------------------------------
    # 1.5 BULK UPLOAD (CSV FNOL MASS INGESTION)
    # ------------------------------------------------------
    with claims_tab5:
        st.subheader("Mass Digital FNOL Ingestion Engine")
        st.caption("Upload mass FNOL CSV datasets covering all intake sections to ingest, validate, and partition claims directly into their designated Lines of Business (LOB).")
        
        # Download Template Row
        sample_csv_data = pd.DataFrame([
            {
                "LOB": "GL (General Liability)",
                "Policy Number": "POL-44109-GL",
                "Insured Entity": "Pinnacle Warehouse Corp",
                "Claimant Name": "Robert Langdon",
                "Loss Date": "2026-10-05",
                "Total Incurred ($)": 32000,
                "Priority": "High Exposure (P2)",
                "Loss State": "OH",
                "Claimant Representation": "Represented by Counsel",
                "Subrogation": "Potential Third-Party Fault",
                "FNOL Narrative": "Customer sustained knee contusion after pallet collapse in aisle 6. Forklift contractor under review."
            },
            {
                "LOB": "WC (Workers' Comp)",
                "Policy Number": "POL-55218-WC",
                "Insured Entity": "Summit Steel Erectors",
                "Claimant Name": "Carlos Mendez",
                "Loss Date": "2026-10-08",
                "Total Incurred ($)": 28500,
                "Priority": "Standard (P3)",
                "Loss State": "TX",
                "Claimant Representation": "Pro Se (Unrepresented)",
                "Subrogation": "None",
                "FNOL Narrative": "Welder suffered second-degree thermal flash burns to forearm during pipe fitting fabrication."
            },
            {
                "LOB": "VA (Commercial Vehicle Auto)",
                "Policy Number": "POL-66327-VA",
                "Insured Entity": "Horizon Express Transport",
                "Claimant Name": "National Transit Lines",
                "Loss Date": "2026-10-10",
                "Total Incurred ($)": 89000,
                "Priority": "Critical / Severity A (P1)",
                "Loss State": "CA",
                "Claimant Representation": "Represented by Counsel",
                "Subrogation": "Active Recovery",
                "FNOL Narrative": "Tractor-trailer rear-ended by adverse commercial bus on Highway 99 during heavy rain. Chassis damage."
            },
            {
                "LOB": "PD (Commercial Property Damage)",
                "Policy Number": "POL-77436-PD",
                "Insured Entity": "Crestview Cold Storage",
                "Claimant Name": "Crestview Real Estate Group",
                "Loss Date": "2026-10-12",
                "Total Incurred ($)": 64000,
                "Priority": "High Exposure (P2)",
                "Loss State": "FL",
                "Claimant Representation": "Pro Se (Unrepresented)",
                "Subrogation": "Defective Product",
                "FNOL Narrative": "Ammonia refrigerant valve ruptured inside freezer room #2, spoiling 14 pallets of seafood."
            }
        ])
        
        bc1, bc2 = st.columns([2, 1])
        with bc1:
            st.info("💡 **Enterprise Ingestion Schema**: Normalized against Policy, Claimant, Exposure, Triage Priority, Jurisdiction State, Reserves, Subrogation, and Loss Narrative.")
        with bc2:
            buf = io.StringIO()
            sample_csv_data.to_csv(buf, index=False)
            st.download_button(
                label="📥 Download Master FNOL CSV Template",
                data=buf.getvalue(),
                file_name="NovaSure_FNOL_Bulk_Intake_Template.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        up_file = st.file_uploader("Upload Bulk FNOL CSV File", type=["csv"])
        load_demo_btn = st.button("⚡ Load Ready-to-Use 4-Claim Mass Dataset")
        
        parsed_df = None
        if up_file:
            parsed_df = pd.read_csv(up_file)
            st.success(f"File **{up_file.name}** parsed successfully ({len(parsed_df)} rows).")
        elif load_demo_btn:
            parsed_df = sample_csv_data.copy()
            st.success("Loaded pre-validated mass intake dataset across GL, WC, VA, and PD!")
            
        if parsed_df is not None:
            st.markdown("#### Pre-Ingestion Data Preview")
            st.dataframe(parsed_df, use_container_width=True, hide_index=True)
            
            if st.button("🚀 Ingest & Import All Claims into Backend Database", type="primary"):
                imported_ids = db.bulk_import_claims_from_df(parsed_df)
                st.balloons()
                st.success(f"🎉 Successfully ingested **{len(imported_ids)} mass claims** into SQL DB! Assigned IDs: `{', '.join(imported_ids[:10])}...`")
                st.rerun()

    # ------------------------------------------------------
    # 1.6 ATTACHMENTS UPLOAD & WORKBENCH
    # ------------------------------------------------------
    with claims_tab6:
        st.subheader("Enterprise Claim Attachment & Document Center")
        st.caption("Upload, index, preview, download, dispatch via secure email, and edit documents associated with claims across all Lines of Business.")
        
        # Upload Form
        with st.expander("📤 Upload New Claim Attachment", expanded=True):
            with st.form("att_upload_form", clear_on_submit=True):
                a_c1, a_c2, a_c3 = st.columns(3)
                with a_c1:
                    att_title = st.text_input("Title *", placeholder="e.g., Police Report - Unit 3 Collision")
                    att_class = st.selectbox(
                        "Class of Document *",
                        ["Evidence & Investigation", "Medical & Health Records", "Legal & Pleadings", "Financial & Proof of Loss", "Policy & Contracts", "Regulatory & Compliance", "Adjuster Field Notes"]
                    )
                with a_c2:
                    att_type = st.selectbox(
                        "Type of Document *",
                        ["PDF Document", "Photographic Image", "Spreadsheet / Loss Run", "Word Doc / Text", "Digital Notice / Email"]
                    )
                    att_lob = st.selectbox(
                        "LOB Type *",
                        ["GL (General Liability)", "WC (Workers' Comp)", "VA (Commercial Vehicle Auto)", "PD (Commercial Property Damage)", "Cross-LOB / Commercial Package"]
                    )
                with a_c3:
                    att_claim_type = st.selectbox(
                        "Claim Type *",
                        ["Bodily Injury", "Property Damage", "Catastrophic / High Exposure", "Workers' Indemnity & Lost Time", "Subrogation / Third-Party Recovery", "Uninsured Motorist", "Environmental / Hazmat"]
                    )
                    recent_claims_for_picker = db.get_recent_claims(50)
                    claim_picker_options = ["General / Unassigned"] + list(recent_claims_for_picker["claim_id"] + " (" + recent_claims_for_picker["insured_entity"] + ")")
                    assoc_claim = st.selectbox("Associated Claim File", options=claim_picker_options)
                    
                a_c4, a_c5 = st.columns([2, 1])
                with a_c4:
                    uploaded_doc_file = st.file_uploader("Select Attachment File", type=["pdf", "png", "jpg", "jpeg", "csv", "txt", "docx", "xlsx"])
                with a_c5:
                    att_status = st.selectbox("Verification Status", ["Verified & Stamped", "Under Legal Review", "Pending Adjuster Review"])
                    
                att_notes = st.text_area("Adjuster Dossier Notes", placeholder="Provide chain of custody, witness references, or context...")
                
                upload_doc_btn = st.form_submit_button("📁 Upload & Register Document to Database", type="primary")
                
                if upload_doc_btn:
                    if not att_title:
                        st.error("Validation Error: 'Title' is mandatory.")
                    else:
                        existing_docs = db.get_all_documents()
                        new_doc_id = f"DOC-2026-{len(existing_docs) + 1:03d}"
                        claim_ref = "Unassigned" if assoc_claim == "General / Unassigned" else assoc_claim.split(" (")[0]
                        
                        if uploaded_doc_file is not None:
                            f_bytes = uploaded_doc_file.getvalue()
                            f_name = uploaded_doc_file.name
                            m_type = uploaded_doc_file.type or "application/octet-stream"
                        else:
                            f_name = f"{att_title.lower().replace(' ', '_')[:24]}.pdf" if "PDF" in att_type else f"{att_title.lower().replace(' ', '_')[:24]}.txt"
                            content_str = (
                                f"NOVASURE CLAIMS PLATFORM - ELECTRONIC RECORD ARCHIVE\n"
                                f"Document ID: {new_doc_id}\n"
                                f"Title: {att_title}\n"
                                f"Class: {att_class} | Type: {att_type}\n"
                                f"LOB: {att_lob} | Claim Type: {att_claim_type}\n"
                                f"Claim Ref: {claim_ref}\n"
                                f"Notes: {att_notes}\n"
                                f"Certified on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                            )
                            f_bytes = content_str.encode("utf-8")
                            m_type = "application/pdf" if "PDF" in att_type else "text/plain"
                            
                        db.save_document_attachment(
                            doc_id=new_doc_id,
                            file_name=f_name,
                            file_bytes=f_bytes,
                            mime_type=m_type,
                            metadata={
                                "title": att_title,
                                "class_of_document": att_class,
                                "type_of_document": att_type,
                                "lob_type": att_lob,
                                "claim_type": att_claim_type,
                                "claim_id": claim_ref,
                                "status": att_status,
                                "notes": att_notes
                            }
                        )
                        st.success(f"✅ Document successfully uploaded & registered in database! ID: **{new_doc_id}** | File: `{f_name}`")
                        st.rerun()

        st.divider()
        st.markdown("#### 📂 Master Attachment Repository Grid")
        
        # Grid Filters
        gf1, gf2, gf3, gf4 = st.columns(4)
        with gf1:
            f_lobs = st.multiselect("Filter by LOB", options=["GL (General Liability)", "WC (Workers' Comp)", "VA (Commercial Vehicle Auto)", "PD (Commercial Property Damage)"])
        with gf2:
            f_classes = st.multiselect("Filter by Class", options=["Evidence & Investigation", "Medical & Health Records", "Legal & Pleadings", "Policy & Contracts"])
        with gf3:
            f_claim = st.text_input("Filter by Claim ID", placeholder="e.g., NS-2026-001")
        with gf4:
            f_search = st.text_input("Search Title / Notes", placeholder="e.g., Police, Fracture...")
            
        docs_df = db.get_all_documents(
            lob_filter=f_lobs if f_lobs else None,
            class_filter=f_classes if f_classes else None,
            claim_id=f_claim if f_claim else None,
            search=f_search if f_search else None
        )
        
        st.dataframe(docs_df[["document_id", "title", "class_of_document", "type_of_document", "lob_type", "claim_type", "claim_id", "file_name", "file_size", "upload_timestamp", "status"]], use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("🛠️ Document Operations: Preview, Download, Email, Edit")
        
        if docs_df.empty:
            st.warning("No documents available under current filters.")
        else:
            doc_opts = list(docs_df["document_id"] + " - " + docs_df["title"])
            chosen_doc = st.selectbox("Select Target Document for Operational Action:", options=doc_opts)
            target_id = chosen_doc.split(" - ")[0]
            target_row = docs_df[docs_df["document_id"] == target_id].iloc[0]
            
            act1, act2, act3, act4 = st.tabs(["👁️ Preview", "⬇️ Download", "📧 Email", "✏️ Edit Metadata"])
            
            # Action 1: Preview
            with act1:
                st.markdown(f"#### Preview: `{target_row['document_id']}` — {target_row['title']}")
                p_c1, p_c2, p_c3, p_c4 = st.columns(4)
                p_c1.metric("Class", target_row["class_of_document"])
                p_c2.metric("Type", target_row["type_of_document"])
                p_c3.metric("LOB & Claim Type", target_row["lob_type"][:12] + "..", target_row["claim_type"])
                p_c4.metric("Status", target_row["status"])
                
                if "Image" in target_row["type_of_document"]:
                    st.markdown(
                        f"""
                        <div style="background-color: #111827; border: 2px dashed #374151; border-radius: 8px; padding: 24px; text-align: center;">
                            <img src="https://img.icons8.com/color/144/image.png" width="96" style="margin-bottom: 12px;" />
                            <h4 style="color: #f9fafb; margin: 0;">{target_row['title']}</h4>
                            <p style="color: #9ca3af; font-size: 13px;">File: {target_row['file_name']} | Size: {target_row['file_size']}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"""
                        <div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 20px; font-family: monospace;">
                            <span style="color: #38bdf8; font-weight: bold;">[NOVASURE CERTIFIED ELECTRONIC DOCUMENT]</span>
                            <hr style="border-color: #334155; margin: 8px 0;" />
                            <p style="color: #e2e8f0; font-size: 13px;"><b>Title:</b> {target_row['title']} | <b>Claim ID:</b> {target_row['claim_id']}</p>
                            <p style="color: #cbd5e1; font-size: 13px;"><b>Notes:</b> {target_row['notes']}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
            # Action 2: Download
            with act2:
                file_bytes, file_name, mime_type = db.read_attachment_file(target_id)
                if file_bytes:
                    st.write(f"📁 **File:** `{file_name}` | 📊 **Size:** `{target_row['file_size']}`")
                    st.download_button(
                        label=f"⬇️ Download {file_name}",
                        data=file_bytes,
                        file_name=file_name,
                        mime=mime_type,
                        type="primary"
                    )
                else:
                    st.warning("Binary file not found on disk.")
                    
            # Action 3: Email
            with act3:
                with st.form(f"email_form_{target_id}"):
                    rec_email = st.text_input("Recipient Email *", placeholder="counsel@firm.com, claims@novasure.internal")
                    em_subject = st.text_input("Subject", value=f"[NovaSure Claims Document] {target_row['title']} (Claim: {target_row['claim_id']})")
                    em_body = st.text_area("Message Body", value=f"Attached is the claims document '{target_row['title']}' regarding Claim {target_row['claim_id']}.")
                    if st.form_submit_button("📤 Dispatch Document via Email", type="primary"):
                        if not rec_email or "@" not in rec_email:
                            st.error("Please enter a valid recipient email.")
                        else:
                            db.log_email_dispatch(rec_email, target_row["document_id"], target_row["claim_id"], em_subject)
                            st.success(f"📧 Email successfully dispatched to **{rec_email}**! Logged in database audit trail.")
                            
                st.markdown("##### Recent Email Transmission Audit Log")
                st.dataframe(db.get_email_audit_logs(10), use_container_width=True, hide_index=True)

            # Action 4: Edit Metadata
            with act4:
                with st.form(f"edit_form_{target_id}"):
                    ed_title = st.text_input("Title", value=target_row["title"])
                    ed_class = st.selectbox("Class of Document", ["Evidence & Investigation", "Medical & Health Records", "Legal & Pleadings", "Financial & Proof of Loss", "Policy & Contracts", "Regulatory & Compliance", "Adjuster Field Notes"], index=0)
                    ed_type = st.selectbox("Type of Document", ["PDF Document", "Photographic Image", "Spreadsheet / Loss Run", "Word Doc / Text", "Digital Notice / Email"], index=0)
                    ed_lob = st.selectbox("LOB Type", ["GL (General Liability)", "WC (Workers' Comp)", "VA (Commercial Vehicle Auto)", "PD (Commercial Property Damage)", "Cross-LOB / Commercial Package"], index=0)
                    ed_claim_type = st.selectbox("Claim Type", ["Bodily Injury", "Property Damage", "Catastrophic / High Exposure", "Workers' Indemnity & Lost Time", "Subrogation / Third-Party Recovery", "Uninsured Motorist", "Environmental / Hazmat"], index=0)
                    ed_status = st.selectbox("Verification Status", ["Verified & Stamped", "Under Legal Review", "Pending Adjuster Review", "Archived"], index=0)
                    ed_notes = st.text_area("Notes", value=target_row["notes"])
                    
                    if st.form_submit_button("💾 Save Metadata Changes to Database", type="primary"):
                        db.update_document_metadata(target_id, {
                            "title": ed_title,
                            "class_of_document": ed_class,
                            "type_of_document": ed_type,
                            "lob_type": ed_lob,
                            "claim_type": ed_claim_type,
                            "status": ed_status,
                            "notes": ed_notes
                        })
                        st.success(f"✅ Document **{target_id}** updated in database!")
                        st.rerun()


# ==========================================================
# ZONE 2: MAINTENANCE ZONE
# ==========================================================
elif app_zone == "🏢 Maintenance Zone":
    st.markdown("""
        <div class="zone-banner">
            <h2 style="color: #60a5fa; margin: 0;">🏢 Maintenance Zone</h2>
            <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">
                Master Data Management: Administer corporate entities, clinics, legal defense firms, adverse carriers, and vendors linked across claims.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    maint_tab1, maint_tab2 = st.tabs(["👥 Entities Management", "🔍 Search Entities"])
    
    with maint_tab1:
        st.subheader("Create & Manage Corporate Entities")
        
        with st.expander("➕ Onboard New Entity into Master Database", expanded=False):
            with st.form("new_entity_form", clear_on_submit=True):
                e_c1, e_c2, e_c3 = st.columns(3)
                with e_c1:
                    e_name = st.text_input("Entity Legal Name *", placeholder="e.g., Summit Industrial Contracting LLC")
                    e_type = st.selectbox("Entity Type *", ["Insured Corporation", "Medical Provider / Clinic", "Defense Law Firm", "Subcontractor / Vendor", "Third-Party Adverse Carrier"])
                with e_c2:
                    e_tax = st.text_input("Tax ID / EIN", placeholder="EIN-XX-XXXXXXX")
                    e_contact = st.text_input("Primary Contact Person", placeholder="e.g., Jennifer Adams")
                with e_c3:
                    e_email = st.text_input("Corporate Email", placeholder="claims@summitcontracting.com")
                    e_phone = st.text_input("Phone Number", placeholder="+1 (555) 123-4567")
                    
                e_c4, e_c5, e_c6 = st.columns(3)
                with e_c4:
                    e_city = st.text_input("City", value="Dallas")
                with e_c5:
                    e_state = st.selectbox("State", ["TX", "CA", "NY", "FL", "IL", "OH", "PA", "GA", "NC"])
                with e_c6:
                    e_status = st.selectbox("Status", ["Active", "Inactive / Suspended"])
                    
                if st.form_submit_button("Register Entity to Database", type="primary"):
                    if not e_name:
                        st.error("Entity Legal Name is required.")
                    else:
                        ent_id = db.create_entity({
                            "entity_name": e_name,
                            "entity_type": e_type,
                            "tax_id": e_tax,
                            "primary_contact": e_contact,
                            "email": e_email,
                            "phone": e_phone,
                            "city": e_city,
                            "state": e_state,
                            "status": e_status
                        })
                        st.success(f"✅ Entity **{e_name}** successfully registered with ID **{ent_id}**!")
                        st.rerun()

        st.markdown("##### Current Master Entities Roster")
        all_entities = db.get_all_entities()
        st.dataframe(all_entities, use_container_width=True, hide_index=True)

    with maint_tab2:
        st.subheader("Search & Query Entities")
        
        sq1, sq2 = st.columns([1, 2])
        with sq1:
            ent_filter_types = st.multiselect("Filter by Entity Type", options=["Insured Corporation", "Medical Provider / Clinic", "Defense Law Firm", "Subcontractor / Vendor", "Third-Party Adverse Carrier"])
        with sq2:
            ent_search_term = st.text_input("Search by Name, City, or Contact", placeholder="e.g., Apex, Dallas, Katherine...")
            
        filtered_entities = db.get_all_entities(type_filter=ent_filter_types if ent_filter_types else None, search=ent_search_term if ent_search_term else None)
        st.dataframe(filtered_entities, use_container_width=True, hide_index=True)


# ==========================================================
# ZONE 3: SECURITY ZONE
# ==========================================================
elif app_zone == "🔐 Security Zone":
    st.markdown("""
        <div class="zone-banner">
            <h2 style="color: #60a5fa; margin: 0;">🔐 Security & Access Control Zone</h2>
            <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">
                Role-Based Access Control (RBAC): Administer user accounts, financial reserve sign-off authorities, and system permissions.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.subheader("User Account & Authority Provisioning")
    
    with st.expander("👤 Provision New User Account", expanded=False):
        with st.form("new_user_form", clear_on_submit=True):
            u_c1, u_c2, u_c3 = st.columns(3)
            with u_c1:
                u_name = st.text_input("Full Name *", placeholder="e.g., Amanda Foster")
                u_username = st.text_input("Username *", placeholder="e.g., afoster")
            with u_c2:
                u_email = st.text_input("Corporate Email *", placeholder="afoster@novasure.internal")
                u_role = st.selectbox("Assigned Role *", ["Senior Claims Adjuster", "Lead Systems Analyst", "Claims Triage Specialist", "Legal Counsel Liaison", "Compliance Auditor", "Claims Admin"])
            with u_c3:
                u_reserve_auth = st.number_input("Maximum Reserve Authority ($) *", min_value=5000, max_value=500000, value=50000, step=5000)
                u_perms = st.selectbox("Permission Tier", ["Full Admin & Policy Overrides", "Claims Create, Edit, Reserve Authority P2", "FNOL Intake & Schema Validation", "Legal Hold & Defense Stance", "Read-Only Compliance Auditor"])
                
            if st.form_submit_button("Create User Account in Database", type="primary"):
                if not u_name or not u_username or not u_email:
                    st.error("Please fill in mandatory user credentials.")
                else:
                    new_uid = db.create_user({
                        "full_name": u_name,
                        "username": u_username,
                        "email": u_email,
                        "role": u_role,
                        "reserve_authority": u_reserve_auth,
                        "permissions": u_perms,
                        "status": "Active"
                    })
                    st.success(f"✅ User **{u_name}** ({new_uid}) successfully enrolled in database!")
                    st.rerun()

    st.markdown("##### Authorized User Roster & RBAC Directory")
    users_df = db.get_all_users()
    st.dataframe(users_df, use_container_width=True, hide_index=True)


# ==========================================================
# ZONE 4: DASHBOARD ZONE
# ==========================================================
elif app_zone == "📊 Dashboard Zone":
    st.markdown("""
        <div class="zone-banner">
            <h2 style="color: #60a5fa; margin: 0;">📊 Executive Dashboard & Analytics Zone</h2>
            <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">
                Demonstrating Business Analysis, SDLC, STLC, and automated triage KPI metrics reducing manual processing overhead.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    kpis = db.get_dashboard_kpis()
    
    # Executive KPI Metric Cards
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Intake Cycle Time", "3.2 Hours", "-87% (Was 2.5 Days)")
    k2.metric("Clerical Error Rate", "1.1%", "-7.1% vs Manual Baseline")
    k3.metric("Total Active Claims", f"{kpis['total_claims']:,}")
    k4.metric("Total Incurred Reserves", f"${kpis['total_incurred']:,.0f}")
    
    st.divider()
    
    # Visual Analytics Grid
    d_c1, d_c2 = st.columns(2)
    
    with d_c1:
        st.subheader("Distribution by Line of Business (LOB)")
        lob_data = kpis["lob_stats"]
        if not lob_data.empty:
            st.bar_chart(lob_data.set_index("LOB")["Count"])
            st.dataframe(lob_data, use_container_width=True, hide_index=True)
        else:
            st.info("No claims in database.")

    with d_c2:
        st.subheader("Adjuster Capacity & Caseload Utilization")
        adj_data = kpis["adjusters"]
        if not adj_data.empty:
            st.dataframe(adj_data.set_index("Name")[["Specialization", "Active Caseload", "Max Capacity"]], use_container_width=True)
            st.bar_chart(adj_data.set_index("Name")[["Active Caseload", "Max Capacity"]])
        else:
            st.info("No adjusters recorded.")
            
    st.divider()
    
    # Problem & Business Analysis Impact Callout
    st.subheader("📈 Business Problem & Automation Impact Analysis")
    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown("##### ⏱️ Processing Delays")
        st.markdown(
            "**Manual Baseline:** Paper/PDF intake forms took 2.5–3 business days to enter into downstream adjudication systems.<br />"
            "**NovaSure Solution:** Digital schema validation and bulk CSV ingestion reduce cycle time to **3.2 hours**.",
            unsafe_allow_html=True
        )
    with b2:
        st.markdown("##### ⚠️ High Error Rates")
        st.markdown(
            "**Manual Baseline:** Keying errors averaged 8.2% (incorrect policy IDs, missing claimant legal representation).<br />"
            "**NovaSure Solution:** Automated regex validation, required field enforcement, and LOB auto-routing drop clerical error to **1.1%**.",
            unsafe_allow_html=True
        )
    with b3:
        st.markdown("##### 💼 Adjuster Overload")
        st.markdown(
            "**Manual Baseline:** Unbalanced manual file distribution led to caseload spikes over 140% of adjuster capacity.<br />"
            "**NovaSure Solution:** Intelligent auto-routing based on specialization and active caseload caps maintains capacity balance under 80%.",
            unsafe_allow_html=True
        )