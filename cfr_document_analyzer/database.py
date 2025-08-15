"""
Database management for CFR Document Analyzer.

Handles SQLite database operations for storing documents, analyses, and sessions.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Any, List, Tuple, Optional
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager for CFR Document Analyzer."""
    
    def __init__(self, db_path: str):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: Tuple = ()) -> List[Any]:
        """
        Execute a query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of query results
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall()
    
    def _initialize_database(self):
        """Initialize database tables if they don't exist."""
        logger.info(f"Initializing database at {self.db_path}")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_number TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    agency_slug TEXT NOT NULL,
                    publication_date TEXT,
                    cfr_citation TEXT,
                    content TEXT,
                    content_length INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Analyses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    prompt_strategy TEXT NOT NULL,
                    category TEXT,  -- SR, NSR, NRAN
                    statutory_references TEXT,  -- JSON array
                    reform_recommendations TEXT,  -- JSON array
                    justification TEXT,
                    raw_response TEXT,
                    token_usage INTEGER,
                    processing_time REAL,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents (id)
                )
            """)
            
            # Sessions table for tracking analysis runs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    agency_slugs TEXT,  -- JSON array
                    prompt_strategy TEXT NOT NULL,
                    document_limit INTEGER,
                    status TEXT DEFAULT 'created',  -- created, running, completed, failed, cancelled
                    documents_processed INTEGER DEFAULT 0,
                    total_documents INTEGER DEFAULT 0,
                    config TEXT,  -- JSON configuration data
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            
            # Meta-analyses table for storing meta-analysis results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meta_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    key_patterns TEXT,  -- JSON array
                    strategic_themes TEXT,  -- JSON array
                    priority_actions TEXT,  -- JSON array
                    goal_alignment TEXT,
                    implementation_roadmap TEXT,
                    executive_summary TEXT,
                    reform_opportunities TEXT,  -- JSON array
                    implementation_challenges TEXT,  -- JSON array
                    stakeholder_impact TEXT,
                    resource_requirements TEXT,
                    risk_assessment TEXT,
                    quick_wins TEXT,  -- JSON array
                    long_term_strategy TEXT,
                    processing_time REAL,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_agency ON documents(agency_slug)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_number ON documents(document_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_document ON analyses(document_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_id ON sessions(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_meta_analyses_session ON meta_analyses(session_id)")
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def store_document(self, document_data: dict) -> int:
        """
        Store a document in the database.
        
        Args:
            document_data: Dictionary containing document information
            
        Returns:
            Document ID
        """
        query = """
            INSERT OR REPLACE INTO documents 
            (document_number, title, agency_slug, publication_date, cfr_citation, content, content_length, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        content = document_data.get('content', '')
        params = (
            document_data['document_number'],
            document_data['title'],
            document_data['agency_slug'],
            document_data.get('publication_date'),
            document_data.get('cfr_citation'),
            content,
            len(content) if content else 0
        )
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    
    def store_analysis(self, analysis_data: dict) -> int:
        """
        Store an analysis result in the database.
        
        Args:
            analysis_data: Dictionary containing analysis information
            
        Returns:
            Analysis ID
        """
        query = """
            INSERT INTO analyses 
            (document_id, prompt_strategy, category, statutory_references, reform_recommendations, 
             justification, raw_response, token_usage, processing_time, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            analysis_data['document_id'],
            analysis_data['prompt_strategy'],
            analysis_data.get('category'),
            analysis_data.get('statutory_references'),  # JSON string
            analysis_data.get('reform_recommendations'),  # JSON string
            analysis_data.get('justification'),
            analysis_data.get('raw_response'),
            analysis_data.get('token_usage', 0),
            analysis_data.get('processing_time', 0.0),
            analysis_data.get('success', True),
            analysis_data.get('error_message')
        )
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    
    def get_documents_by_agency(self, agency_slug: str, limit: Optional[int] = None) -> List[dict]:
        """
        Get documents for a specific agency.
        
        Args:
            agency_slug: Agency identifier
            limit: Maximum number of documents to return
            
        Returns:
            List of document dictionaries
        """
        query = "SELECT * FROM documents WHERE agency_slug = ? ORDER BY publication_date DESC"
        params = (agency_slug,)
        
        if limit:
            query += " LIMIT ?"
            params = (agency_slug, limit)
        
        results = self.execute_query(query, params)
        return [dict(row) for row in results]
    
    def get_analyses_by_document(self, document_id: int) -> List[dict]:
        """
        Get all analyses for a specific document.
        
        Args:
            document_id: Document ID
            
        Returns:
            List of analysis dictionaries
        """
        query = "SELECT * FROM analyses WHERE document_id = ? ORDER BY created_at DESC"
        results = self.execute_query(query, (document_id,))
        return [dict(row) for row in results]
    
    def create_session(self, session_data: dict) -> str:
        """
        Create a new analysis session.
        
        Args:
            session_data: Session configuration data
            
        Returns:
            Session ID
        """
        import uuid
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_id = f"session_{timestamp}_{uuid.uuid4().hex[:8]}"
        
        query = """
            INSERT INTO sessions 
            (session_id, agency_slugs, prompt_strategy, document_limit, total_documents)
            VALUES (?, ?, ?, ?, ?)
        """
        
        params = (
            session_id,
            session_data.get('agency_slugs'),  # JSON string
            session_data['prompt_strategy'],
            session_data.get('document_limit'),
            session_data.get('total_documents', 0)
        )
        
        self.execute_query(query, params)
        return session_id
    
    def update_session_status(self, session_id: str, status: str, documents_processed: Optional[int] = None):
        """
        Update session status and progress.
        
        Args:
            session_id: Session identifier
            status: New status
            documents_processed: Number of documents processed
        """
        if documents_processed is not None:
            query = "UPDATE sessions SET status = ?, documents_processed = ? WHERE session_id = ?"
            params = (status, documents_processed, session_id)
        else:
            query = "UPDATE sessions SET status = ? WHERE session_id = ?"
            params = (status, session_id)
        
        if status == 'completed':
            query = query.replace("SET status = ?", "SET status = ?, completed_at = CURRENT_TIMESTAMP")
        
        self.execute_query(query, params)
    
    def store_meta_analysis(self, meta_analysis_data: dict) -> int:
        """
        Store a meta-analysis result in the database.
        
        Args:
            meta_analysis_data: Dictionary containing meta-analysis information
            
        Returns:
            Meta-analysis ID
        """
        query = """
            INSERT INTO meta_analyses 
            (session_id, key_patterns, strategic_themes, priority_actions, goal_alignment,
             implementation_roadmap, executive_summary, reform_opportunities, implementation_challenges,
             stakeholder_impact, resource_requirements, risk_assessment, quick_wins, long_term_strategy,
             processing_time, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            meta_analysis_data['session_id'],
            meta_analysis_data.get('key_patterns'),  # JSON string
            meta_analysis_data.get('strategic_themes'),  # JSON string
            meta_analysis_data.get('priority_actions'),  # JSON string
            meta_analysis_data.get('goal_alignment'),
            meta_analysis_data.get('implementation_roadmap'),
            meta_analysis_data.get('executive_summary'),
            meta_analysis_data.get('reform_opportunities'),  # JSON string
            meta_analysis_data.get('implementation_challenges'),  # JSON string
            meta_analysis_data.get('stakeholder_impact'),
            meta_analysis_data.get('resource_requirements'),
            meta_analysis_data.get('risk_assessment'),
            meta_analysis_data.get('quick_wins'),  # JSON string
            meta_analysis_data.get('long_term_strategy'),
            meta_analysis_data.get('processing_time', 0.0),
            meta_analysis_data.get('success', True),
            meta_analysis_data.get('error_message')
        )
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    
    def get_meta_analysis_by_session(self, session_id: str) -> Optional[dict]:
        """
        Get meta-analysis result for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Meta-analysis dictionary or None if not found
        """
        query = "SELECT * FROM meta_analyses WHERE session_id = ? ORDER BY created_at DESC LIMIT 1"
        results = self.execute_query(query, (session_id,))
        
        if results:
            return dict(results[0])
        return None