"""
Streamlit web interface for CFR Document Analyzer.

Provides a user-friendly web interface for document analysis and results viewing.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import time
from typing import Dict, List, Optional, Any

from .database import Database
from .analysis_engine import AnalysisEngine
from .statistics_engine import StatisticsEngine
from .session_manager import SessionManager
from .progress_tracker import ProgressTracker, WebProgressCallback, ProgressStage
from .models import SessionStatus
from .config import Config


# Page configuration
st.set_page_config(
    page_title="CFR Document Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .status-running {
        color: #ff7f0e;
    }
    .status-completed {
        color: #2ca02c;
    }
    .status-failed {
        color: #d62728;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_database():
    """Get cached database connection."""
    return Database(Config.DATABASE_PATH)


@st.cache_resource
def get_analysis_engine():
    """Get cached analysis engine."""
    db = get_database()
    return AnalysisEngine(db)


@st.cache_resource
def get_statistics_engine():
    """Get cached statistics engine."""
    db = get_database()
    return StatisticsEngine(db)


@st.cache_resource
def get_session_manager():
    """Get cached session manager."""
    db = get_database()
    return SessionManager(db)


def main():
    """Main Streamlit application."""
    st.markdown('<h1 class="main-header">CFR Document Analyzer</h1>', unsafe_allow_html=True)
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["🏠 Dashboard", "🔍 New Analysis", "📊 Results", "📈 Statistics", "⚙️ Settings"]
    )
    
    # Route to appropriate page
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "🔍 New Analysis":
        show_new_analysis()
    elif page == "📊 Results":
        show_results()
    elif page == "📈 Statistics":
        show_statistics()
    elif page == "⚙️ Settings":
        show_settings()


def show_dashboard():
    """Show dashboard with overview statistics."""
    st.header("Dashboard")
    
    try:
        stats_engine = get_statistics_engine()
        session_manager = get_session_manager()
        
        # Get overall statistics
        overall_stats = stats_engine.get_overall_statistics()
        
        # Display key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total Documents Analyzed",
                value=f"{overall_stats.total_documents:,}",
                delta=None
            )
        
        with col2:
            st.metric(
                label="Total Sessions",
                value=f"{overall_stats.total_sessions:,}",
                delta=None
            )
        
        with col3:
            st.metric(
                label="Success Rate",
                value=f"{overall_stats.success_rate:.1f}%",
                delta=None
            )
        
        with col4:
            st.metric(
                label="Avg Processing Time",
                value=f"{overall_stats.average_processing_time:.1f}s",
                delta=None
            )
        
        # Recent sessions
        st.subheader("Recent Sessions")
        recent_sessions = session_manager.list_sessions(limit=10)
        
        if recent_sessions:
            session_data = []
            for session in recent_sessions:
                status_class = f"status-{session.status.value}"
                session_data.append({
                    "Session ID": session.session_id,
                    "Agencies": ", ".join(session.agency_slugs),
                    "Strategy": session.prompt_strategy,
                    "Status": session.status.value.title(),
                    "Progress": f"{session.documents_processed}/{session.total_documents}",
                    "Created": session.created_at.strftime("%Y-%m-%d %H:%M") if session.created_at else "Unknown"
                })
            
            df = pd.DataFrame(session_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No sessions found. Create your first analysis!")
        
        # Category distribution chart
        if overall_stats.category_distribution:
            st.subheader("Document Categories")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Pie chart
                fig = px.pie(
                    values=list(overall_stats.category_distribution.values()),
                    names=list(overall_stats.category_distribution.keys()),
                    title="Distribution of Document Categories"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Category breakdown
                st.write("**Category Breakdown:**")
                for category, count in overall_stats.category_distribution.items():
                    percentage = (count / overall_stats.total_documents) * 100
                    st.write(f"• **{category}**: {count:,} ({percentage:.1f}%)")
        
        # Top agencies chart
        if overall_stats.agency_distribution:
            st.subheader("Top Agencies by Document Count")
            
            # Take top 10 agencies
            top_agencies = dict(list(overall_stats.agency_distribution.items())[:10])
            
            fig = px.bar(
                x=list(top_agencies.values()),
                y=list(top_agencies.keys()),
                orientation='h',
                title="Documents Analyzed by Agency",
                labels={'x': 'Number of Documents', 'y': 'Agency'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")


def show_new_analysis():
    """Show new analysis creation interface."""
    st.header("New Analysis")
    
    with st.form("new_analysis_form"):
        st.subheader("Analysis Configuration")
        
        # Agency selection
        agency_input_method = st.radio(
            "How would you like to specify agencies?",
            ["Single Agency", "Multiple Agencies", "Upload CSV"]
        )
        
        agencies = []
        
        if agency_input_method == "Single Agency":
            agency = st.text_input(
                "Agency Slug",
                placeholder="e.g., national-credit-union-administration",
                help="Enter the Federal Register agency slug"
            )
            if agency:
                agencies = [agency.strip()]
        
        elif agency_input_method == "Multiple Agencies":
            agency_text = st.text_area(
                "Agency Slugs (one per line)",
                placeholder="national-credit-union-administration\nfarm-credit-administration\narctic-research-commission",
                help="Enter one agency slug per line"
            )
            if agency_text:
                agencies = [line.strip() for line in agency_text.split('\n') if line.strip()]
        
        else:  # Upload CSV
            uploaded_file = st.file_uploader(
                "Upload CSV file with agencies",
                type=['csv'],
                help="CSV must contain 'agency_slug' column"
            )
            if uploaded_file:
                try:
                    df = pd.read_csv(uploaded_file)
                    if 'agency_slug' in df.columns:
                        agencies = df['agency_slug'].dropna().tolist()
                        st.success(f"Loaded {len(agencies)} agencies from CSV")
                        st.dataframe(df.head())
                    else:
                        st.error("CSV must contain 'agency_slug' column")
                except Exception as e:
                    st.error(f"Error reading CSV: {e}")
        
        # Analysis parameters
        col1, col2 = st.columns(2)
        
        with col1:
            prompt_strategy = st.selectbox(
                "Analysis Strategy",
                ["DOGE Criteria", "Blue Dreams", "EO 14219", "Technical Competence"],
                help="Choose the analysis framework to use"
            )
        
        with col2:
            document_limit = st.number_input(
                "Document Limit",
                min_value=1,
                max_value=1000,
                value=10,
                help="Maximum number of documents to analyze per agency"
            )
        
        # Advanced options
        with st.expander("Advanced Options"):
            enable_meta_analysis = st.checkbox(
                "Enable Meta-Analysis",
                value=True,
                help="Perform meta-analysis after document analysis"
            )
            
            enable_progress_tracking = st.checkbox(
                "Enable Progress Tracking",
                value=True,
                help="Show real-time progress updates"
            )
        
        # Submit button
        submitted = st.form_submit_button("Start Analysis", type="primary")
        
        if submitted:
            if not agencies:
                st.error("Please specify at least one agency")
                return
            
            try:
                # Create session
                session_manager = get_session_manager()
                session = session_manager.create_session(
                    agency_slugs=agencies,
                    prompt_strategy=prompt_strategy,
                    document_limit=document_limit,
                    session_config={
                        'enable_meta_analysis': enable_meta_analysis,
                        'enable_progress_tracking': enable_progress_tracking
                    }
                )
                
                st.success(f"Analysis session created: {session.session_id}")
                
                # Store session ID in session state for progress tracking
                st.session_state.current_session_id = session.session_id
                st.session_state.show_progress = True
                
                # Start analysis in background (this would need to be implemented with threading)
                st.info("Analysis started! Check the progress below or visit the Results page.")
                
                # Show progress tracking
                if enable_progress_tracking:
                    show_analysis_progress(session.session_id)
                
            except Exception as e:
                st.error(f"Failed to start analysis: {e}")


def show_analysis_progress(session_id: str):
    """Show real-time analysis progress."""
    st.subheader("Analysis Progress")
    
    # Create progress containers
    progress_bar = st.progress(0)
    status_text = st.empty()
    details_container = st.empty()
    
    # This would need to be implemented with WebSocket or polling
    # For now, show a placeholder
    with st.spinner("Analysis in progress..."):
        # Simulate progress updates
        for i in range(101):
            progress_bar.progress(i)
            status_text.text(f"Processing... {i}%")
            time.sleep(0.1)  # This is just for demo
        
        st.success("Analysis completed!")


def show_results():
    """Show analysis results interface."""
    st.header("Analysis Results")
    
    try:
        session_manager = get_session_manager()
        analysis_engine = get_analysis_engine()
        
        # Session selection
        sessions = session_manager.list_sessions(limit=50)
        
        if not sessions:
            st.info("No analysis sessions found. Create your first analysis!")
            return
        
        # Create session options
        session_options = {}
        for session in sessions:
            agencies_str = ", ".join(session.agency_slugs)
            created_str = session.created_at.strftime("%Y-%m-%d %H:%M") if session.created_at else "Unknown"
            label = f"{session.session_id} - {agencies_str} ({created_str})"
            session_options[label] = session.session_id
        
        selected_session_label = st.selectbox(
            "Select Session",
            options=list(session_options.keys()),
            help="Choose an analysis session to view results"
        )
        
        if selected_session_label:
            session_id = session_options[selected_session_label]
            session = session_manager.get_session(session_id)
            
            if not session:
                st.error("Session not found")
                return
            
            # Session info
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Status", session.status.value.title())
            
            with col2:
                st.metric("Documents Processed", f"{session.documents_processed}/{session.total_documents}")
            
            with col3:
                st.metric("Strategy", session.prompt_strategy)
            
            with col4:
                progress = session.progress_percentage
                st.metric("Progress", f"{progress:.1f}%")
            
            # Get analysis results
            results = analysis_engine.get_analysis_results(session_id)
            
            if results:
                st.subheader(f"Analysis Results ({len(results)} documents)")
                
                # Results summary
                categories = {}
                for result in results:
                    category = result.get('analysis', {}).get('category', 'UNKNOWN')
                    categories[category] = categories.get(category, 0) + 1
                
                # Category distribution
                if categories:
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.write("**Category Distribution:**")
                        for category, count in categories.items():
                            percentage = (count / len(results)) * 100
                            st.write(f"• **{category}**: {count} ({percentage:.1f}%)")
                    
                    with col2:
                        fig = px.pie(
                            values=list(categories.values()),
                            names=list(categories.keys()),
                            title="Document Categories"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                # Detailed results table
                st.subheader("Detailed Results")
                
                # Prepare data for table
                table_data = []
                for result in results:
                    analysis = result.get('analysis', {})
                    table_data.append({
                        "Document": result.get('document_number', 'Unknown'),
                        "Title": result.get('title', 'Unknown')[:100] + "..." if len(result.get('title', '')) > 100 else result.get('title', 'Unknown'),
                        "Agency": result.get('agency_slug', 'Unknown'),
                        "Category": analysis.get('category', 'UNKNOWN'),
                        "Success": "✅" if analysis.get('success') else "❌",
                        "Processing Time": f"{analysis.get('processing_time', 0):.2f}s"
                    })
                
                df = pd.DataFrame(table_data)
                
                # Add filters
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    category_filter = st.multiselect(
                        "Filter by Category",
                        options=list(categories.keys()),
                        default=list(categories.keys())
                    )
                
                with col2:
                    success_filter = st.selectbox(
                        "Filter by Success",
                        options=["All", "Successful Only", "Failed Only"],
                        index=0
                    )
                
                with col3:
                    agency_filter = st.multiselect(
                        "Filter by Agency",
                        options=df['Agency'].unique(),
                        default=df['Agency'].unique()
                    )
                
                # Apply filters
                filtered_df = df[df['Category'].isin(category_filter)]
                filtered_df = filtered_df[filtered_df['Agency'].isin(agency_filter)]
                
                if success_filter == "Successful Only":
                    filtered_df = filtered_df[filtered_df['Success'] == "✅"]
                elif success_filter == "Failed Only":
                    filtered_df = filtered_df[filtered_df['Success'] == "❌"]
                
                st.dataframe(filtered_df, use_container_width=True)
                
                # Export options
                st.subheader("Export Results")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("Export as CSV"):
                        csv = filtered_df.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name=f"analysis_results_{session_id}.csv",
                            mime="text/csv"
                        )
                
                with col2:
                    if st.button("Export as JSON"):
                        json_data = json.dumps(results, indent=2, ensure_ascii=False)
                        st.download_button(
                            label="Download JSON",
                            data=json_data,
                            file_name=f"analysis_results_{session_id}.json",
                            mime="application/json"
                        )
                
                with col3:
                    # Meta-analysis button
                    if st.button("Generate Meta-Analysis"):
                        with st.spinner("Generating meta-analysis..."):
                            try:
                                meta_analysis = analysis_engine.perform_meta_analysis(session_id)
                                if meta_analysis and meta_analysis.success:
                                    st.success("Meta-analysis completed!")
                                    show_meta_analysis_results(meta_analysis)
                                else:
                                    error_msg = meta_analysis.error_message if meta_analysis else "Unknown error"
                                    st.error(f"Meta-analysis failed: {error_msg}")
                            except Exception as e:
                                st.error(f"Meta-analysis error: {e}")
            
            else:
                st.info("No analysis results found for this session.")
    
    except Exception as e:
        st.error(f"Error loading results: {e}")


def show_meta_analysis_results(meta_analysis):
    """Show meta-analysis results."""
    st.subheader("Meta-Analysis Results")
    
    # Executive summary
    if meta_analysis.executive_summary:
        st.write("**Executive Summary:**")
        st.write(meta_analysis.executive_summary)
    
    # Key insights in columns
    col1, col2 = st.columns(2)
    
    with col1:
        if meta_analysis.key_patterns:
            st.write("**Key Patterns:**")
            for i, pattern in enumerate(meta_analysis.key_patterns, 1):
                st.write(f"{i}. {pattern}")
        
        if meta_analysis.quick_wins:
            st.write("**Quick Wins:**")
            for i, win in enumerate(meta_analysis.quick_wins, 1):
                st.write(f"{i}. {win}")
    
    with col2:
        if meta_analysis.priority_actions:
            st.write("**Priority Actions:**")
            for i, action in enumerate(meta_analysis.priority_actions, 1):
                st.write(f"{i}. {action}")
        
        if meta_analysis.reform_opportunities:
            st.write("**Reform Opportunities:**")
            for i, opportunity in enumerate(meta_analysis.reform_opportunities, 1):
                st.write(f"{i}. {opportunity}")


def show_statistics():
    """Show statistics and analytics interface."""
    st.header("Statistics & Analytics")
    
    try:
        stats_engine = get_statistics_engine()
        
        # Time range selector
        col1, col2 = st.columns(2)
        
        with col1:
            date_from = st.date_input(
                "From Date",
                value=datetime.now() - timedelta(days=30),
                help="Start date for statistics"
            )
        
        with col2:
            date_to = st.date_input(
                "To Date",
                value=datetime.now(),
                help="End date for statistics"
            )
        
        # Get statistics
        overall_stats = stats_engine.get_overall_statistics(
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat()
        )
        
        # Pattern analysis
        patterns = stats_engine.analyze_patterns()
        
        # Cost analysis
        cost_analysis = stats_engine.generate_cost_analysis()
        
        # Display statistics
        st.subheader("Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Documents", f"{overall_stats.total_documents:,}")
        
        with col2:
            st.metric("Sessions", f"{overall_stats.total_sessions:,}")
        
        with col3:
            st.metric("Success Rate", f"{overall_stats.success_rate:.1f}%")
        
        with col4:
            st.metric("Avg Time", f"{overall_stats.average_processing_time:.1f}s")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            if overall_stats.category_distribution:
                fig = px.pie(
                    values=list(overall_stats.category_distribution.values()),
                    names=list(overall_stats.category_distribution.keys()),
                    title="Category Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if overall_stats.agency_distribution:
                top_agencies = dict(list(overall_stats.agency_distribution.items())[:10])
                fig = px.bar(
                    x=list(top_agencies.values()),
                    y=list(top_agencies.keys()),
                    orientation='h',
                    title="Top Agencies"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Pattern analysis
        if patterns.frequent_reform_recommendations:
            st.subheader("Reform Recommendation Themes")
            
            themes_data = {
                'Theme': [item[0] for item in patterns.frequent_reform_recommendations],
                'Count': [item[1] for item in patterns.frequent_reform_recommendations]
            }
            
            fig = px.bar(
                x=themes_data['Count'],
                y=themes_data['Theme'],
                orientation='h',
                title="Most Common Reform Themes"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Cost analysis
        if cost_analysis:
            st.subheader("Resource Usage")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                token_usage = cost_analysis.get('token_usage', {})
                st.metric(
                    "Total Tokens",
                    f"{token_usage.get('total_tokens', 0):,}"
                )
            
            with col2:
                processing_time = cost_analysis.get('processing_time', {})
                total_hours = processing_time.get('total_seconds', 0) / 3600
                st.metric(
                    "Total Processing Time",
                    f"{total_hours:.1f} hours"
                )
            
            with col3:
                cost_estimates = cost_analysis.get('cost_estimates', {})
                st.metric(
                    "Estimated Cost",
                    f"${cost_estimates.get('estimated_total_cost', 0):.2f}"
                )
    
    except Exception as e:
        st.error(f"Error loading statistics: {e}")


def show_settings():
    """Show settings and configuration interface."""
    st.header("Settings")
    
    # Configuration settings
    st.subheader("Configuration")
    
    with st.form("settings_form"):
        # Database settings
        st.write("**Database Settings**")
        database_path = st.text_input(
            "Database Path",
            value=Config.DATABASE_PATH,
            help="Path to SQLite database file"
        )
        
        # LLM settings
        st.write("**LLM Settings**")
        default_model = st.selectbox(
            "Default Model",
            ["gemini/gemini-2.5-flash", "gpt-4", "gpt-3.5-turbo", "claude-3-sonnet"],
            index=0,
            help="Default LLM model to use"
        )
        
        rate_limit = st.number_input(
            "Rate Limit (requests/second)",
            min_value=0.1,
            max_value=10.0,
            value=1.0,
            step=0.1,
            help="Rate limit for LLM API calls"
        )
        
        # Analysis settings
        st.write("**Analysis Settings**")
        default_document_limit = st.number_input(
            "Default Document Limit",
            min_value=1,
            max_value=1000,
            value=10,
            help="Default number of documents to analyze"
        )
        
        default_strategy = st.selectbox(
            "Default Strategy",
            ["DOGE Criteria", "Blue Dreams", "EO 14219", "Technical Competence"],
            index=0,
            help="Default analysis strategy"
        )
        
        # Export settings
        st.write("**Export Settings**")
        output_directory = st.text_input(
            "Output Directory",
            value="results",
            help="Default directory for exported results"
        )
        
        # Save settings
        if st.form_submit_button("Save Settings"):
            st.success("Settings saved! (Note: This is a demo - settings are not actually persisted)")
    
    # System information
    st.subheader("System Information")
    
    try:
        db = get_database()
        
        # Database statistics
        total_docs_query = "SELECT COUNT(*) FROM documents"
        total_docs = db.execute_query(total_docs_query)[0][0]
        
        total_analyses_query = "SELECT COUNT(*) FROM analyses"
        total_analyses = db.execute_query(total_analyses_query)[0][0]
        
        total_sessions_query = "SELECT COUNT(*) FROM sessions"
        total_sessions = db.execute_query(total_sessions_query)[0][0]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Documents in Database", f"{total_docs:,}")
        
        with col2:
            st.metric("Total Analyses", f"{total_analyses:,}")
        
        with col3:
            st.metric("Total Sessions", f"{total_sessions:,}")
        
        # Database maintenance
        st.subheader("Database Maintenance")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Clean Old Sessions"):
                session_manager = get_session_manager()
                cleaned = session_manager.cleanup_old_sessions(days_old=30)
                st.success(f"Cleaned up {cleaned} old sessions")
        
        with col2:
            if st.button("Optimize Database"):
                db.execute_query("VACUUM")
                st.success("Database optimized")
    
    except Exception as e:
        st.error(f"Error loading system information: {e}")


if __name__ == "__main__":
    main()