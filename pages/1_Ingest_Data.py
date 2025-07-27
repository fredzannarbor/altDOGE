# pages/1_Ingest_Data.py
import streamlit as st
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)
st.set_page_config(page_title="Ingest Data - AltDOGE", layout="wide")

if "runner" not in st.session_state:
    st.error("Application not initialized. Please return to the main page.")
    st.page_link("run_altDOGE.py", label="Go to Home", icon="🏠")
    st.stop()
runner = st.session_state.runner

if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.error("Please log in to access this page.")
    st.page_link("run_altDOGE.py", label="Go to Login", icon="🏠")
    st.stop()

st.title("Ingest Federal Register Data")
start_date = st.text_input("Start Date (YYYY-MM-DD)", "2025-07-01")
end_date = st.text_input("End Date (YYYY-MM-DD)", "2025-07-31")

# --- Agency Dropdown ---
all_agencies = runner.ingestion_manager.agencies
if all_agencies:
    agency_options = {agency['name']: agency['slug'] for agency in all_agencies}
    agency_names = ["All Agencies"] + list(agency_options.keys())
    selected_agency_name = st.selectbox(
        "Select an Agency (optional)",
        options=agency_names,
        index=0  # Default to "All Agencies"
    )
    agency_slug = agency_options.get(selected_agency_name)
else:
    st.warning("Could not fetch agency list. Please enter agency slug manually.")
    agency_slug = st.text_input("Agency Slug (e.g., securities-and-exchange-commission)", "")

prompt_strategies = runner.ingestion_manager.prompt_strategies.keys()
selected_strategy = st.radio("Select Prompt Strategy", options=list(prompt_strategies))
doc_limit = st.number_input("Document Limit", min_value=1, value=3, help="Max number of documents for LLM analysis.")
llm_call_limit = st.number_input("Total LLM Call Limit", min_value=1, value=4,
                                 help="Max total LLM calls for this session.")

if st.button("Start Ingestion"):
    progress_bar = st.progress(0, text="Starting ingestion...")


    def streamlit_progress_callback(current, total, message):
        if total > 0:
            progress_bar.progress(current / total, text=message)
        else:
            progress_bar.progress(0, text=message)


    result = runner.ingestion_manager.process_federal_register(
        start_date, end_date, agency=agency_slug,
        doc_limit=doc_limit, llm_call_limit=llm_call_limit,
        prompt_strategy_name=selected_strategy,
        progress_callback=streamlit_progress_callback
    )

    if result["status"] == "success":
        st.success(f"Processed {len(result['results'])} documents")
        output_file = runner.output_dir / f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(result["results"], f, indent=2)
        st.write(f"Results saved to {output_file}")
        st.info("You can now view the results on the 'View Ingestion Results' page.")
        st.json(result["results"][:5])
    else:
        st.error(f"Ingestion failed: {result['message']}")
