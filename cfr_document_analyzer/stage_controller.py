"""
Stage controller for selective execution and resource controls.

Manages configurable analysis stages with resource limits and validation.
"""

import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

from .models import SessionStatus
from .progress_tracker import ProgressStage


logger = logging.getLogger(__name__)


class AnalysisStage(Enum):
    """Available analysis stages."""
    DOCUMENT_RETRIEVAL = "document_retrieval"
    DOCUMENT_ANALYSIS = "document_analysis"
    META_ANALYSIS = "meta_analysis"
    AGENCY_RESPONSE_SIMULATION = "agency_response_simulation"
    LEADERSHIP_DECISION_SIMULATION = "leadership_decision_simulation"
    REGULATORY_SUBMISSION = "regulatory_submission"
    PUBLIC_COMMENT_SIMULATION = "public_comment_simulation"
    PUBLIC_COMMENT_ANALYSIS = "public_comment_analysis"
    FINAL_RULE_DRAFTING = "final_rule_drafting"
    EXPORT_RESULTS = "export_results"


@dataclass
class StageConfig:
    """Configuration for an analysis stage."""
    enabled: bool = True
    document_limit: Optional[int] = None
    time_limit_seconds: Optional[int] = None
    memory_limit_mb: Optional[int] = None
    retry_attempts: int = 3
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """Validate stage configuration."""
        errors = []
        
        if self.document_limit is not None and self.document_limit <= 0:
            errors.append("Document limit must be positive")
        
        if self.time_limit_seconds is not None and self.time_limit_seconds <= 0:
            errors.append("Time limit must be positive")
        
        if self.memory_limit_mb is not None and self.memory_limit_mb <= 0:
            errors.append("Memory limit must be positive")
        
        if self.retry_attempts < 0:
            errors.append("Retry attempts cannot be negative")
        
        return errors


@dataclass
class ResourceLimits:
    """Resource limits for analysis execution."""
    max_documents_per_stage: int = 1000
    max_total_processing_time: int = 3600  # seconds
    max_memory_usage: int = 2048  # MB
    max_concurrent_operations: int = 5
    max_api_calls_per_minute: int = 60
    
    def validate(self) -> List[str]:
        """Validate resource limits."""
        errors = []
        
        if self.max_documents_per_stage <= 0:
            errors.append("Max documents per stage must be positive")
        
        if self.max_total_processing_time <= 0:
            errors.append("Max total processing time must be positive")
        
        if self.max_memory_usage <= 0:
            errors.append("Max memory usage must be positive")
        
        if self.max_concurrent_operations <= 0:
            errors.append("Max concurrent operations must be positive")
        
        if self.max_api_calls_per_minute <= 0:
            errors.append("Max API calls per minute must be positive")
        
        return errors


class StageController:
    """Controls selective stage execution with resource management."""
    
    def __init__(self, resource_limits: Optional[ResourceLimits] = None):
        """
        Initialize stage controller.
        
        Args:
            resource_limits: Resource limits configuration
        """
        self.resource_limits = resource_limits or ResourceLimits()
        self.stage_configs: Dict[AnalysisStage, StageConfig] = {}
        self.execution_order: List[AnalysisStage] = [
            AnalysisStage.DOCUMENT_RETRIEVAL,
            AnalysisStage.DOCUMENT_ANALYSIS,
            AnalysisStage.META_ANALYSIS,
            AnalysisStage.AGENCY_RESPONSE_SIMULATION,
            AnalysisStage.LEADERSHIP_DECISION_SIMULATION,
            AnalysisStage.REGULATORY_SUBMISSION,
            AnalysisStage.PUBLIC_COMMENT_SIMULATION,
            AnalysisStage.PUBLIC_COMMENT_ANALYSIS,
            AnalysisStage.FINAL_RULE_DRAFTING,
            AnalysisStage.EXPORT_RESULTS
        ]
        
        # Initialize default configurations
        self._initialize_default_configs()
        
        logger.info("Stage controller initialized")
    
    def _initialize_default_configs(self):
        """Initialize default stage configurations."""
        # Document retrieval - always enabled
        self.stage_configs[AnalysisStage.DOCUMENT_RETRIEVAL] = StageConfig(
            enabled=True,
            document_limit=None,  # Use session limit
            time_limit_seconds=300,  # 5 minutes
            parameters={'use_cache': True}
        )
        
        # Document analysis - core functionality
        self.stage_configs[AnalysisStage.DOCUMENT_ANALYSIS] = StageConfig(
            enabled=True,
            document_limit=None,  # Use session limit
            time_limit_seconds=1800,  # 30 minutes
            parameters={'parallel_processing': False}
        )
        
        # Meta-analysis - enabled by default
        self.stage_configs[AnalysisStage.META_ANALYSIS] = StageConfig(
            enabled=True,
            time_limit_seconds=300,  # 5 minutes
            parameters={'include_patterns': True, 'include_recommendations': True}
        )
        
        # Advanced stages - disabled by default
        for stage in [
            AnalysisStage.AGENCY_RESPONSE_SIMULATION,
            AnalysisStage.LEADERSHIP_DECISION_SIMULATION,
            AnalysisStage.REGULATORY_SUBMISSION,
            AnalysisStage.PUBLIC_COMMENT_SIMULATION,
            AnalysisStage.PUBLIC_COMMENT_ANALYSIS,
            AnalysisStage.FINAL_RULE_DRAFTING
        ]:
            self.stage_configs[stage] = StageConfig(
                enabled=False,
                time_limit_seconds=600,  # 10 minutes
                document_limit=100  # Limit for simulation stages
            )
        
        # Export results - always enabled
        self.stage_configs[AnalysisStage.EXPORT_RESULTS] = StageConfig(
            enabled=True,
            time_limit_seconds=120,  # 2 minutes
            parameters={'formats': ['json', 'csv', 'html']}
        )
    
    def configure_stage(self, stage: AnalysisStage, config: StageConfig) -> bool:
        """
        Configure a specific analysis stage.
        
        Args:
            stage: Analysis stage to configure
            config: Stage configuration
            
        Returns:
            True if configuration is valid and applied
        """
        try:
            # Validate configuration
            errors = config.validate()
            if errors:
                logger.error(f"Invalid stage configuration for {stage.value}: {errors}")
                return False
            
            # Apply configuration
            self.stage_configs[stage] = config
            logger.info(f"Configured stage {stage.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure stage {stage.value}: {e}")
            return False
    
    def enable_stage(self, stage: AnalysisStage, **parameters) -> bool:
        """
        Enable a specific analysis stage.
        
        Args:
            stage: Analysis stage to enable
            **parameters: Additional stage parameters
            
        Returns:
            True if successful
        """
        try:
            if stage not in self.stage_configs:
                self.stage_configs[stage] = StageConfig()
            
            self.stage_configs[stage].enabled = True
            if parameters:
                self.stage_configs[stage].parameters.update(parameters)
            
            logger.info(f"Enabled stage {stage.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable stage {stage.value}: {e}")
            return False
    
    def disable_stage(self, stage: AnalysisStage) -> bool:
        """
        Disable a specific analysis stage.
        
        Args:
            stage: Analysis stage to disable
            
        Returns:
            True if successful
        """
        try:
            if stage in self.stage_configs:
                self.stage_configs[stage].enabled = False
                logger.info(f"Disabled stage {stage.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable stage {stage.value}: {e}")
            return False
    
    def get_enabled_stages(self) -> List[AnalysisStage]:
        """
        Get list of enabled stages in execution order.
        
        Returns:
            List of enabled analysis stages
        """
        enabled_stages = []
        for stage in self.execution_order:
            if stage in self.stage_configs and self.stage_configs[stage].enabled:
                enabled_stages.append(stage)
        
        return enabled_stages
    
    def validate_stage_configuration(self) -> List[str]:
        """
        Validate the complete stage configuration.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate resource limits
        resource_errors = self.resource_limits.validate()
        errors.extend([f"Resource limit error: {error}" for error in resource_errors])
        
        # Validate individual stage configurations
        for stage, config in self.stage_configs.items():
            stage_errors = config.validate()
            errors.extend([f"Stage {stage.value} error: {error}" for error in stage_errors])
        
        # Validate stage dependencies
        enabled_stages = self.get_enabled_stages()
        
        # Document analysis requires document retrieval
        if (AnalysisStage.DOCUMENT_ANALYSIS in enabled_stages and 
            AnalysisStage.DOCUMENT_RETRIEVAL not in enabled_stages):
            errors.append("Document analysis requires document retrieval to be enabled")
        
        # Meta-analysis requires document analysis
        if (AnalysisStage.META_ANALYSIS in enabled_stages and 
            AnalysisStage.DOCUMENT_ANALYSIS not in enabled_stages):
            errors.append("Meta-analysis requires document analysis to be enabled")
        
        # Advanced stages require document analysis
        advanced_stages = [
            AnalysisStage.AGENCY_RESPONSE_SIMULATION,
            AnalysisStage.LEADERSHIP_DECISION_SIMULATION,
            AnalysisStage.REGULATORY_SUBMISSION,
            AnalysisStage.PUBLIC_COMMENT_SIMULATION,
            AnalysisStage.PUBLIC_COMMENT_ANALYSIS,
            AnalysisStage.FINAL_RULE_DRAFTING
        ]
        
        for stage in advanced_stages:
            if (stage in enabled_stages and 
                AnalysisStage.DOCUMENT_ANALYSIS not in enabled_stages):
                errors.append(f"{stage.value} requires document analysis to be enabled")
        
        # Public comment analysis requires public comment simulation
        if (AnalysisStage.PUBLIC_COMMENT_ANALYSIS in enabled_stages and 
            AnalysisStage.PUBLIC_COMMENT_SIMULATION not in enabled_stages):
            errors.append("Public comment analysis requires public comment simulation")
        
        return errors
    
    def estimate_resource_usage(self, document_count: int) -> Dict[str, Any]:
        """
        Estimate resource usage for the configured stages.
        
        Args:
            document_count: Number of documents to process
            
        Returns:
            Dictionary with resource usage estimates
        """
        enabled_stages = self.get_enabled_stages()
        
        # Base estimates per document (these would be calibrated from actual usage)
        base_estimates = {
            AnalysisStage.DOCUMENT_RETRIEVAL: {'time': 2, 'memory': 10, 'api_calls': 1},
            AnalysisStage.DOCUMENT_ANALYSIS: {'time': 15, 'memory': 50, 'api_calls': 1},
            AnalysisStage.META_ANALYSIS: {'time': 30, 'memory': 100, 'api_calls': 2},
            AnalysisStage.AGENCY_RESPONSE_SIMULATION: {'time': 10, 'memory': 30, 'api_calls': 1},
            AnalysisStage.LEADERSHIP_DECISION_SIMULATION: {'time': 5, 'memory': 20, 'api_calls': 1},
            AnalysisStage.REGULATORY_SUBMISSION: {'time': 20, 'memory': 40, 'api_calls': 1},
            AnalysisStage.PUBLIC_COMMENT_SIMULATION: {'time': 60, 'memory': 200, 'api_calls': 10},
            AnalysisStage.PUBLIC_COMMENT_ANALYSIS: {'time': 30, 'memory': 100, 'api_calls': 5},
            AnalysisStage.FINAL_RULE_DRAFTING: {'time': 25, 'memory': 60, 'api_calls': 2},
            AnalysisStage.EXPORT_RESULTS: {'time': 1, 'memory': 20, 'api_calls': 0}
        }
        
        total_time = 0
        total_memory = 0
        total_api_calls = 0
        
        stage_estimates = {}
        
        for stage in enabled_stages:
            if stage in base_estimates:
                # Apply document limits
                stage_config = self.stage_configs.get(stage, StageConfig())
                effective_doc_count = document_count
                
                if stage_config.document_limit:
                    effective_doc_count = min(document_count, stage_config.document_limit)
                
                # Calculate estimates
                base = base_estimates[stage]
                stage_time = base['time'] * effective_doc_count
                stage_memory = base['memory'] * min(effective_doc_count, 10)  # Memory doesn't scale linearly
                stage_api_calls = base['api_calls'] * effective_doc_count
                
                # Meta-analysis and export don't scale with document count
                if stage in [AnalysisStage.META_ANALYSIS, AnalysisStage.EXPORT_RESULTS]:
                    stage_time = base['time']
                    stage_memory = base['memory']
                    stage_api_calls = base['api_calls']
                
                stage_estimates[stage.value] = {
                    'estimated_time_seconds': stage_time,
                    'estimated_memory_mb': stage_memory,
                    'estimated_api_calls': stage_api_calls,
                    'document_count': effective_doc_count
                }
                
                total_time += stage_time
                total_memory = max(total_memory, stage_memory)  # Peak memory usage
                total_api_calls += stage_api_calls
        
        return {
            'total_estimated_time_seconds': total_time,
            'peak_estimated_memory_mb': total_memory,
            'total_estimated_api_calls': total_api_calls,
            'stage_estimates': stage_estimates,
            'within_limits': {
                'time': total_time <= self.resource_limits.max_total_processing_time,
                'memory': total_memory <= self.resource_limits.max_memory_usage,
                'api_calls': total_api_calls <= (self.resource_limits.max_api_calls_per_minute * (total_time / 60))
            }
        }
    
    def create_execution_plan(self, document_count: int) -> Dict[str, Any]:
        """
        Create an execution plan for the configured stages.
        
        Args:
            document_count: Number of documents to process
            
        Returns:
            Dictionary with execution plan
        """
        # Validate configuration
        validation_errors = self.validate_stage_configuration()
        if validation_errors:
            return {
                'valid': False,
                'errors': validation_errors,
                'stages': [],
                'resource_estimates': {}
            }
        
        # Get enabled stages
        enabled_stages = self.get_enabled_stages()
        
        # Create stage execution details
        stage_details = []
        for stage in enabled_stages:
            config = self.stage_configs[stage]
            
            # Determine effective document limit
            effective_limit = document_count
            if config.document_limit:
                effective_limit = min(document_count, config.document_limit)
            
            stage_details.append({
                'stage': stage.value,
                'enabled': config.enabled,
                'document_limit': effective_limit,
                'time_limit_seconds': config.time_limit_seconds,
                'memory_limit_mb': config.memory_limit_mb,
                'retry_attempts': config.retry_attempts,
                'parameters': config.parameters
            })
        
        # Get resource estimates
        resource_estimates = self.estimate_resource_usage(document_count)
        
        return {
            'valid': True,
            'errors': [],
            'stages': stage_details,
            'resource_estimates': resource_estimates,
            'total_stages': len(enabled_stages),
            'estimated_duration_minutes': resource_estimates['total_estimated_time_seconds'] / 60
        }
    
    def get_stage_config(self, stage: AnalysisStage) -> Optional[StageConfig]:
        """
        Get configuration for a specific stage.
        
        Args:
            stage: Analysis stage
            
        Returns:
            StageConfig or None if not configured
        """
        return self.stage_configs.get(stage)
    
    def set_resource_limits(self, limits: ResourceLimits) -> bool:
        """
        Set resource limits.
        
        Args:
            limits: Resource limits configuration
            
        Returns:
            True if valid and applied
        """
        try:
            errors = limits.validate()
            if errors:
                logger.error(f"Invalid resource limits: {errors}")
                return False
            
            self.resource_limits = limits
            logger.info("Updated resource limits")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set resource limits: {e}")
            return False
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current configuration.
        
        Returns:
            Dictionary with configuration summary
        """
        enabled_stages = self.get_enabled_stages()
        
        return {
            'enabled_stages': [stage.value for stage in enabled_stages],
            'total_enabled_stages': len(enabled_stages),
            'resource_limits': {
                'max_documents_per_stage': self.resource_limits.max_documents_per_stage,
                'max_total_processing_time': self.resource_limits.max_total_processing_time,
                'max_memory_usage': self.resource_limits.max_memory_usage,
                'max_concurrent_operations': self.resource_limits.max_concurrent_operations,
                'max_api_calls_per_minute': self.resource_limits.max_api_calls_per_minute
            },
            'stage_configurations': {
                stage.value: {
                    'enabled': config.enabled,
                    'document_limit': config.document_limit,
                    'time_limit_seconds': config.time_limit_seconds,
                    'memory_limit_mb': config.memory_limit_mb,
                    'retry_attempts': config.retry_attempts,
                    'parameters': config.parameters
                }
                for stage, config in self.stage_configs.items()
            }
        }