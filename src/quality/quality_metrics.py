"""Continuous improvement and quality metrics system for medical record analysis."""
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import statistics
from enum import Enum

from .hallucination_detector import ValidationIssue, ValidationSeverity, ValidationType
from ..models import AnalysisReport
from ..utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of quality metrics."""
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    RELIABILITY = "reliability"
    PERFORMANCE = "performance"

@dataclass
class QualityMetric:
    """Individual quality metric."""
    metric_id: str
    metric_type: MetricType
    name: str
    value: float
    target_value: float
    timestamp: datetime
    patient_id: Optional[str] = None
    component: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_meeting_target(self) -> bool:
        """Check if metric meets target value."""
        return self.value >= self.target_value
    
    @property
    def deviation_from_target(self) -> float:
        """Calculate deviation from target (positive = above target)."""
        return self.value - self.target_value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/reporting."""
        return {
            "metric_id": self.metric_id,
            "metric_type": self.metric_type.value,
            "name": self.name,
            "value": self.value,
            "target_value": self.target_value,
            "timestamp": self.timestamp.isoformat(),
            "patient_id": self.patient_id,
            "component": self.component,
            "is_meeting_target": self.is_meeting_target,
            "deviation_from_target": self.deviation_from_target,
            "metadata": self.metadata
        }

@dataclass
class QualityTrend:
    """Quality trend analysis."""
    metric_name: str
    time_period: str
    trend_direction: str  # "improving", "declining", "stable"
    trend_strength: float  # 0-1, how strong the trend is
    current_value: float
    previous_value: float
    change_percentage: float
    significance: str  # "significant", "moderate", "minor"

class QualityMetricsCollector:
    """Collects and analyzes quality metrics for continuous improvement."""
    
    def __init__(self, 
                 audit_logger: Optional[AuditLogger] = None,
                 max_history_size: int = 10000):
        """
        Initialize quality metrics collector.
        
        Args:
            audit_logger: Optional audit logger for compliance
            max_history_size: Maximum number of metrics to keep in memory
        """
        self.audit_logger = audit_logger
        self.max_history_size = max_history_size
        
        # Metric storage
        self.metrics_history: deque = deque(maxlen=max_history_size)
        self.metrics_by_type: Dict[MetricType, List[QualityMetric]] = defaultdict(list)
        self.metrics_by_component: Dict[str, List[QualityMetric]] = defaultdict(list)
        
        # Quality targets (can be configured)
        self.quality_targets = {
            "overall_accuracy": 0.90,
            "data_completeness": 0.95,
            "validation_pass_rate": 0.85,
            "research_credibility": 0.75,
            "processing_time": 300.0,  # seconds
            "error_rate": 0.05,
            "hallucination_detection_rate": 0.98,
            "terminology_accuracy": 0.92,
            "source_verification_rate": 0.90,
            "research_relevance": 0.80
        }
        
        # Pattern detection
        self.failure_patterns: Dict[str, int] = defaultdict(int)
        self.improvement_opportunities: List[Dict[str, Any]] = []
        
        # Statistics
        self.collection_stats = {
            "total_metrics_collected": 0,
            "metrics_meeting_targets": 0,
            "metrics_below_targets": 0,
            "last_collection_time": None,
            "collection_start_time": datetime.now()
        }
        
        logger.info("Quality metrics collector initialized")
    
    def collect_analysis_metrics(self, 
                                analysis_report: AnalysisReport,
                                validation_result: Dict[str, Any],
                                processing_time: float) -> List[QualityMetric]:
        """
        Collect quality metrics from analysis results.
        
        Args:
            analysis_report: Complete analysis report
            validation_result: Validation results from data validator
            processing_time: Total processing time in seconds
            
        Returns:
            List[QualityMetric]: Collected metrics
        """
        metrics = []
        timestamp = datetime.now()
        patient_id = analysis_report.patient_data.patient_id
        
        try:
            # 1. Overall accuracy metric
            overall_accuracy = analysis_report.quality_metrics.get("overall_quality_score", 0.0)
            metrics.append(QualityMetric(
                metric_id=f"ACC_{timestamp.strftime('%Y%m%d_%H%M%S')}_001",
                metric_type=MetricType.ACCURACY,
                name="overall_accuracy",
                value=overall_accuracy,
                target_value=self.quality_targets["overall_accuracy"],
                timestamp=timestamp,
                patient_id=patient_id,
                component="overall_system"
            ))
            
            # 2. Data completeness metric
            completeness_score = analysis_report.quality_metrics.get("data_completeness_score", 0.0)
            metrics.append(QualityMetric(
                metric_id=f"COMP_{timestamp.strftime('%Y%m%d_%H%M%S')}_001",
                metric_type=MetricType.COMPLETENESS,
                name="data_completeness",
                value=completeness_score,
                target_value=self.quality_targets["data_completeness"],
                timestamp=timestamp,
                patient_id=patient_id,
                component="data_extraction"
            ))
            
            # 3. Validation pass rate
            validation_status = validation_result.get("validation_status", "FAILED")
            validation_pass = 1.0 if validation_status in ["PASSED", "PASSED_WITH_WARNINGS"] else 0.0
            metrics.append(QualityMetric(
                metric_id=f"VAL_{timestamp.strftime('%Y%m%d_%H%M%S')}_001",
                metric_type=MetricType.RELIABILITY,
                name="validation_pass_rate",
                value=validation_pass,
                target_value=self.quality_targets["validation_pass_rate"],
                timestamp=timestamp,
                patient_id=patient_id,
                component="validation_system",
                metadata={"validation_status": validation_status}
            ))
            
            # 4. Research credibility metric
            research_confidence = analysis_report.research_analysis.analysis_confidence
            metrics.append(QualityMetric(
                metric_id=f"RES_{timestamp.strftime('%Y%m%d_%H%M%S')}_001",
                metric_type=MetricType.ACCURACY,
                name="research_credibility",
                value=research_confidence,
                target_value=self.quality_targets["research_credibility"],
                timestamp=timestamp,
                patient_id=patient_id,
                component="research_correlation"
            ))
            
            # 5. Processing time metric (inverted - lower is better)
            time_score = max(0.0, 1.0 - (processing_time / self.quality_targets["processing_time"]))
            metrics.append(QualityMetric(
                metric_id=f"PERF_{timestamp.strftime('%Y%m%d_%H%M%S')}_001",
                metric_type=MetricType.PERFORMANCE,
                name="processing_time",
                value=time_score,
                target_value=0.8,  # Target: complete within 80% of max time
                timestamp=timestamp,
                patient_id=patient_id,
                component="workflow_orchestrator",
                metadata={"actual_time_seconds": processing_time}
            ))
            
            # 6. Error rate metric (from validation issues)
            total_issues = validation_result.get("total_issues", 0)
            error_issues = len(validation_result.get("issues_by_severity", {}).get("error", []))
            critical_issues = len(validation_result.get("issues_by_severity", {}).get("critical", []))
            
            error_rate = (error_issues + critical_issues * 2) / max(1, total_issues + 10)  # Normalize
            error_score = max(0.0, 1.0 - error_rate)
            
            metrics.append(QualityMetric(
                metric_id=f"ERR_{timestamp.strftime('%Y%m%d_%H%M%S')}_001",
                metric_type=MetricType.RELIABILITY,
                name="error_rate",
                value=error_score,
                target_value=1.0 - self.quality_targets["error_rate"],
                timestamp=timestamp,
                patient_id=patient_id,
                component="error_handling",
                metadata={
                    "total_issues": total_issues,
                    "error_issues": error_issues,
                    "critical_issues": critical_issues
                }
            ))
            
            # 7. Medical terminology accuracy
            terminology_issues = len(validation_result.get("issues_by_type", {}).get("medical_terminology", []))
            total_conditions = len(analysis_report.medical_summary.key_conditions)
            terminology_accuracy = max(0.0, 1.0 - (terminology_issues / max(1, total_conditions)))
            
            metrics.append(QualityMetric(
                metric_id=f"TERM_{timestamp.strftime('%Y%m%d_%H%M%S')}_001",
                metric_type=MetricType.ACCURACY,
                name="terminology_accuracy",
                value=terminology_accuracy,
                target_value=self.quality_targets["terminology_accuracy"],
                timestamp=timestamp,
                patient_id=patient_id,
                component="medical_summarization",
                metadata={
                    "terminology_issues": terminology_issues,
                    "total_conditions": total_conditions
                }
            ))
            
            # Store metrics
            for metric in metrics:
                self._store_metric(metric)
            
            # Update statistics
            self._update_collection_statistics(metrics)
            
            # Analyze patterns
            self._analyze_failure_patterns(validation_result)
            
            logger.info(f"Collected {len(metrics)} quality metrics for patient {patient_id}")
            
        except Exception as e:
            logger.error(f"Error collecting quality metrics: {str(e)}")
            # Create error metric
            error_metric = QualityMetric(
                metric_id=f"ERR_{timestamp.strftime('%Y%m%d_%H%M%S')}_COLLECT",
                metric_type=MetricType.RELIABILITY,
                name="metric_collection_error",
                value=0.0,
                target_value=1.0,
                timestamp=timestamp,
                patient_id=patient_id,
                component="quality_metrics",
                metadata={"error": str(e)}
            )
            metrics.append(error_metric)
            self._store_metric(error_metric)
        
        return metrics
    
    def _store_metric(self, metric: QualityMetric):
        """Store metric in various collections."""
        self.metrics_history.append(metric)
        self.metrics_by_type[metric.metric_type].append(metric)
        if metric.component:
            self.metrics_by_component[metric.component].append(metric)
    
    def _update_collection_statistics(self, metrics: List[QualityMetric]):
        """Update collection statistics."""
        self.collection_stats["total_metrics_collected"] += len(metrics)
        self.collection_stats["last_collection_time"] = datetime.now()
        
        for metric in metrics:
            if metric.is_meeting_target:
                self.collection_stats["metrics_meeting_targets"] += 1
            else:
                self.collection_stats["metrics_below_targets"] += 1
    
    def _analyze_failure_patterns(self, validation_result: Dict[str, Any]):
        """Analyze failure patterns for improvement opportunities."""
        issues_by_type = validation_result.get("issues_by_type", {})
        
        for issue_type, issues in issues_by_type.items():
            if len(issues) > 0:
                self.failure_patterns[issue_type] += len(issues)
        
        # Identify improvement opportunities
        if validation_result.get("validation_status") == "FAILED":
            opportunity = {
                "timestamp": datetime.now().isoformat(),
                "validation_status": validation_result.get("validation_status"),
                "total_issues": validation_result.get("total_issues", 0),
                "primary_issue_types": list(issues_by_type.keys())[:3],
                "recommendations": validation_result.get("recommendations", [])
            }
            self.improvement_opportunities.append(opportunity)
            
            # Keep only recent opportunities
            if len(self.improvement_opportunities) > 100:
                self.improvement_opportunities = self.improvement_opportunities[-100:]
    
    def get_quality_dashboard(self, time_period_days: int = 30) -> Dict[str, Any]:
        """
        Generate comprehensive quality dashboard.
        
        Args:
            time_period_days: Number of days to include in analysis
            
        Returns:
            Dict[str, Any]: Quality dashboard data
        """
        cutoff_date = datetime.now() - timedelta(days=time_period_days)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_date]
        
        if not recent_metrics:
            return {
                "summary": "No metrics available for the specified time period",
                "time_period_days": time_period_days,
                "total_metrics": 0
            }
        
        # Overall summary
        total_metrics = len(recent_metrics)
        meeting_targets = len([m for m in recent_metrics if m.is_meeting_target])
        target_achievement_rate = meeting_targets / total_metrics if total_metrics > 0 else 0
        
        # Metrics by type
        metrics_by_type = {}
        for metric_type in MetricType:
            type_metrics = [m for m in recent_metrics if m.metric_type == metric_type]
            if type_metrics:
                avg_value = statistics.mean([m.value for m in type_metrics])
                avg_target = statistics.mean([m.target_value for m in type_metrics])
                meeting_target_rate = len([m for m in type_metrics if m.is_meeting_target]) / len(type_metrics)
                
                metrics_by_type[metric_type.value] = {
                    "count": len(type_metrics),
                    "average_value": avg_value,
                    "average_target": avg_target,
                    "target_achievement_rate": meeting_target_rate,
                    "trend": self._calculate_trend(type_metrics)
                }
        
        # Component performance
        component_performance = {}
        for component, comp_metrics in self.metrics_by_component.items():
            comp_recent = [m for m in comp_metrics if m.timestamp >= cutoff_date]
            if comp_recent:
                avg_value = statistics.mean([m.value for m in comp_recent])
                meeting_target_rate = len([m for m in comp_recent if m.is_meeting_target]) / len(comp_recent)
                
                component_performance[component] = {
                    "count": len(comp_recent),
                    "average_value": avg_value,
                    "target_achievement_rate": meeting_target_rate,
                    "trend": self._calculate_trend(comp_recent)
                }
        
        # Top issues and improvement opportunities
        recent_patterns = {}
        for pattern, count in self.failure_patterns.items():
            if count > 0:
                recent_patterns[pattern] = count
        
        top_issues = sorted(recent_patterns.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Quality trends
        quality_trends = self._analyze_quality_trends(recent_metrics)
        
        return {
            "summary": {
                "time_period_days": time_period_days,
                "total_metrics": total_metrics,
                "target_achievement_rate": target_achievement_rate,
                "overall_quality_score": target_achievement_rate,
                "metrics_meeting_targets": meeting_targets,
                "metrics_below_targets": total_metrics - meeting_targets
            },
            "metrics_by_type": metrics_by_type,
            "component_performance": component_performance,
            "top_issues": [{"issue_type": issue, "count": count} for issue, count in top_issues],
            "quality_trends": quality_trends,
            "improvement_opportunities": self.improvement_opportunities[-10:],  # Recent opportunities
            "collection_statistics": self.collection_stats,
            "recommendations": self._generate_improvement_recommendations(recent_metrics)
        }
    
    def _calculate_trend(self, metrics: List[QualityMetric]) -> Dict[str, Any]:
        """Calculate trend for a set of metrics."""
        if len(metrics) < 2:
            return {"direction": "insufficient_data", "strength": 0.0}
        
        # Sort by timestamp
        sorted_metrics = sorted(metrics, key=lambda m: m.timestamp)
        
        # Calculate simple trend
        values = [m.value for m in sorted_metrics]
        
        # Linear regression slope approximation
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(values)
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Determine trend direction and strength
        if abs(slope) < 0.01:
            direction = "stable"
            strength = 0.0
        elif slope > 0:
            direction = "improving"
            strength = min(1.0, abs(slope) * 10)
        else:
            direction = "declining"
            strength = min(1.0, abs(slope) * 10)
        
        return {
            "direction": direction,
            "strength": strength,
            "slope": slope,
            "current_value": values[-1],
            "previous_value": values[0],
            "change_percentage": ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0
        }
    
    def _analyze_quality_trends(self, metrics: List[QualityMetric]) -> List[QualityTrend]:
        """Analyze quality trends across different metrics."""
        trends = []
        
        # Group metrics by name
        metrics_by_name = defaultdict(list)
        for metric in metrics:
            metrics_by_name[metric.name].append(metric)
        
        for metric_name, metric_list in metrics_by_name.items():
            if len(metric_list) >= 2:
                trend_data = self._calculate_trend(metric_list)
                
                # Determine significance
                if trend_data["strength"] > 0.7:
                    significance = "significant"
                elif trend_data["strength"] > 0.3:
                    significance = "moderate"
                else:
                    significance = "minor"
                
                trend = QualityTrend(
                    metric_name=metric_name,
                    time_period="recent",
                    trend_direction=trend_data["direction"],
                    trend_strength=trend_data["strength"],
                    current_value=trend_data["current_value"],
                    previous_value=trend_data["previous_value"],
                    change_percentage=trend_data["change_percentage"],
                    significance=significance
                )
                trends.append(trend)
        
        return trends
    
    def _generate_improvement_recommendations(self, metrics: List[QualityMetric]) -> List[str]:
        """Generate improvement recommendations based on metrics analysis."""
        recommendations = []
        
        # Analyze metrics below targets
        below_target_metrics = [m for m in metrics if not m.is_meeting_target]
        
        if not below_target_metrics:
            recommendations.append("All quality metrics are meeting targets - maintain current performance")
            return recommendations
        
        # Group by metric name
        below_target_by_name = defaultdict(list)
        for metric in below_target_metrics:
            below_target_by_name[metric.name].append(metric)
        
        # Generate specific recommendations
        for metric_name, metric_list in below_target_by_name.items():
            avg_deviation = statistics.mean([m.deviation_from_target for m in metric_list])
            
            if metric_name == "overall_accuracy":
                if avg_deviation < -0.1:
                    recommendations.append("Overall accuracy is significantly below target - review data extraction and validation processes")
                else:
                    recommendations.append("Overall accuracy needs improvement - focus on data quality and validation")
            
            elif metric_name == "data_completeness":
                recommendations.append("Data completeness is below target - review XML parsing and data extraction logic")
            
            elif metric_name == "validation_pass_rate":
                recommendations.append("Validation pass rate is low - investigate common validation failures and improve data quality")
            
            elif metric_name == "research_credibility":
                recommendations.append("Research credibility is below target - review research search algorithms and source quality")
            
            elif metric_name == "processing_time":
                recommendations.append("Processing time is above target - optimize workflow performance and consider parallel processing")
            
            elif metric_name == "terminology_accuracy":
                recommendations.append("Medical terminology accuracy needs improvement - update terminology validation dictionaries")
        
        # Analyze failure patterns
        if self.failure_patterns:
            top_pattern = max(self.failure_patterns.items(), key=lambda x: x[1])
            recommendations.append(f"Most common issue type is '{top_pattern[0]}' - prioritize addressing this pattern")
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def get_metric_history(self, metric_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        matching_metrics = [
            m for m in self.metrics_history 
            if m.name == metric_name and m.timestamp >= cutoff_date
        ]
        
        return [m.to_dict() for m in sorted(matching_metrics, key=lambda x: x.timestamp)]
    
    def export_metrics(self, format_type: str = "json") -> str:
        """Export metrics data in specified format."""
        if format_type.lower() == "json":
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "total_metrics": len(self.metrics_history),
                "collection_stats": self.collection_stats,
                "quality_targets": self.quality_targets,
                "failure_patterns": dict(self.failure_patterns),
                "metrics": [m.to_dict() for m in self.metrics_history]
            }
            return json.dumps(export_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def clear_metrics(self, older_than_days: Optional[int] = None):
        """Clear metrics data."""
        if older_than_days is None:
            # Clear all metrics
            self.metrics_history.clear()
            self.metrics_by_type.clear()
            self.metrics_by_component.clear()
            self.failure_patterns.clear()
            self.improvement_opportunities.clear()
            logger.info("All quality metrics cleared")
        else:
            # Clear metrics older than specified days
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            
            # Filter metrics
            self.metrics_history = deque(
                [m for m in self.metrics_history if m.timestamp >= cutoff_date],
                maxlen=self.max_history_size
            )
            
            # Rebuild other collections
            self.metrics_by_type.clear()
            self.metrics_by_component.clear()
            
            for metric in self.metrics_history:
                self.metrics_by_type[metric.metric_type].append(metric)
                if metric.component:
                    self.metrics_by_component[metric.component].append(metric)
            
            logger.info(f"Cleared quality metrics older than {older_than_days} days")
    
    def get_quality_score(self) -> float:
        """Get overall quality score based on recent metrics."""
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp >= datetime.now() - timedelta(days=7)
        ]
        
        if not recent_metrics:
            return 0.0
        
        meeting_targets = len([m for m in recent_metrics if m.is_meeting_target])
        return meeting_targets / len(recent_metrics)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get quality statistics summary.
        
        This is an alias for get_quality_dashboard with default parameters,
        providing backward compatibility.
        
        Returns:
            Dict[str, Any]: Quality statistics and dashboard data
        """
        return self.get_quality_dashboard(time_period_days=30)