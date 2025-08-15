"""
Statistics and reporting engine for CFR Document Analyzer.

Provides aggregate analysis, pattern identification, and comparative statistics.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass

from .database import Database
from .models import RegulationCategory, SessionStatus
from .utils import safe_json_loads


logger = logging.getLogger(__name__)


@dataclass
class AnalysisStatistics:
    """Container for analysis statistics."""
    total_documents: int
    total_sessions: int
    category_distribution: Dict[str, int]
    agency_distribution: Dict[str, int]
    success_rate: float
    average_processing_time: float
    total_cost: float
    date_range: Tuple[str, str]


@dataclass
class PatternAnalysis:
    """Container for pattern analysis results."""
    common_statutory_references: List[Tuple[str, int]]
    frequent_reform_recommendations: List[Tuple[str, int]]
    category_trends: Dict[str, List[Tuple[str, int]]]
    agency_patterns: Dict[str, Dict[str, Any]]


@dataclass
class ComparativeAnalysis:
    """Container for comparative analysis results."""
    agency_comparisons: Dict[str, Dict[str, Any]]
    strategy_comparisons: Dict[str, Dict[str, Any]]
    temporal_trends: Dict[str, List[Tuple[str, float]]]


class StatisticsEngine:
    """Engine for generating statistics and reports from analysis data."""
    
    def __init__(self, database: Database):
        """
        Initialize statistics engine.
        
        Args:
            database: Database instance
        """
        self.database = database
        logger.info("Statistics engine initialized")
    
    def get_overall_statistics(self, date_from: Optional[str] = None, 
                              date_to: Optional[str] = None) -> AnalysisStatistics:
        """
        Get overall analysis statistics.
        
        Args:
            date_from: Start date filter (ISO format)
            date_to: End date filter (ISO format)
            
        Returns:
            AnalysisStatistics object
        """
        try:
            # Build date filter
            date_filter = ""
            params = []
            
            if date_from:
                date_filter += " AND a.created_at >= ?"
                params.append(date_from)
            
            if date_to:
                date_filter += " AND a.created_at <= ?"
                params.append(date_to)
            
            # Total documents analyzed
            total_query = f"""
                SELECT COUNT(*) FROM analyses a
                WHERE a.success = 1{date_filter}
            """
            total_results = self.database.execute_query(total_query, tuple(params))
            total_documents = total_results[0][0] if total_results else 0
            
            # Total sessions
            session_query = f"""
                SELECT COUNT(DISTINCT s.session_id) FROM sessions s
                JOIN documents d ON JSON_EXTRACT(s.agency_slugs, '$[0]') = d.agency_slug
                JOIN analyses a ON d.id = a.document_id
                WHERE a.success = 1{date_filter.replace('a.created_at', 's.created_at')}
            """
            session_results = self.database.execute_query(session_query, tuple(params))
            total_sessions = session_results[0][0] if session_results else 0
            
            # Category distribution
            category_query = f"""
                SELECT a.category, COUNT(*) FROM analyses a
                WHERE a.success = 1{date_filter}
                GROUP BY a.category
            """
            category_results = self.database.execute_query(category_query, tuple(params))
            category_distribution = {row[0] or 'UNKNOWN': row[1] for row in category_results}
            
            # Agency distribution
            agency_query = f"""
                SELECT d.agency_slug, COUNT(*) FROM analyses a
                JOIN documents d ON a.document_id = d.id
                WHERE a.success = 1{date_filter}
                GROUP BY d.agency_slug
                ORDER BY COUNT(*) DESC
            """
            agency_results = self.database.execute_query(agency_query, tuple(params))
            agency_distribution = {row[0]: row[1] for row in agency_results}
            
            # Success rate
            success_query = f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                FROM analyses a
                WHERE 1=1{date_filter}
            """
            success_results = self.database.execute_query(success_query, tuple(params))
            if success_results and success_results[0][0] > 0:
                total_attempts = success_results[0][0]
                successful = success_results[0][1]
                success_rate = (successful / total_attempts) * 100.0
            else:
                success_rate = 0.0
            
            # Average processing time
            time_query = f"""
                SELECT AVG(processing_time) FROM analyses a
                WHERE a.success = 1 AND a.processing_time > 0{date_filter}
            """
            time_results = self.database.execute_query(time_query, tuple(params))
            average_processing_time = time_results[0][0] if time_results and time_results[0][0] else 0.0
            
            # Date range
            range_query = f"""
                SELECT MIN(created_at), MAX(created_at) FROM analyses a
                WHERE a.success = 1{date_filter}
            """
            range_results = self.database.execute_query(range_query, tuple(params))
            if range_results and range_results[0][0]:
                date_range = (range_results[0][0], range_results[0][1])
            else:
                date_range = ("", "")
            
            return AnalysisStatistics(
                total_documents=total_documents,
                total_sessions=total_sessions,
                category_distribution=category_distribution,
                agency_distribution=agency_distribution,
                success_rate=success_rate,
                average_processing_time=average_processing_time,
                total_cost=0.0,  # Would need to implement cost tracking
                date_range=date_range
            )
            
        except Exception as e:
            logger.error(f"Failed to get overall statistics: {e}")
            return AnalysisStatistics(0, 0, {}, {}, 0.0, 0.0, 0.0, ("", ""))
    
    def analyze_patterns(self, limit: int = 20) -> PatternAnalysis:
        """
        Analyze patterns in analysis results.
        
        Args:
            limit: Maximum number of patterns to return
            
        Returns:
            PatternAnalysis object
        """
        try:
            # Common statutory references
            statutory_refs = []
            ref_query = """
                SELECT statutory_references FROM analyses 
                WHERE success = 1 AND statutory_references IS NOT NULL
            """
            ref_results = self.database.execute_query(ref_query)
            
            ref_counter = Counter()
            for row in ref_results:
                refs = safe_json_loads(row[0], [])
                for ref in refs:
                    if ref and len(ref.strip()) > 10:  # Filter out very short references
                        ref_counter[ref.strip()] += 1
            
            common_statutory_references = ref_counter.most_common(limit)
            
            # Frequent reform recommendations
            rec_query = """
                SELECT reform_recommendations FROM analyses 
                WHERE success = 1 AND reform_recommendations IS NOT NULL
            """
            rec_results = self.database.execute_query(rec_query)
            
            rec_counter = Counter()
            for row in rec_results:
                recs = safe_json_loads(row[0], [])
                for rec in recs:
                    if rec and len(rec.strip()) > 20:  # Filter out very short recommendations
                        # Extract key phrases from recommendations
                        rec_lower = rec.lower()
                        if 'simplif' in rec_lower:
                            rec_counter['Simplification'] += 1
                        if 'modern' in rec_lower:
                            rec_counter['Modernization'] += 1
                        if 'harmon' in rec_lower:
                            rec_counter['Harmonization'] += 1
                        if 'delet' in rec_lower or 'remov' in rec_lower:
                            rec_counter['Deletion'] += 1
                        if 'burden' in rec_lower:
                            rec_counter['Burden Reduction'] += 1
                        if 'automat' in rec_lower:
                            rec_counter['Automation'] += 1
            
            frequent_reform_recommendations = rec_counter.most_common(limit)
            
            # Category trends by agency
            trend_query = """
                SELECT d.agency_slug, a.category, COUNT(*) 
                FROM analyses a
                JOIN documents d ON a.document_id = d.id
                WHERE a.success = 1
                GROUP BY d.agency_slug, a.category
                ORDER BY d.agency_slug, COUNT(*) DESC
            """
            trend_results = self.database.execute_query(trend_query)
            
            category_trends = defaultdict(list)
            for row in trend_results:
                agency, category, count = row
                category_trends[agency].append((category or 'UNKNOWN', count))
            
            # Agency patterns
            agency_patterns = {}
            for agency in category_trends.keys():
                agency_query = """
                    SELECT 
                        COUNT(*) as total_docs,
                        AVG(a.processing_time) as avg_time,
                        SUM(CASE WHEN a.success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
                    FROM analyses a
                    JOIN documents d ON a.document_id = d.id
                    WHERE d.agency_slug = ?
                """
                agency_results = self.database.execute_query(agency_query, (agency,))
                
                if agency_results:
                    total_docs, avg_time, success_rate = agency_results[0]
                    agency_patterns[agency] = {
                        'total_documents': total_docs,
                        'average_processing_time': avg_time or 0.0,
                        'success_rate': success_rate or 0.0,
                        'category_distribution': dict(category_trends[agency])
                    }
            
            return PatternAnalysis(
                common_statutory_references=common_statutory_references,
                frequent_reform_recommendations=frequent_reform_recommendations,
                category_trends=dict(category_trends),
                agency_patterns=agency_patterns
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze patterns: {e}")
            return PatternAnalysis([], [], {}, {})
    
    def compare_agencies(self, agencies: List[str]) -> ComparativeAnalysis:
        """
        Compare analysis results across agencies.
        
        Args:
            agencies: List of agency slugs to compare
            
        Returns:
            ComparativeAnalysis object
        """
        try:
            agency_comparisons = {}
            
            for agency in agencies:
                # Get agency statistics
                stats_query = """
                    SELECT 
                        COUNT(*) as total_docs,
                        AVG(a.processing_time) as avg_time,
                        SUM(CASE WHEN a.success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
                        a.category,
                        COUNT(a.category) as category_count
                    FROM analyses a
                    JOIN documents d ON a.document_id = d.id
                    WHERE d.agency_slug = ?
                    GROUP BY a.category
                """
                stats_results = self.database.execute_query(stats_query, (agency,))
                
                if stats_results:
                    total_docs = stats_results[0][0]
                    avg_time = stats_results[0][1] or 0.0
                    success_rate = stats_results[0][2] or 0.0
                    
                    categories = {}
                    for row in stats_results:
                        category = row[3] or 'UNKNOWN'
                        count = row[4]
                        categories[category] = count
                    
                    agency_comparisons[agency] = {
                        'total_documents': total_docs,
                        'average_processing_time': avg_time,
                        'success_rate': success_rate,
                        'categories': categories
                    }
            
            # Strategy comparisons (if multiple strategies used)
            strategy_query = """
                SELECT 
                    a.prompt_strategy,
                    COUNT(*) as total_docs,
                    AVG(a.processing_time) as avg_time,
                    SUM(CASE WHEN a.success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
                FROM analyses a
                GROUP BY a.prompt_strategy
            """
            strategy_results = self.database.execute_query(strategy_query)
            
            strategy_comparisons = {}
            for row in strategy_results:
                strategy, total_docs, avg_time, success_rate = row
                strategy_comparisons[strategy] = {
                    'total_documents': total_docs,
                    'average_processing_time': avg_time or 0.0,
                    'success_rate': success_rate or 0.0
                }
            
            # Temporal trends (documents analyzed over time)
            temporal_query = """
                SELECT 
                    DATE(a.created_at) as analysis_date,
                    COUNT(*) as docs_analyzed
                FROM analyses a
                WHERE a.success = 1
                GROUP BY DATE(a.created_at)
                ORDER BY analysis_date
            """
            temporal_results = self.database.execute_query(temporal_query)
            
            temporal_trends = {
                'daily_volume': [(row[0], row[1]) for row in temporal_results]
            }
            
            return ComparativeAnalysis(
                agency_comparisons=agency_comparisons,
                strategy_comparisons=strategy_comparisons,
                temporal_trends=temporal_trends
            )
            
        except Exception as e:
            logger.error(f"Failed to compare agencies: {e}")
            return ComparativeAnalysis({}, {}, {})
    
    def generate_cost_analysis(self) -> Dict[str, Any]:
        """
        Generate cost analysis based on token usage and processing time.
        
        Returns:
            Dictionary with cost analysis
        """
        try:
            # Token usage analysis
            token_query = """
                SELECT 
                    SUM(token_usage) as total_tokens,
                    AVG(token_usage) as avg_tokens,
                    COUNT(*) as total_calls
                FROM analyses
                WHERE success = 1 AND token_usage > 0
            """
            token_results = self.database.execute_query(token_query)
            
            if token_results and token_results[0][0]:
                total_tokens, avg_tokens, total_calls = token_results[0]
            else:
                total_tokens = avg_tokens = total_calls = 0
            
            # Processing time analysis
            time_query = """
                SELECT 
                    SUM(processing_time) as total_time,
                    AVG(processing_time) as avg_time,
                    MAX(processing_time) as max_time,
                    MIN(processing_time) as min_time
                FROM analyses
                WHERE success = 1 AND processing_time > 0
            """
            time_results = self.database.execute_query(time_query)
            
            if time_results and time_results[0][0]:
                total_time, avg_time, max_time, min_time = time_results[0]
            else:
                total_time = avg_time = max_time = min_time = 0
            
            # Estimate costs (these would need to be updated with actual pricing)
            estimated_cost_per_1k_tokens = 0.002  # Example pricing
            estimated_total_cost = (total_tokens / 1000) * estimated_cost_per_1k_tokens
            
            return {
                'token_usage': {
                    'total_tokens': total_tokens or 0,
                    'average_tokens_per_call': avg_tokens or 0,
                    'total_calls': total_calls or 0
                },
                'processing_time': {
                    'total_seconds': total_time or 0,
                    'average_seconds': avg_time or 0,
                    'max_seconds': max_time or 0,
                    'min_seconds': min_time or 0
                },
                'cost_estimates': {
                    'estimated_total_cost': estimated_total_cost,
                    'cost_per_document': estimated_total_cost / max(1, total_calls),
                    'cost_per_token': estimated_cost_per_1k_tokens / 1000
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate cost analysis: {e}")
            return {}
    
    def get_session_performance_metrics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics for sessions.
        
        Args:
            session_id: Specific session ID (optional)
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            session_filter = ""
            params = []
            
            if session_id:
                session_filter = " AND s.session_id = ?"
                params.append(session_id)
            
            # Session completion metrics
            completion_query = f"""
                SELECT 
                    s.status,
                    COUNT(*) as count,
                    AVG(
                        CASE WHEN s.completed_at IS NOT NULL 
                        THEN (julianday(s.completed_at) - julianday(s.created_at)) * 24 * 60
                        ELSE NULL END
                    ) as avg_duration_minutes
                FROM sessions s
                WHERE 1=1{session_filter}
                GROUP BY s.status
            """
            completion_results = self.database.execute_query(completion_query, tuple(params))
            
            session_metrics = {}
            for row in completion_results:
                status, count, avg_duration = row
                session_metrics[status] = {
                    'count': count,
                    'average_duration_minutes': avg_duration or 0
                }
            
            # Document processing efficiency
            efficiency_query = f"""
                SELECT 
                    s.session_id,
                    s.documents_processed,
                    s.total_documents,
                    (s.documents_processed * 100.0 / NULLIF(s.total_documents, 0)) as completion_rate,
                    (julianday(COALESCE(s.completed_at, 'now')) - julianday(s.created_at)) * 24 * 60 as duration_minutes
                FROM sessions s
                WHERE s.total_documents > 0{session_filter}
            """
            efficiency_results = self.database.execute_query(efficiency_query, tuple(params))
            
            efficiency_metrics = []
            for row in efficiency_results:
                session_id, processed, total, completion_rate, duration = row
                efficiency_metrics.append({
                    'session_id': session_id,
                    'documents_processed': processed,
                    'total_documents': total,
                    'completion_rate': completion_rate or 0,
                    'duration_minutes': duration or 0,
                    'documents_per_minute': processed / max(1, duration or 1)
                })
            
            return {
                'session_status_distribution': session_metrics,
                'efficiency_metrics': efficiency_metrics,
                'total_sessions': len(efficiency_metrics)
            }
            
        except Exception as e:
            logger.error(f"Failed to get session performance metrics: {e}")
            return {}
    
    def generate_comprehensive_report(self, output_format: str = 'dict') -> Any:
        """
        Generate comprehensive analysis report.
        
        Args:
            output_format: Output format ('dict', 'json', 'markdown')
            
        Returns:
            Comprehensive report in specified format
        """
        try:
            # Gather all statistics
            overall_stats = self.get_overall_statistics()
            patterns = self.analyze_patterns()
            cost_analysis = self.generate_cost_analysis()
            performance_metrics = self.get_session_performance_metrics()
            
            # Get top agencies for comparison
            top_agencies = list(overall_stats.agency_distribution.keys())[:5]
            comparative_analysis = self.compare_agencies(top_agencies)
            
            report_data = {
                'generated_at': datetime.now().isoformat(),
                'overall_statistics': {
                    'total_documents': overall_stats.total_documents,
                    'total_sessions': overall_stats.total_sessions,
                    'success_rate': overall_stats.success_rate,
                    'average_processing_time': overall_stats.average_processing_time,
                    'date_range': overall_stats.date_range
                },
                'category_distribution': overall_stats.category_distribution,
                'agency_distribution': dict(list(overall_stats.agency_distribution.items())[:10]),
                'pattern_analysis': {
                    'top_statutory_references': patterns.common_statutory_references[:10],
                    'reform_recommendation_themes': patterns.frequent_reform_recommendations[:10],
                    'agency_category_patterns': {k: v[:3] for k, v in patterns.category_trends.items()}
                },
                'cost_analysis': cost_analysis,
                'performance_metrics': performance_metrics,
                'comparative_analysis': {
                    'agency_comparisons': comparative_analysis.agency_comparisons,
                    'strategy_comparisons': comparative_analysis.strategy_comparisons
                }
            }
            
            if output_format == 'json':
                return json.dumps(report_data, indent=2, ensure_ascii=False)
            elif output_format == 'markdown':
                return self._format_report_as_markdown(report_data)
            else:
                return report_data
                
        except Exception as e:
            logger.error(f"Failed to generate comprehensive report: {e}")
            return {} if output_format == 'dict' else ""
    
    def _format_report_as_markdown(self, report_data: Dict[str, Any]) -> str:
        """
        Format report data as Markdown.
        
        Args:
            report_data: Report data dictionary
            
        Returns:
            Markdown formatted report
        """
        lines = [
            "# CFR Document Analysis Report",
            "",
            f"**Generated:** {report_data['generated_at']}",
            "",
            "## Overall Statistics",
            "",
            f"- **Total Documents Analyzed:** {report_data['overall_statistics']['total_documents']:,}",
            f"- **Total Sessions:** {report_data['overall_statistics']['total_sessions']:,}",
            f"- **Success Rate:** {report_data['overall_statistics']['success_rate']:.1f}%",
            f"- **Average Processing Time:** {report_data['overall_statistics']['average_processing_time']:.2f} seconds",
            "",
            "## Category Distribution",
            ""
        ]
        
        for category, count in report_data['category_distribution'].items():
            lines.append(f"- **{category}:** {count:,} documents")
        
        lines.extend([
            "",
            "## Top Agencies by Document Count",
            ""
        ])
        
        for agency, count in list(report_data['agency_distribution'].items())[:10]:
            lines.append(f"- **{agency}:** {count:,} documents")
        
        if report_data.get('pattern_analysis', {}).get('reform_recommendation_themes'):
            lines.extend([
                "",
                "## Reform Recommendation Themes",
                ""
            ])
            
            for theme, count in report_data['pattern_analysis']['reform_recommendation_themes']:
                lines.append(f"- **{theme}:** {count:,} occurrences")
        
        if report_data.get('cost_analysis', {}).get('token_usage'):
            token_data = report_data['cost_analysis']['token_usage']
            lines.extend([
                "",
                "## Resource Usage",
                "",
                f"- **Total Tokens:** {token_data.get('total_tokens', 0):,}",
                f"- **Average Tokens per Call:** {token_data.get('average_tokens_per_call', 0):.0f}",
                f"- **Total API Calls:** {token_data.get('total_calls', 0):,}"
            ])
        
        return "\n".join(lines)