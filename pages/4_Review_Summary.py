
import streamlit as st
import pandas as pd
import logging
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)
st.set_page_config(page_title="Review Summary - AltDOGE", layout="wide")

@st.cache_data
def load_all_results(output_dir: Path) -> pd.DataFrame:
    all_results = []
    result_files = sorted(output_dir.glob("analysis_results_*.json"), key=os.path.getmtime, reverse=True)
    for file_path in result_files:
        try:
            with open(file_path, "r", encoding='utf-8') as f:
                data = json.load(f)
                all_results.extend(data)
        except Exception as e:
            logger.error(f"Could not read file {file_path}: {e}")
    return pd.DataFrame(all_results) if all_results else pd.DataFrame()

def create_summary_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    processed_rows = []
    for _, row in df.iterrows():
        meta_analysis = row.get('meta_analysis', {})
        if not isinstance(meta_analysis, dict):
            meta_analysis = {}
        bullet_summary_list = meta_analysis.get('bullet_summary', [])
        if isinstance(bullet_summary_list, list):
            bullet_summary = "\n".join(f"- {item}" for item in bullet_summary_list)
        else:
            bullet_summary = "Summary not available."
        new_row = {
            'document_number': row.get('document_number'),
            'title': row.get('title'),
            'agency': row.get('agency'),
            'Strategy': row.get('prompt_strategy_name', 'Unknown'),
            'Recommended Action': meta_analysis.get('recommended_action', 'N/A'),
            'Goal Alignment': meta_analysis.get('goal_alignment', 'N/A'),
            'Summary': bullet_summary
        }
        processed_rows.append(new_row)
    return pd.DataFrame(processed_rows)

if "runner" not in st.session_state:
    st.error("Application not initialized. Please return to the main page.")
    st.page_link("run_altDOGE.py", label="Go to Home", icon="🏠")
    st.stop()
runner = st.session_state.runner

if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.error("Please log in to access this page.")
    st.page_link("run_altDOGE.py", label="Go to Login", icon="🏠")
    st.stop()

st.title("Review Summary of All Ingestions")
raw_df = load_all_results(runner.output_dir)

if raw_df.empty:
    st.warning("No result files found in the output directory. Please run an ingestion first.")
    st.stop()

total_results = len(raw_df)
unique_df = raw_df.drop_duplicates(subset=['document_number'], keep='last').copy()
unique_results = len(unique_df)

st.metric("Total Results Analyzed (All Runs)", total_results)
st.metric("Unique Regulations Analyzed", unique_results)

processed_df = create_summary_dataframe(unique_df)

st.subheader("Summary by Regulation")

if not processed_df.empty:
    st.write("### Recommended Actions Breakdown")
    action_counts = processed_df['Recommended Action'].value_counts()
    st.bar_chart(action_counts)
    st.dataframe(
        processed_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Recommended Action": st.column_config.TextColumn(width="medium"),
            "Goal Alignment": st.column_config.TextColumn(width="medium"),
            "Summary": st.column_config.TextColumn(width="large")
        }
    )
else:
    st.info("Could not process results into a summary view.")
