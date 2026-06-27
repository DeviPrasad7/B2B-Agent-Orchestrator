import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="ICP Agent Platform", layout="wide")

st.title("B2B SaaS Agentic Platform")

tab1, tab2, tab3 = st.tabs(["Prospects", "HITL Approvals", "Configuration"])

with tab1:
    st.header("Prospect Pipeline")
    if st.button("Refresh Prospects"):
        try:
            response = requests.get(f"{API_URL}/api/prospects/")
            if response.status_code == 200:
                prospects = response.json()
                st.table(prospects)
            else:
                st.error("Failed to load prospects")
        except Exception as e:
            st.error(f"Error: {e}")

with tab2:
    st.header("Human-in-the-Loop Requests")
    if st.button("Refresh HITL"):
        try:
            response = requests.get(f"{API_URL}/api/hitl/pending")
            if response.status_code == 200:
                requests_data = response.json()
                if not requests_data:
                    st.info("No pending requests.")
                for req in requests_data:
                    st.write(f"**Prospect ID:** {req['prospect_id']}")
                    st.write(f"**Summary:** {req['summary']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Approve", key=f"approve_{req['id']}"):
                            requests.post(f"{API_URL}/api/hitl/{req['id']}/resolve", json={"decision": "APPROVED", "corrections": {}})
                            st.success("Approved!")
                    with col2:
                        if st.button("Reject", key=f"reject_{req['id']}"):
                            requests.post(f"{API_URL}/api/hitl/{req['id']}/resolve", json={"decision": "REJECTED", "corrections": {}})
                            st.error("Rejected!")
            else:
                st.error("Failed to load HITL requests")
        except Exception as e:
            st.error(f"Error: {e}")

with tab3:
    st.header("Platform Configuration")
    st.write("Manage your Ideal Customer Profile and Rules here.")
    st.info("Configuration API endpoints are available but UI management is coming soon in Phase 4.")
