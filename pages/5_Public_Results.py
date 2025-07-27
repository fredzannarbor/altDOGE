
import streamlit as st
import pandas as pd
import logging
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)
st.set_page_config(page_title="Public Results - AltDOGE", layout="wide")

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
OUTPUT_DIR = PROJECT_ROOT / "output"

@st.cache_data
def load_all_results(output_dir: Path) -> pd.DataFrame:
    all_results = []
    if not output_dir.exists():
        logger.warning(f"Output directory does not exist: {output_dir}")
        return pd.DataFrame()
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

st.title("Public Dashboard: Summary of All Analyses")
st.info("This page displays a cached summary of all previously completed regulation analyses.")
raw_df = load_all_results(OUTPUT_DIR)

if raw_df.empty:
    st.warning("No result files found. Analysis may not have been run yet.")
    st.stop()

unique_df = raw_df.drop_duplicates(subset=['document_number'], keep='last').copy()
processed_df = create_summary_dataframe(unique_df)

st.subheader("Summary by Regulation")

if not processed_df.empty:
    st.metric("Unique Regulations Analyzed", len(unique_df))
    st.write("#### Recommended Actions Breakdown")
    action_counts = processed_df['Recommended Action'].value_counts()
    st.bar_chart(action_counts)
    st.dataframe(processed_df, use_container_width=True, hide_index=True)
else:
    st.info("Could not process results into a summary view.")
