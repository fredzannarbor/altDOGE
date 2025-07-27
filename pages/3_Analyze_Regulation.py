
import streamlit as st
import logging

logger = logging.getLogger(__name__)
st.set_page_config(page_title="Analyze Regulation - AltDOGE", layout="wide")

if "runner" not in st.session_state:
    st.error("Application not initialized. Please return to the main page.")
    st.page_link("run_altDOGE.py", label="Go to Home", icon="🏠")
    st.stop()
runner = st.session_state.runner

if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.error("Please log in to access this page.")
    st.page_link("run_altDOGE.py", label="Go to Login", icon="🏠")
    st.stop()

st.title("Analyze a Specific Regulation by ID")
prompt_strategies = runner.ingestion_manager.prompt_strategies.keys()
selected_strategy = st.selectbox("Select Prompt Strategy", options=list(prompt_strategies))
reg_id = st.number_input("Regulation ID from Database", min_value=1, step=1)
if st.button("Analyze"):
    with st.spinner(f"Analyzing regulation {reg_id} with '{selected_strategy}' strategy..."):
        result = runner.ingestion_manager.analyze_regulation(reg_id, prompt_strategy_name=selected_strategy)
        if "error" not in result:
            st.success("Analysis complete")
            st.json(result)
        else:
            st.error(f"Analysis failed: {result['error']}")
