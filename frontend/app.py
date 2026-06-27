import streamlit as st
import requests
import os
import json
import time
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="ICP Agent Platform", layout="wide", page_icon="🤖")

st_autorefresh(interval=5000, key="refresh")

st.title("B2B SaaS Agentic Platform")
st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Initialize session state for optimistic UI and balloons
if "optimistic_prospects" not in st.session_state:
    st.session_state.optimistic_prospects = []
if "completed_prospects" not in st.session_state:
    st.session_state.completed_prospects = set()

tab1, tab2, tab3, tab4 = st.tabs(["📋 Prospects", "✋ HITL Requests", "⚙️ Configuration", "📡 Live Logs"])

# ==========================================
# Tab 1: Prospects
# ==========================================
with tab1:
    st.header("Prospect Pipeline")
    
    with st.expander("➕ Add New Prospect", expanded=True):
        with st.form("new_prospect_form"):
            col1, col2 = st.columns(2)
            with col1:
                company_name = st.text_input("Company Name")
            with col2:
                website = st.text_input("Website (Optional)")
            
            simulate_failure = st.checkbox("Simulate Agent Failure (For Demo purposes)")
            
            submit = st.form_submit_button("Submit Prospect")
            if submit and company_name:
                with st.spinner("Submitting..."):
                    payload = {
                        "company_name": company_name,
                        "website": website if website else None,
                        "trigger_event": "manual_submission",
                        "simulate_failure": simulate_failure
                    }
                    try:
                        resp = requests.post(f"{API_URL}/api/prospects", json=payload)
                        if resp.status_code == 200:
                            st.toast(f"Successfully submitted {company_name}", icon="✅")
                            # Add to optimistic UI
                            st.session_state.optimistic_prospects.append({
                                "company_name": company_name,
                                "status": "WORKFLOW STARTING",
                                "confidence_score": 0.0,
                                "updated_at": datetime.now().isoformat()
                            })
                        else:
                            st.error(f"Failed to submit: {resp.text}")
                    except Exception as e:
                        st.error(f"Error submitting prospect: {e}")

    st.subheader("Live Prospect Queue")
    try:
        response = requests.get(f"{API_URL}/api/prospects?limit=50")
        if response.status_code == 200:
            prospects_data = response.json()
            
            # Merge optimistic rows
            fetched_names = {p["company_name"] for p in prospects_data}
            pending_optimistic = [p for p in st.session_state.optimistic_prospects if p["company_name"] not in fetched_names]
            st.session_state.optimistic_prospects = pending_optimistic # keep only those not yet in db
            
            all_prospects = pending_optimistic + prospects_data
            
            if all_prospects:
                for p in all_prospects:
                    status = p.get("status", "UNKNOWN")
                    # Check for completed prospect for balloon effect
                    if status == "COMPLETED" and p.get("id") and p.get("id") not in st.session_state.completed_prospects:
                        st.balloons()
                        st.session_state.completed_prospects.add(p.get("id"))
                    
                    # Highlight completed
                    border_color = "green" if status == "COMPLETED" else "gray"
                    emoji = "✅" if status == "COMPLETED" else "⏳" if status in ["PENDING", "IN_PROGRESS", "WORKFLOW STARTING"] else "⚠️"
                    
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                        c1.markdown(f"**{emoji} {p['company_name']}**")
                        c2.write(status)
                        c3.write(f"Updated: {p['updated_at'][:19].replace('T', ' ')}")
            else:
                st.info("No prospects in the pipeline yet.")
        else:
            st.error("Failed to fetch prospects from backend.")
    except Exception as e:
        st.error(f"Error connecting to backend: {e}")

# ==========================================
# Tab 2: HITL Requests
# ==========================================
with tab2:
    st.header("Human-in-the-Loop Pending Approvals")
    try:
        response = requests.get(f"{API_URL}/api/hitl/pending")
        if response.status_code == 200:
            requests_data = response.json()
            if not requests_data:
                st.info("No pending HITL requests.")
            for req in requests_data:
                with st.container(border=True):
                    st.markdown(f"### Prospect ID: {req.get('prospect_id', 'Unknown')}")
                    st.write(f"**Reason:** {req.get('summary', 'No summary provided')}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Approve", key=f"app_{req['id']}", use_container_width=True, type="primary"):
                            try:
                                r = requests.post(f"{API_URL}/api/hitl/{req['id']}/approve")
                                if r.status_code == 200:
                                    st.toast("Request Approved!", icon="✅")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("Approval failed.")
                            except Exception as e:
                                st.error(f"Error: {e}")
                    with c2:
                        if st.button("Reject", key=f"rej_{req['id']}", use_container_width=True):
                            try:
                                r = requests.post(f"{API_URL}/api/hitl/{req['id']}/reject")
                                if r.status_code == 200:
                                    st.toast("Request Rejected!", icon="🛑")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("Rejection failed.")
                            except Exception as e:
                                st.error(f"Error: {e}")
        else:
            st.error("Failed to load HITL requests")
    except Exception as e:
        st.error(f"Error: {e}")

# ==========================================
# Tab 3: Configuration
# ==========================================
with tab3:
    st.header("Platform Configuration")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("Reset to Defaults", type="primary"):
            try:
                r = requests.post(f"{API_URL}/api/config/reset")
                if r.status_code == 200:
                    st.toast("Configuration reset to defaults!", icon="🔄")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Failed to reset config.")
            except Exception as e:
                st.error(f"Error: {e}")

    try:
        icp_resp = requests.get(f"{API_URL}/api/config/icp")
        persona_resp = requests.get(f"{API_URL}/api/config/persona")
        thresh_resp = requests.get(f"{API_URL}/api/config/thresholds")
        
        if icp_resp.status_code == 200 and persona_resp.status_code == 200 and thresh_resp.status_code == 200:
            icp = icp_resp.json()
            persona = persona_resp.json()
            thresh = thresh_resp.json()
            
            with st.form("config_form"):
                st.subheader("ICP Criteria")
                industries = st.text_input("Industries (comma separated)", value=", ".join(icp.get("industries", [])))
                tech_stack = st.text_area("Tech Stack Keywords (one per line or comma separated)", value=", ".join(icp.get("tech_stack", [])))
                
                st.subheader("Target Personas")
                job_titles = st.text_area("Job Titles (comma separated)", value=", ".join(persona.get("job_titles", [])))
                
                st.subheader("Thresholds")
                c1, c2 = st.columns(2)
                with c1:
                    min_confidence = st.number_input("Min Confidence (%)", min_value=0.0, max_value=100.0, value=float(thresh.get("min_confidence_score", 50.0)))
                with c2:
                    hitl_confidence = st.number_input("HITL Threshold (%)", min_value=0.0, max_value=100.0, value=float(thresh.get("hitl_confidence_threshold", 70.0)))
                
                if st.form_submit_button("Update Configuration"):
                    with st.spinner("Saving..."):
                        # Process lists
                        new_icp = icp.copy()
                        new_icp["industries"] = [i.strip() for i in industries.split(",") if i.strip()]
                        new_icp["tech_stack"] = [t.strip() for t in tech_stack.replace("\n", ",").split(",") if t.strip()]
                        
                        new_persona = persona.copy()
                        new_persona["job_titles"] = [j.strip() for j in job_titles.replace("\n", ",").split(",") if j.strip()]
                        
                        new_thresh = thresh.copy()
                        new_thresh["min_confidence_score"] = min_confidence
                        new_thresh["hitl_confidence_threshold"] = hitl_confidence
                        
                        # API Calls
                        r1 = requests.put(f"{API_URL}/api/config/icp", json=new_icp)
                        r2 = requests.put(f"{API_URL}/api/config/persona", json=new_persona)
                        r3 = requests.put(f"{API_URL}/api/config/thresholds", json=new_thresh)
                        
                        if r1.status_code == 200 and r2.status_code == 200 and r3.status_code == 200:
                            st.toast("Configuration updated successfully!", icon="✅")
                        else:
                            st.error("Failed to update one or more configurations.")
        else:
            st.error("Could not fetch current configuration from backend.")
    except Exception as e:
        st.error(f"Error connecting to backend: {e}")

# ==========================================
# Tab 4: Live Logs
# ==========================================
with tab4:
    st.header("Live Agent Logs")
    st.write("Real-time stream of agent events across the system.")
    
    try:
        response = requests.get(f"{API_URL}/api/events")
        if response.status_code == 200:
            events_data = response.json().get("events", [])
            
            if not events_data:
                st.info("No events yet.")
            else:
                with st.container(height=600):
                    for evt in events_data:
                        evt_time = datetime.fromtimestamp(evt.get("time", time.time())).strftime('%H:%M:%S')
                        evt_type = evt.get("type", "UNKNOWN")
                        payload = evt.get("payload", {})
                        
                        # Formatting based on event type
                        if "FAILED" in evt_type or "ERROR" in evt_type:
                            color = "red"
                        elif "SUCCESS" in evt_type or "COMPLETED" in evt_type:
                            color = "green"
                        else:
                            color = "blue"
                            
                        st.markdown(f"**[{evt_time}]** :{color}[{evt_type}]")
                        with st.expander("View Payload"):
                            st.json(payload)
                        st.divider()
        else:
            st.error("Failed to fetch events from backend.")
    except Exception as e:
        st.error(f"Error connecting to backend: {e}")

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Built for the ICP Discovery Hackathon | Powered by LangGraph & FastAPI</p>", unsafe_allow_html=True)
