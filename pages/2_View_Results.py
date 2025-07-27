
import streamlit as st
import logging
import json
import os

logger = logging.getLogger(__name__)
st.set_page_config(page_title="View Results - AltDOGE", layout="wide")

if "runner" not in st.session_state:
    st.error("Application not initialized. Please return to the main page.")
    st.page_link("run_altDOGE.py", label="Go to Home", icon="🏠")
    st.stop()
runner = st.session_state.runner

if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.error("Please log in to access this page.")
    st.page_link("run_altDOGE.py", label="Go to Login", icon="🏠")
    st.stop()

st.header("View Ingestion Results")
try:
    result_files = sorted(runner.output_dir.glob("analysis_results_*.json"), key=os.path.getmtime, reverse=True)
    if not result_files:
        st.warning("No result files found. Please run an ingestion first.")
    else:
        selected_file = st.selectbox("Select a result file to view:", options=result_files, format_func=lambda p: p.name)
        if selected_file:
            with open(selected_file, "r", encoding='utf-8') as f:
                results_data = json.load(f)
            st.write(f"Displaying results from `{selected_file.name}`")
            st.write(f"Total documents analyzed: {len(results_data)}")
            for doc_result in results_data:
                title = doc_result.get('title', 'No Title Provided')
                doc_num = doc_result.get('document_number', 'Unknown Document')
                with st.expander(f"**{doc_num}**: {title}"):
                    st.write(f"**Agency:** {doc_result.get('agency', 'N/A')}")
                    st.subheader("Analyses:")
                    for analysis in doc_result.get('analyses', []):
                        st.markdown(f"**Prompt:** `{analysis.get('prompt')}`")
                        st.markdown(analysis.get('result'))
                        st.markdown("---")
except Exception as e:
    st.error(f"An error occurred while reading result files: {e}")
    logger.error(f"Error reading result files: {e}", exc_info=True)
