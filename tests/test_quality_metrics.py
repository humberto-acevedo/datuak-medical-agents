"""Tests for quality metrics and continuous improvement system."""
import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta
import json

from src.quality.quality_metrics import (
    QualityMetricsCollector, QualityMetric, QualityTrend, MetricType
)
from src.models import PatientData, MedicalSummary, ResearchAnalysis, AnalysisReport


class TestQualityMetric:
    """Test QualityMetric class."""
    
    def test_quality_metric_creation(self):
        """Test quality metric creation."""
        timestamp = datetime.now()
        metric = QualityMetric(
            metric_id="TEST_001",
            metric_type=MetricType.ACCURACY,
            name="test_accuracy",
            value=0.85,
            target_value=0.90,
            timestamp=timestamp,
            patient_id="PAT123",
            component="test_component"
        )
        
        assert metric.metric_id == "TEST_001"
        assert metric.metric_type == MetricType.ACCURACY
        assert metric.name == "test_accuracy"
        assert metric.value == 0.85
        assert metric.target_value == 0.90
        assert metric.timestamp == timestamp
        assert metric.patient_id == "PAT123"
        assert metric.component == "test_component"
    
    def test_quality_metric_target_checking(self):
        """Test quality metric target checking."""
        # Meeting target
        metric_good = QualityMetric(
            metric_id="TEST_001",
            metric_type=MetricType.ACCURACY,
            name="test_metric",
            value=0.95,
            target_value=0.90,
            timestamp=datetime.now()
        )
        
        assert metric_good.is_meeting_target is True
        assert metric_good.deviation_from_target == 0.05
        
        # Below target
        metric_bad = QualityMetric(
            metric_id="TEST_002",
            metric_type=MetricType.ACCURACY,
            name="test_metric",
            value=0.85,
            target_value=0.90,
            timestamp=datetime.now()
        )
        
        assert metric_bad.is_meeting_target is False
        assert metric_bad.deviation_from_target == -0.05
    
    def test_quality_metric_to_dict(self):
        """Test quality metric dictionary conversion."""
        timestamp = datetime.now()
        metric = QualityMetric(
            metric_id="TEST_001",
            metric_type=MetricType.PERFORMANCE,
            name="test_performance",
            value=0.75,
            target_value=0.80,
            timestamp=timestamp,
            metadata={"test_key": "test_value"}
        )
        
        metric_dict = metric.to_dict()
        
        assert metric_dict["metric_id"] == "TEST_001"
        assert metric_dict["metric_type"] == "performance"
        assert metric_dict["name"] == "test_performance"
        assert metric_dict["value"] == 0.75
        assert metric_dict["target_value"] == 0.80
        assert metric_dict["is_meeting_target"] is False
        assert metric_dict["deviation_from_target"] == -0.05
        assert metric_dict["metadata"]["test_key"] == "test_value"


class TestQualityMetricsCollector:
    """Test QualityMetricsCollector class."""
    
    @pytest.fixture
    def collector(self):
        """Create quality metrics collector."""
        return QualityMetricsCollector(max_history_size=1000)
    
    @pytest.fixture
    def sample_analysis_report(self):
        """Create sample analysis report."""
        from src.models.patient_data import Demographics
        
        patient_data = PatientData(
            patient_id="PAT123",
            name="John Smith",
            demographics=Demographics(age=45, gender="Male"),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient>test</patient>",
            extraction_timestamp=datetime.now()
        )
        
        from src.models.medical_summary import Condition
        
        medical_summary = MedicalSummary(
            patient_id="PAT123",
            summary_text="Patient has hypertension and diabetes.",
            key_conditions=[
                Condition(name="hypertension", confidence_score=0.9),
                Condition(name="diabetes", confidence_score=0.8)
            ],
            medication_summary="Patient takes antihypertensive medications.",
            procedure_summary="No recent procedures.",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.9,
            missing_data_indicators=[]
        )
        
        from src.models.research_analysis import ResearchFinding
        from src.models.medical_summary import Condition
        
        research_analysis = ResearchAnalysis(
            patient_id="PAT123",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[Condition(name="hypertension"), Condition(name="diabetes")],
            research_findings=[
                ResearchFinding(
                    title="Hypertension Study",
                    authors=["Smith, J."],
                    publication_date="2023-01-01",
                    journal="Medical Journal",
                    citation="Smith J. Hypertension Study. Med J. 2023."
                )
            ],
            condition_research_correlations={},
            categorized_findings={},
            research_insights=["Test insight"],
            clinical_recommendations=["Test recommendation"],
            analysis_confidence=0.85,
            total_papers_reviewed=10,
            relevant_papers_found=5
        )
        
        return AnalysisReport(
            report_id="RPT_001",
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            quality_metrics={
                "overall_quality_score": 0.88,
                "data_completeness_score": 0.92
            }
        )
    
    @pytest.fixture
    def sample_validation_result(self):
        """Create sample validation result."""
        return {
            "validation_status": "PASSED",
            "total_issues": 3,
            "issues_by_severity": {
                "warning": [1, 2],
                "info": [3]
            },
            "issues_by_type": {
                "medical_terminology": [1],
                "source_verification": [2, 3]
            },
            "recommendations": ["Review terminology accuracy"]
        }
    
    def test_collector_initialization(self, collector):
        """Test collector initialization."""
        assert collector.max_history_size == 1000
        assert len(collector.metrics_history) == 0
        assert len(collector.quality_targets) > 5
        assert collector.collection_stats["total_metrics_collected"] == 0
    
    def test_collect_analysis_metrics(self, collector, sample_analysis_report, sample_validation_result):
        """Test collecting metrics from analysis results."""
        processing_time = 45.5
        
        metrics = collector.collect_analysis_metrics(
            sample_analysis_report,
            sample_validation_result,
            processing_time
        )
        
        # Should collect multiple metrics
        assert len(metrics) >= 5
        
        # Check metric types
        metric_names = [m.name for m in metrics]
        expected_names = [
            "overall_accuracy", "data_completeness", "validation_pass_rate",
            "research_credibility", "processing_time", "error_rate", "terminology_accuracy"
        ]
        
        for expected_name in expected_names:
            assert expected_name in metric_names, f"Missing metric: {expected_name}"
        
        # Check that metrics are stored
        assert len(collector.metrics_history) == len(metrics)
        assert collector.collection_stats["total_metrics_collected"] == len(metrics)
    
    def test_collect_metrics_with_failed_validation(self, collector, sample_analysis_report):
        """Test collecting metrics with failed validation."""
        failed_validation = {
            "validation_status": "FAILED",
            "total_issues": 10,
            "issues_by_severity": {
                "critical": [1, 2],
                "error": [3, 4, 5],
                "warning": [6, 7, 8, 9, 10]
            },
            "issues_by_type": {
                "medical_terminology": [1, 2, 3],
                "source_verification": [4, 5],
                "logical_coherence": [6, 7, 8, 9, 10]
            }
        }
        
        metrics = collector.collect_analysis_metrics(
            sample_analysis_report,
            failed_validation,
            120.0
        )
        
        # Should still collect metrics
        assert len(metrics) >= 5
        
        # Validation pass rate should be 0
        validation_metrics = [m for m in metrics if m.name == "validation_pass_rate"]
        assert len(validation_metrics) == 1
        assert validation_metrics[0].value == 0.0
        
        # Should record failure patterns
        assert len(collector.failure_patterns) > 0
        assert "medical_terminology" in collector.failure_patterns
        
        # Should record improvement opportunity
        assert len(collector.improvement_opportunities) > 0
    
    def test_quality_dashboard_empty(self, collector):
        """Test quality dashboard with no metrics."""
        dashboard = collector.get_quality_dashboard()
        
        assert dashboard["summary"] == "No metrics available for the specified time period"
        assert dashboard["total_metrics"] == 0
    
    def test_quality_dashboard_with_metrics(self, collector, sample_analysis_report, sample_validation_result):
        """Test quality dashboard with metrics."""
        # Collect some metrics
        for i in range(3):
            collector.collect_analysis_metrics(
                sample_analysis_report,
                sample_validation_result,
                30.0 + i * 10
            )
        
        dashboard = collector.get_quality_dashboard()
        
        # Check dashboard structure
        assert "summary" in dashboard
        assert "metrics_by_type" in dashboard
        assert "component_performance" in dashboard
        assert "quality_trends" in dashboard
        assert "recommendations" in dashboard
        
        # Check summary
        summary = dashboard["summary"]
        assert summary["total_metrics"] > 0
        assert 0 <= summary["target_achievement_rate"] <= 1
        assert summary["metrics_meeting_targets"] + summary["metrics_below_targets"] == summary["total_metrics"]
        
        # Check metrics by type
        assert len(dashboard["metrics_by_type"]) > 0
        
        # Check component performance
        assert len(dashboard["component_performance"]) > 0
    
    def test_metric_history_retrieval(self, collector, sample_analysis_report, sample_validation_result):
        """Test retrieving metric history."""
        # Collect metrics
        collector.collect_analysis_metrics(
            sample_analysis_report,
            sample_validation_result,
            45.0
        )
        
        # Get history for specific metric
        history = collector.get_metric_history("overall_accuracy", days=30)
        
        assert len(history) == 1
        assert history[0]["name"] == "overall_accuracy"
        assert "timestamp" in history[0]
        assert "value" in history[0]
    
    def test_trend_calculation(self, collector):
        """Test trend calculation."""
        # Create metrics with improving trend
        base_time = datetime.now()
        improving_metrics = []
        
        for i in range(5):
            metric = QualityMetric(
                metric_id=f"TREND_{i}",
                metric_type=MetricType.ACCURACY,
                name="test_metric",
                value=0.5 + (i * 0.1),  # Improving from 0.5 to 0.9
                target_value=0.8,
                timestamp=base_time + timedelta(hours=i)
            )
            improving_metrics.append(metric)
        
        trend = collector._calculate_trend(improving_metrics)
        
        assert trend["direction"] == "improving"
        assert trend["strength"] > 0
        assert trend["current_value"] == 0.9
        assert trend["previous_value"] == 0.5
        assert trend["change_percentage"] > 0
    
    def test_improvement_recommendations(self, collector, sample_analysis_report):
        """Test improvement recommendations generation."""
        # Create validation result with issues
        problematic_validation = {
            "validation_status": "WARNING",
            "total_issues": 8,
            "issues_by_severity": {
                "warning": [1, 2, 3, 4, 5, 6, 7, 8]
            },
            "issues_by_type": {
                "medical_terminology": [1, 2, 3, 4],
                "data_consistency": [5, 6, 7, 8]
            }
        }
        
        # Collect metrics
        collector.collect_analysis_metrics(
            sample_analysis_report,
            problematic_validation,
            200.0  # Slow processing
        )
        
        # Get dashboard with recommendations
        dashboard = collector.get_quality_dashboard()
        recommendations = dashboard["recommendations"]
        
        assert len(recommendations) > 0
        assert any("terminology" in rec.lower() for rec in recommendations)
    
    def test_export_metrics(self, collector, sample_analysis_report, sample_validation_result):
        """Test metrics export."""
        # Collect some metrics
        collector.collect_analysis_metrics(
            sample_analysis_report,
            sample_validation_result,
            45.0
        )
        
        # Export as JSON
        export_data = collector.export_metrics("json")
        
        # Should be valid JSON
        parsed_data = json.loads(export_data)
        
        assert "export_timestamp" in parsed_data
        assert "total_metrics" in parsed_data
        assert "metrics" in parsed_data
        assert len(parsed_data["metrics"]) > 0
        
        # Test invalid format
        with pytest.raises(ValueError):
            collector.export_metrics("invalid_format")
    
    def test_clear_metrics(self, collector, sample_analysis_report, sample_validation_result):
        """Test clearing metrics."""
        # Collect some metrics
        collector.collect_analysis_metrics(
            sample_analysis_report,
            sample_validation_result,
            45.0
        )
        
        assert len(collector.metrics_history) > 0
        
        # Clear all metrics
        collector.clear_metrics()
        
        assert len(collector.metrics_history) == 0
        assert len(collector.metrics_by_type) == 0
        assert len(collector.metrics_by_component) == 0
    
    def test_clear_old_metrics(self, collector):
        """Test clearing old metrics."""
        # Create old and new metrics
        old_time = datetime.now() - timedelta(days=10)
        new_time = datetime.now()
        
        old_metric = QualityMetric(
            metric_id="OLD_001",
            metric_type=MetricType.ACCURACY,
            name="old_metric",
            value=0.8,
            target_value=0.9,
            timestamp=old_time
        )
        
        new_metric = QualityMetric(
            metric_id="NEW_001",
            metric_type=MetricType.ACCURACY,
            name="new_metric",
            value=0.9,
            target_value=0.9,
            timestamp=new_time
        )
        
        collector._store_metric(old_metric)
        collector._store_metric(new_metric)
        
        assert len(collector.metrics_history) == 2
        
        # Clear metrics older than 5 days
        collector.clear_metrics(older_than_days=5)
        
        # Should only have new metric
        assert len(collector.metrics_history) == 1
        assert collector.metrics_history[0].metric_id == "NEW_001"
    
    def test_quality_score_calculation(self, collector, sample_analysis_report, sample_validation_result):
        """Test overall quality score calculation."""
        # Initially should be 0
        assert collector.get_quality_score() == 0.0
        
        # Collect some metrics
        collector.collect_analysis_metrics(
            sample_analysis_report,
            sample_validation_result,
            45.0
        )
        
        # Should have a quality score
        quality_score = collector.get_quality_score()
        assert 0.0 <= quality_score <= 1.0
    
    def test_failure_pattern_analysis(self, collector, sample_analysis_report):
        """Test failure pattern analysis."""
        # Create validation with specific failure patterns
        validation_with_patterns = {
            "validation_status": "FAILED",
            "total_issues": 6,
            "issues_by_type": {
                "medical_terminology": [1, 2, 3],
                "source_verification": [4, 5],
                "data_consistency": [6]
            }
        }
        
        # Collect metrics multiple times
        for _ in range(3):
            collector.collect_analysis_metrics(
                sample_analysis_report,
                validation_with_patterns,
                60.0
            )
        
        # Should detect patterns
        assert len(collector.failure_patterns) > 0
        assert collector.failure_patterns["medical_terminology"] == 9  # 3 issues × 3 collections
        assert collector.failure_patterns["source_verification"] == 6   # 2 issues × 3 collections
        
        # Should have improvement opportunities
        assert len(collector.improvement_opportunities) == 3


class TestQualityMetricsIntegration:
    """Test quality metrics integration scenarios."""
    
    def test_comprehensive_quality_monitoring(self):
        """Test comprehensive quality monitoring workflow."""
        collector = QualityMetricsCollector()
        
        # Simulate multiple analysis sessions with varying quality
        analysis_sessions = [
            # High quality session
            {
                "quality_metrics": {"overall_quality_score": 0.95, "data_completeness_score": 0.98},
                "research_confidence": 0.92,
                "validation": {"validation_status": "PASSED", "total_issues": 1},
                "processing_time": 35.0
            },
            # Medium quality session
            {
                "quality_metrics": {"overall_quality_score": 0.82, "data_completeness_score": 0.88},
                "research_confidence": 0.75,
                "validation": {"validation_status": "PASSED_WITH_WARNINGS", "total_issues": 5},
                "processing_time": 65.0
            },
            # Lower quality session
            {
                "quality_metrics": {"overall_quality_score": 0.68, "data_completeness_score": 0.72},
                "research_confidence": 0.58,
                "validation": {"validation_status": "WARNING", "total_issues": 12},
                "processing_time": 120.0
            }
        ]
        
        # Collect metrics for each session
        for i, session in enumerate(analysis_sessions):
            from src.models.patient_data import Demographics
            
            patient_data = PatientData(
                patient_id=f"PAT{i:03d}",
                name=f"Patient {i}",
                demographics=Demographics(),
                medical_history=[],
                medications=[],
                procedures=[],
                diagnoses=[],
                raw_xml="<patient>test</patient>",
                extraction_timestamp=datetime.now()
            )
            medical_summary = MedicalSummary(
                patient_id=f"PAT{i:03d}",
                summary_text="Test summary",
                key_conditions=[],
                medication_summary="No medications",
                procedure_summary="No procedures",
                chronological_events=[],
                generated_timestamp=datetime.now(),
                data_quality_score=0.8,
                missing_data_indicators=[]
            )
            research_analysis = ResearchAnalysis(
                patient_id=f"PAT{i:03d}",
                analysis_timestamp=datetime.now(),
                conditions_analyzed=[],
                research_findings=[],
                condition_research_correlations={},
                categorized_findings={},
                research_insights=[],
                clinical_recommendations=[],
                analysis_confidence=session["research_confidence"],
                total_papers_reviewed=0,
                relevant_papers_found=0
            )
            
            report = AnalysisReport(
                report_id=f"RPT_{i:03d}",
                patient_data=patient_data,
                medical_summary=medical_summary,
                research_analysis=research_analysis,
                quality_metrics=session["quality_metrics"]
            )
            
            validation_result = {
                **session["validation"],
                "issues_by_severity": {"warning": list(range(session["validation"]["total_issues"]))},
                "issues_by_type": {"medical_terminology": list(range(session["validation"]["total_issues"]))}
            }
            
            collector.collect_analysis_metrics(report, validation_result, session["processing_time"])
        
        # Generate comprehensive dashboard
        dashboard = collector.get_quality_dashboard()
        
        # Verify dashboard completeness
        assert dashboard["summary"]["total_metrics"] > 15  # Multiple metrics per session
        assert len(dashboard["metrics_by_type"]) > 3
        assert len(dashboard["component_performance"]) > 3
        assert len(dashboard["recommendations"]) > 0
        
        # Check quality trends
        trends = dashboard["quality_trends"]
        assert len(trends) > 0
        
        # Should detect declining trends for some metrics
        declining_trends = [t for t in trends if t.trend_direction == "declining"]
        assert len(declining_trends) > 0, "Should detect declining quality trends"
        
        # Export metrics for analysis
        export_data = collector.export_metrics()
        parsed_export = json.loads(export_data)
        
        assert parsed_export["total_metrics"] > 15
        assert len(parsed_export["metrics"]) > 15
        
        # Overall quality score should reflect mixed performance
        quality_score = collector.get_quality_score()
        assert 0.3 <= quality_score <= 0.8, f"Quality score {quality_score} should reflect mixed performance"