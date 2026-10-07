import streamlit as st
import pandas as pd
import datetime

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
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }
    .badge-p1 { color: #dc2626; font-weight: bold; background: #fee2e2; padding: 2px 8px; border-radius: 4px; }
    .badge-p2 { color: #d97706; font-weight: bold; background: #fef3c7; padding: 2px 8px; border-radius: 4px; }
    .badge-p3 { color: #16a34a; font-weight: bold; background: #dcfce7; padding: 2px 8px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

# --- Production In-Memory Database (Session State) ---
if "claims_db" not in st.session_state:
    st.session_state.claims_db = pd.DataFrame([
        {
            "Claim ID": "NS-2026-001",
            "LOB": "GL (General Liability)",
            "Policy Number": "POL-99214-GL",
            "Insured Entity": "Omni Logistics LLC",
            "Claimant Name": "Sarah Jenkins",
            "Loss Date": "2026-09-15",
            "Total Incurred ($)": 45000,
            "Status": "Open - Adjuster Assigned",
            "Adjuster ID": "ADJ-101",
            "Subrogation": "Potential (Third-Party Loading Dock)",
            "Litigation Status": "Pre-Suit Notice"
        },
        {
            "Claim ID": "NS-2026-002",
            "LOB": "WC (Workers' Comp)",
            "Policy Number": "POL-77142-WC",
            "Insured Entity": "Apex Build Group",
            "Claimant Name": "Marcus Vance",
            "Loss Date": "2026-09-28",
            "Total Incurred ($)": 18200,
            "Status": "Open - Adjuster Assigned",
            "Adjuster ID": "ADJ-102",
            "Subrogation": "None",
            "Litigation Status": "None"
        },
        {
            "Claim ID": "NS-2026-003",
            "LOB": "VA (Commercial Vehicle Auto)",
            "Policy Number": "POL-33108-VA",
            "Insured Entity": "Metro Fleet Freight",
            "Claimant Name": "Express Courier Inc.",
            "Loss Date": "2026-10-02",
            "Total Incurred ($)": 73500,
            "Status": "Pending Verification",
            "Adjuster ID": "ADJ-103",
            "Subrogation": "Active Recovery",
            "Litigation Status": "Litigation Formal Hold"
        }
    ])

if "adjusters_db" not in st.session_state:
    st.session_state.adjusters_db = pd.DataFrame([
        {"Adjuster ID": "ADJ-101", "Name": "David Chen", "Specialization": "GL / Commercial", "Active Caseload": 18, "Max Capacity": 25, "Email": "dchen@novasure.internal"},
        {"Adjuster ID": "ADJ-102", "Name": "Elena Rostova", "Specialization": "WC / Indemnity", "Active Caseload": 21, "Max Capacity": 25, "Email": "erostova@novasure.internal"},
        {"Adjuster ID": "ADJ-103", "Name": "Marcus Sterling", "Specialization": "VA / Complex Auto", "Active Caseload": 14, "Max Capacity": 20, "Email": "msterling@novasure.internal"},
        {"Adjuster ID": "ADJ-104", "Name": "Rachel Ward", "Specialization": "Property & Casualty", "Active Caseload": 9, "Max Capacity": 20, "Email": "rward@novasure.internal"}
    ])

# --- Global Sidebar (System Metadata & Navigation) ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/shield.png", width=64)
    st.title("NovaSure Suite")
    st.caption("Core Claims Intake & Adjudication System")
    st.caption("Release: `v2.4-Production` | Environment: `AWS-East-Prod`")
    
    st.divider()
    nav_module = st.radio(
        "Navigation Hub",
        [
            "📊 Executive Ops Dashboard",
            "📝 Digital Claim Intake (FNOL)",
            "👥 Claims Work Queue & Child Modules",
            "💼 Adjuster Management & Directory"
        ]
    )
    
    st.divider()
    st.caption("🔒 Session Authenticated: Lead Systems Analyst")
    st.caption("Tenant: Global Commercial Casualty Ops")


# ==========================================================
# MODULE 1: EXECUTIVE OPS DASHBOARD
# ==========================================================
if nav_module == "📊 Executive Ops Dashboard":
    st.title("Claims Modernization & Intake Command Center")
    st.markdown("Automating intake from manual paper/email scans into real-time digital routing.")
    
    # Live KPI Row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Avg Intake Cycle Time", "3.2 Hours", "-87% (Was 2.5 Days)")
    col2.metric("Clerical Error Rate", "1.1%", "-7.1% vs Manual Baseline")
    col3.metric("Total Active Claims", len(st.session_state.claims_db))
    total_reserves = st.session_state.claims_db["Total Incurred ($)"].sum()
    col4.metric("Active Total Incurred", f"${total_reserves:,.0f}")
    
    st.divider()
    
    # Analytical Breakdowns
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        st.subheader("Distribution by Line of Business (LOB)")
        lob_counts = st.session_state.claims_db["LOB"].value_counts()
        st.bar_chart(lob_counts)
    
    with d_col2:
        st.subheader("Adjuster Capacity Utilization")
        adj_util = st.session_state.adjusters_db.set_index("Name")[["Active Caseload", "Max Capacity"]]
        st.dataframe(adj_util, use_container_width=True)


# ==========================================================
# MODULE 2: DIGITAL CLAIM INTAKE (FNOL)
# ==========================================================
elif nav_module == "📝 Digital Claim Intake (FNOL)":
    st.title("Digital FNOL Intake Engine")
    st.caption("Replaces manual physical data keying with direct schema validation and triage rules.")
    
    with st.form("new_claim_intake_form", clear_on_submit=True):
        st.subheader("Section 1: Policy & Loss Classification")
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
            insured_name = st.text_input("Insured Entity Name *", placeholder="e.g., Acme Industrial Supply")
            loss_date = st.date_input("Date of Loss *", max_value=datetime.date.today())
        with c3:
            loss_severity = st.selectbox("Intake Triage Priority", ["Standard (P3)", "High Exposure (P2)", "Critical / Severity A (P1)"])
            incident_state = st.selectbox("Jurisdiction / Loss State", ["TX", "CA", "NY", "FL", "IL", "OH", "PA"])

        st.subheader("Section 2: Claimant & Exposure Details")
        c4, c5, c6 = st.columns(3)
        with c4:
            claimant_name = st.text_input("Claimant Full Name *", placeholder="Primary party claiming loss")
            claimant_rep = st.selectbox("Claimant Representation", ["Pro Se (Unrepresented)", "Represented by Counsel", "Unknown"])
        with c5:
            initial_reserve = st.number_input("Initial Incurred Loss Reserve ($) *", min_value=500, max_value=1000000, step=1000, value=15000)
            subro_flag = st.selectbox("Initial Subrogation Indicator", ["None", "Potential Third-Party Fault", "Defective Product"])
        with c6:
            available_adjusters = st.session_state.adjusters_db["Adjuster ID"] + " - " + st.session_state.adjusters_db["Name"]
            assigned_adj = st.selectbox("Assign Initial Adjuster", options=available_adjusters)
            initial_lit_status = "Litigation Formal Hold" if claimant_rep == "Represented by Counsel" else "None"

        st.subheader("Section 3: Incident Narrative")
        loss_desc = st.text_area("Detailed First Notice of Loss (FNOL) Summary", placeholder="Enter specific description of incident, damages, and witness references...")

        submit_btn = st.form_submit_button("Ingest Claim into Core Adjudication Queue")

        if submit_btn:
            if not policy_num or not insured_name or not claimant_name:
                st.error("Validation Failed: Mandatory fields (Policy, Insured, Claimant) must be populated.")
            else:
                new_claim_id = f"NS-2026-00{len(st.session_state.claims_db) + 1}"
                adj_code = assigned_adj.split(" - ")[0]
                
                new_record = {
                    "Claim ID": new_claim_id,
                    "LOB": lob_selection,
                    "Policy Number": policy_num,
                    "Insured Entity": insured_name,
                    "Claimant Name": claimant_name,
                    "Loss Date": str(loss_date),
                    "Total Incurred ($)": initial_reserve,
                    "Status": "Open - Adjuster Assigned",
                    "Adjuster ID": adj_code,
                    "Subrogation": subro_flag,
                    "Litigation Status": initial_lit_status
                }
                
                st.session_state.claims_db = pd.concat([st.session_state.claims_db, pd.DataFrame([new_record])], ignore_index=True)
                st.success(f"Claim **{new_claim_id}** ingested and triaged via Digital Ingestion Rules!")


# ==========================================================
# MODULE 3: CLAIMS WORK QUEUE & CHILD SCREENS
# ==========================================================
elif nav_module == "👥 Claims Work Queue & Child Modules":
    st.title("Adjudication Workspace & Child Screens")
    st.caption("Select an active claim from the primary queue to inspect its dedicated downstream child modules.")
    
    # Primary Search & Filter Bar
    f1, f2 = st.columns([2, 1])
    with f1:
        lob_filter = st.multiselect("Filter by LOB", options=st.session_state.claims_db["LOB"].unique(), default=st.session_state.claims_db["LOB"].unique())
    with f2:
        claim_selector = st.selectbox("Inspect Active Claim (Child Screen Pivot)", options=st.session_state.claims_db["Claim ID"])

    # Active Queue Table
    filtered_claims = st.session_state.claims_db[st.session_state.claims_db["LOB"].isin(lob_filter)]
    st.dataframe(filtered_claims, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Dedicated Child Screens for Selected Claim
    current_record = st.session_state.claims_db[st.session_state.claims_db["Claim ID"] == claim_selector].iloc[0]
    st.header(f"🗂️ Child Screen: Adjudication File [{claim_selector}]")
    st.caption(f"Insured: **{current_record['Insured Entity']}** | Policy: **{current_record['Policy Number']}** | LOB: **{current_record['LOB']}**")

    child_tab1, child_tab2, child_tab3, child_tab4 = st.tabs([
        "👤 Claimant Record & Injury/Damage",
        "⚖️ Litigation & Legal Hold",
        "🔄 Subrogation & Recovery Triage",
        "💰 Financial Reserves & Loss Ledger"
    ])

    # Child Screen 1: Claimant Details
    with child_tab1:
        st.subheader("Claimant Demographics & Injury/Property Specification")
        cc1, cc2 = st.columns(2)
        with cc1:
            st.text_input("Claimant Full Name", value=current_record["Claimant Name"], disabled=True)
            st.text_input("Claimant Contact / Counsel Phone", value="+1 (555) 234-8901")
            st.selectbox("Claimant Type", ["Primary Third Party", "Employee", "Passenger", "Pedestrian"])
        with cc2:
            st.selectbox("Injury Severity Tier", ["Tier 0: Property Damage Only", "Tier 1: Minor Medical", "Tier 2: Lost Time / Surgery", "Tier 3: Catastrophic"])
            st.text_area("Recorded Medical / Physical Damage Statement", "Initial adjuster interview confirms damage to structural loading gate. Claimant medical report pending.")
        st.button("Update Claimant Record", key="btn_claimant")

    # Child Screen 2: Litigation & Legal Hold
    with child_tab2:
        st.subheader("Litigation Management & Defense Panel Assignment")
        lc1, lc2 = st.columns(2)
        with lc1:
            lit_status = st.selectbox("Legal Stance", ["None", "Pre-Suit Notice", "Summons & Complaint Served", "Discovery", "Mediation / ADR"], index=1 if current_record["Litigation Status"] != "None" else 0)
            outside_counsel = st.selectbox("Assigned Defense Firm", ["None Assigned", "Baker & Hostetler LLP", "Morgan Lewis & Bockius", "In-House Staff Counsel"])
        with lc2:
            st.text_input("Court Docket / Matter Number", "2026-CV-09881" if lit_status != "None" else "N/A")
            st.date_input("Trial / Hearing Deadline", value=datetime.date(2027, 4, 15))
        st.checkbox("Enforce Evidence Spoliation / Legal Hold across records", value=True if lit_status != "None" else False)
        st.button("Save Litigation Status", key="btn_lit")

    # Child Screen 3: Subrogation & Recovery
    with child_tab3:
        st.subheader("Subrogation Identification & Recovery Tracking")
        sc1, sc2 = st.columns(2)
        with sc1:
            sub_identified = st.radio("Third-Party Liability Identified?", ["Yes - Pursuing Recovery", "Under Review", "No Subrogation Potential"], index=0 if current_record["Subrogation"] != "None" else 2)
            adverse_carrier = st.text_input("Adverse Carrier / Third-Party Insurer", "Travelers Commercial Lines" if sub_identified.startswith("Yes") else "None")
        with sc2:
            recovery_target = st.number_input("Target Recovery Amount ($)", value=int(current_record["Total Incurred ($)"] * 0.75) if sub_identified.startswith("Yes") else 0)
            subro_status = st.selectbox("Arbitration / Demand Status", ["Demand Letter Sent", "Inter-Company Arbitration Filed", "Closed / Uncollectible", "Pending Evidence"])
        st.button("Update Subrogation Record", key="btn_subro")

    # Child Screen 4: Financial Reserves
    with child_tab4:
        st.subheader("Loss Reserves & Expense Ledger")
        fc1, fc2, fc3 = st.columns(3)
        indemnity_reserve = int(current_record["Total Incurred ($)"] * 0.8)
        expense_reserve = int(current_record["Total Incurred ($)"] * 0.2)
        
        fc1.metric("Indemnity Reserve", f"${indemnity_reserve:,.0f}")
        fc2.metric("ALAE / Legal Defense Reserve", f"${expense_reserve:,.0f}")
        fc3.metric("Total Incurred", f"${current_record['Total Incurred ($)']:,.0f}")
        
        st.markdown("##### Adjust Reserve Authority (Requires Senior Approver > $50,000)")
        new_adj_reserve = st.number_input("Modify Total Reserve ($)", value=int(current_record["Total Incurred ($)"]), step=5000)
        if st.button("Submit Reserve Revision", key="btn_reserve"):
            idx = st.session_state.claims_db[st.session_state.claims_db["Claim ID"] == claim_selector].index[0]
            st.session_state.claims_db.at[idx, "Total Incurred ($)"] = new_adj_reserve
            st.success(f"Reserve updated to ${new_adj_reserve:,.0f} and audit event recorded.")
            st.rerun()


# ==========================================================
# MODULE 4: ADJUSTER MANAGEMENT & DIRECTORY
# ==========================================================
elif nav_module == "💼 Adjuster Management & Directory":
    st.title("Claims Adjuster Staff Directory & Routing Matrix")
    st.caption("Administer claims routing thresholds, specializations, and caseload caps.")
    
    st.dataframe(st.session_state.adjusters_db, use_container_width=True, hide_index=True)
    
    st.divider()
    st.subheader("Onboard New Adjuster to Roster")
    with st.form("new_adj_form", clear_on_submit=True):
        a1, a2, a3 = st.columns(3)
        with a1:
            new_adj_id = f"ADJ-10{len(st.session_state.adjusters_db) + 1}"
            st.text_input("Assigned Adjuster ID", value=new_adj_id, disabled=True)
            adj_name = st.text_input("Adjuster Name", placeholder="e.g., Sarah Taylor")
        with a2:
            spec = st.selectbox("Primary LOB Specialty", ["GL / Commercial", "WC / Indemnity", "VA / Complex Auto", "Property & Casualty"])
            email = st.text_input("Internal Email", placeholder="staylor@novasure.internal")
        with a3:
            cap = st.number_input("Max Open Caseload Cap", min_value=10, max_value=40, value=25)
        
        if st.form_submit_button("Add Adjuster to Platform"):
            if adj_name and email:
                new_adj_entry = {
                    "Adjuster ID": new_adj_id,
                    "Name": adj_name,
                    "Specialization": spec,
                    "Active Caseload": 0,
                    "Max Capacity": cap,
                    "Email": email
                }
                st.session_state.adjusters_db = pd.concat([st.session_state.adjusters_db, pd.DataFrame([new_adj_entry])], ignore_index=True)
                st.success(f"Adjuster {adj_name} ({new_adj_id}) enrolled in automatic triage routing!")
                st.rerun()