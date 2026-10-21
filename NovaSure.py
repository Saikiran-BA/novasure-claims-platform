import datetime as dt
from decimal import Decimal
import pandas as pd
import streamlit as st
import database as db

st.set_page_config(page_title='NovaSure Claims Platform',page_icon='NS',layout='wide',initial_sidebar_state='expanded')
LOBS=['GL','WC','VA','PD']; STATUSES=['New','Open','Pending','Litigation','Closed','Denied']; PRIORITIES=['Low','Medium','High','Critical']; STATES=['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']; ROLES=['Claims Admin','Lead Systems Analyst','Senior Claims Adjuster','Claims Triage Specialist','Legal Counsel Liaison','Compliance Auditor']; ETYPES=['Insured Corporation','Medical Provider / Clinic','Defense Law Firm','Subcontractor','Third-Party Adverse Carrier']; DCLASSES=['Legal','Medical','Evidence','Financial','Policy','Compliance','Adjuster Notes']; DTYPES=['PDF','Image','Spreadsheet','Word Doc','Notice','Text']
st.markdown('''<style>.stApp{background:#f5f8fc}.nslogo{display:flex;align-items:center;gap:14px}.shield{width:68px;height:68px;border:3px solid #ff4b4b;border-radius:18px 18px 27px 27px;background:#103b63;color:white!important;display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:800}.brand{font-size:34px;font-weight:800;color:#103b63!important}.tag{color:#d62f3c!important;font-size:11px;font-weight:800;letter-spacing:2px}[data-testid="stSidebar"]{background:#0b1f35}[data-testid="stSidebar"] *{color:#f7fbff!important}@media(prefers-color-scheme:dark){.stApp{background:#0e1621;color:#edf4fb}.brand{color:#f3f8fd!important}[data-testid="stAppViewContainer"] label,[data-testid="stAppViewContainer"] p,[data-testid="stAppViewContainer"] h1,[data-testid="stAppViewContainer"] h2,[data-testid="stAppViewContainer"] h3{color:#edf4fb!important}[data-baseweb="input"] input,[data-baseweb="textarea"] textarea{color:#fff!important;-webkit-text-fill-color:#fff!important}}</style>''',unsafe_allow_html=True)
db.init_db()
for k,v in {'auth':False,'user':None}.items(): st.session_state.setdefault(k,v)

def login():
    _,c,_=st.columns([1,1.2,1])
    with c:
        st.markdown('<div class="nslogo"><div class="shield">NS</div><div><div class="brand">NovaSure</div><div class="tag">CLAIMS PLATFORM</div></div></div>',unsafe_allow_html=True)
        st.caption('Claims Platform | Secure Enterprise Access')
        with st.form('login'):
            u=st.text_input('Username'); p=st.text_input('Password',type='password'); go=st.form_submit_button('Sign in to NovaSure',use_container_width=True,type='primary')
        if go:
            x=db.validate_login(u,p)
            if x: st.session_state.auth=True; st.session_state.user=x; db.audit(x['id'],'LOGIN','SESSION',None,'Successful login'); st.rerun()
            else: st.error('Invalid credentials or inactive account.')
        st.info('Initial login: admin / pass123')

def new_claim():
    st.subheader('New Claim')
    with st.form('claim',clear_on_submit=True):
        st.markdown('#### Section 1: Policy & Classification'); a,b,c=st.columns(3); pol=a.text_input('Policy Number *'); ins=b.text_input('Insured Entity *'); lob=c.selectbox('LOB',LOBS); a,b,c=st.columns(3); ct=a.text_input('Claim Type *'); state=b.selectbox('Jurisdiction',STATES); pri=c.selectbox('Priority',PRIORITIES,index=1)
        st.markdown('#### Section 2: Claimant & Exposure Details'); a,b,c=st.columns(3); claimant=a.text_input('Claimant Name *'); email=b.text_input('Email'); phone=c.text_input('Phone'); a,b,c=st.columns(3); incident=a.date_input('Incident Date'); reported=b.date_input('Reported Date'); reserve=c.number_input('Incurred Reserve ($)',min_value=0.0); location=st.text_input('Incident Location')
        st.markdown('#### Section 3: Incident Narrative'); narrative=st.text_area('Narrative *'); submit=st.form_submit_button('Create Claim',type='primary')
    if submit:
        if not all(x.strip() for x in [pol,ins,ct,claimant,narrative]): st.error('Complete required fields.')
        elif reported<incident: st.error('Reported date cannot precede incident date.')
        else:
            adj=db.adjusters(); aid=adj[0]['id'] if adj else None; i,num=db.create_claim(dict(policy_number=pol,insured_entity=ins,claimant_name=claimant,claimant_email=email,claimant_phone=phone,lob=lob,claim_type=ct,jurisdiction_state=state,incident_date=incident,reported_date=reported,priority=pri,incident_location=location,incident_narrative=narrative,incurred_reserve=reserve,assigned_adjuster_id=aid),st.session_state.user['id']); db.audit(st.session_state.user['id'],'CREATE','CLAIM',i,num); st.success(f'Created {num}')

def claims():
    st.header('Claims Zone'); tab=st.radio('Workspace',['New Claim','Recent Claims','Search','Bulk Upload','Attachments'],horizontal=True)
    if tab=='New Claim': new_claim()
    elif tab=='Recent Claims':
        r=db.recent()
        if r:
            st.dataframe(pd.DataFrame(r),use_container_width=True,hide_index=True)
        else:
            st.info('No claims yet. Use New Claim or Bulk Upload.')
    elif tab=='Search':
        q=st.text_input('Quick Search')
        a,b,c,d=st.columns(4); lob=a.selectbox('LOB',['All']+LOBS); status=b.selectbox('Status',['All']+STATUSES); state=c.selectbox('State',['All']+STATES); pri=d.selectbox('Priority',['All']+PRIORITIES)
        a,b=st.columns(2); lo=a.number_input('Minimum Reserve',0.0); hi=b.number_input('Maximum Reserve',0.0,999999999.0)
        r=db.search(q,lob,status,state,pri,lo,hi)
        if r:
            st.dataframe(pd.DataFrame(r),use_container_width=True,hide_index=True)
        else:
            st.info('No matches.')
    elif tab=='Bulk Upload':
        cols=['policy_number','insured_entity','claimant_name','claimant_email','claimant_phone','lob','claim_type','jurisdiction_state','incident_date','reported_date','priority','incident_location','incident_narrative','incurred_reserve']; sample=pd.DataFrame([['POL-10001','Acme Logistics','Jordan Lee','j@example.com','555-0101','GL','Bodily Injury','TX','2026-01-10','2026-01-11','High','Dallas','Slip and fall',25000]],columns=cols); st.download_button('Download FNOL Template',sample.to_csv(index=False).encode(),'novasure_fnol_template.csv','text/csv'); f=st.file_uploader('Upload FNOL CSV',type='csv')
        if f:
            df=pd.read_csv(f); st.dataframe(df.head(20),use_container_width=True)
            if st.button('Import Claims',type='primary'):
                ok=0; errors=[]
                for idx,row in df.iterrows():
                    try:
                        adj=db.adjusters(); d=row.to_dict(); d['incident_date']=pd.to_datetime(d['incident_date']).date(); d['reported_date']=pd.to_datetime(d['reported_date']).date(); d['assigned_adjuster_id']=adj[0]['id'] if adj else None; db.create_claim(d,st.session_state.user['id']); ok+=1
                    except Exception as e: errors.append(f'Row {idx+2}: {e}')
                st.success(f'Imported {ok} claims');
                if errors: st.code('\n'.join(errors[:30]))
    else:
        r=db.recent(500)
        if not r: st.info('Create a claim before uploading attachments.')
        else:
            cmap={x['claim_number']:x['id'] for x in r}; up,work=st.tabs(['Upload','Workbench'])
            with up:
                with st.form('up',clear_on_submit=True):
                    title=st.text_input('Title *'); a,b,c=st.columns(3); dc=a.selectbox('Class',DCLASSES); dtp=b.selectbox('Type',DTYPES); lob=c.selectbox('LOB',LOBS); a,b=st.columns(2); ct=a.text_input('Claim Type *'); cn=b.selectbox('Claim ID',list(cmap)); file=st.file_uploader('File'); submit=st.form_submit_button('Upload')
                if submit and file and title and ct: db.save_attachment(dict(title=title,document_class=dc,document_type=dtp,lob=lob,claim_type=ct,claim_id=cmap[cn]),file.name,file.type or 'application/octet-stream',file.getvalue(),st.session_state.user['id']); st.success('Uploaded')
            with work:
                items=db.attachments()
                if items:
                    st.dataframe(pd.DataFrame(items),use_container_width=True,hide_index=True)
                else:
                    st.info('No attachments.')
                if items:
                    aid=st.selectbox('Attachment ID',[x['id'] for x in items]); x=db.attachment(aid); st.download_button('Download',x['file_bytes'],x['file_name'],x['mime_type']); status=st.selectbox('Verification',['Unverified','Verified','Rejected']); notes=st.text_area('Adjuster Notes',x.get('adjuster_notes') or '')
                    if st.button('Update Metadata'): db.update_attachment(aid,status,notes); st.success('Updated')

def maintenance():
    st.header('Maintenance Zone'); create,search=st.tabs(['Entities Management','Search Criteria'])
    with create:
        with st.form('entity',clear_on_submit=True):
            name=st.text_input('Entity Name *'); typ=st.selectbox('Type',ETYPES); a,b,c=st.columns(3); contact=a.text_input('Contact'); email=b.text_input('Email'); phone=c.text_input('Phone'); address=st.text_input('Address'); submit=st.form_submit_button('Create Entity')
        if submit and name: db.create_entity(dict(entity_name=name,entity_type=typ,contact_name=contact,email=email,phone=phone,address=address),st.session_state.user['id']); st.success('Entity created')
    with search:
        a,b=st.columns(2); q=a.text_input('Keyword'); t=b.selectbox('Classification',['All']+ETYPES)
        r=db.entities(q,t)
        if r:
            st.dataframe(pd.DataFrame(r),use_container_width=True,hide_index=True)
        else:
            st.info('No entities.')

def security():
    st.header('Security Zone')
    if st.session_state.user['role'] not in ['Claims Admin','Lead Systems Analyst']: st.warning('Admin access required.'); return
    with st.form('usr',clear_on_submit=True):
        a,b=st.columns(2); u=a.text_input('Username *'); n=b.text_input('Display Name *'); a,b,c=st.columns(3); p=a.text_input('Temporary Password *',type='password'); r=b.selectbox('Role',ROLES); limit=c.number_input('Reserve Authority',min_value=0.0); submit=st.form_submit_button('Create User')
    if submit:
        try: db.create_user(u,n,p,r,Decimal(str(limit))); st.success('User created and can log in.')
        except ValueError as e: st.error(str(e))
    us=db.users(); st.dataframe(pd.DataFrame(us),use_container_width=True,hide_index=True)
    labels={f"{x['display_name']} ({x['username']})":x for x in us}; label=st.selectbox('Manage User',list(labels)); active=st.checkbox('Active',value=bool(labels[label]['is_active']))
    if st.button('Update User Status'):
        if labels[label]['id']==st.session_state.user['id'] and not active: st.error('Cannot deactivate current account.')
        else: db.set_active(labels[label]['id'],active); st.success('Status updated')

def dashboard():
    st.header('Dashboard Zone'); k=db.kpis(); a,b,c,d=st.columns(4); a.metric('Total Claims',k['total_claims']); b.metric('Reserve Exposure',f"${k['reserve']:,.2f}"); c.metric('Unique Insureds',k['insureds']); d.metric('Active Users',k['active_users']); left,right=st.columns(2)
    with left:
        st.subheader('Distribution by LOB'); r=db.by_lob()
        if r:
            st.bar_chart(pd.DataFrame(r).set_index('lob')['claim_count'])
        else:
            st.info('No claims.')
    with right:
        st.subheader('Adjuster Caseload'); r=db.adjusters()
        if r:
            st.bar_chart(pd.DataFrame(r).set_index('display_name')['active_cases'])
        else:
            st.info('No adjusters.')
    st.info('Dashboard metrics are calculated from the local SQLite records.')

def app():
    u=st.session_state.user
    with st.sidebar:
        st.markdown('## NovaSure Suite'); st.success(f"Signed in as {u['display_name']}"); st.caption(f"Role: {u['role']}"); zone=st.radio('Application Zones',['Dashboard Zone','Claims Zone','Maintenance Zone','Security Zone']); st.divider(); k=db.kpis(); st.caption(f"Claims: {k['total_claims']} | Attachments: {k['total_docs']} | Entities: {k['total_entities']}")
        if st.button('Logout'): db.audit(u['id'],'LOGOUT','SESSION',None,'Logout'); st.session_state.auth=False; st.session_state.user=None; st.rerun()
    {'Dashboard Zone':dashboard,'Claims Zone':claims,'Maintenance Zone':maintenance,'Security Zone':security}[zone]()

login() if not st.session_state.auth else app()
