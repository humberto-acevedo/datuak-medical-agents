"""Integration tests for complete report generation and persistence workflow."""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import json

from src.agents.report_generator import ReportGenerator
from src.agents.s3_report_persister import S3ReportPersister
from src.models import (
    PatientData, Demographics, MedicalSummary, Condition,
    ResearchAnalysis, ResearchFinding, AnalysisReport
)
from src.utils import AuditLogger


class TestReportIntegration:
    """Integration tests for the complete report workflow."""
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Create mock audit logger."""
        return Mock(spec=AuditLogger)
    
    @pytest.fixture
    def comprehensive_patient_data(self):
        """Create comprehensive patient data for integration testing."""
        return PatientData(
            patient_id="INTEGRATION_RPT_456",
            name="Sarah Martinez",
            demographics=Demographics(
                age=58,
                gender="F",
                date_of_birth="1966-08-12"
            ),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient>comprehensive integration test data</patient>",
            extraction_timestamp=datetime.now()
        )
    
    @pytest.fixture
    def comprehensive_medical_summary(self):
        """Create comprehensive medical summary for integration testing."""
        conditions = [
            Condition(
                name="Chronic Kidney Disease Stage 3",
                icd_10_code="N18.3",
                severity="moderate",
                confidence_score=0.94,
                status="chronic",
                first_diagnosed="2020-02-15"
            ),
            Condition(
                name="Type 2 Diabetes Mellitus with Complications",
                icd_10_code="E11.9",
                severity="severe",
                confidence_score=0.91,
                status="active",
                first_diagnosed="2015-06-20"
            ),
            Condition(
                name="Hypertensive Heart Disease",
                icd_10_code="I11.9",
                severity="moderate",
                confidence_score=0.87,
                status="chronic",
                first_diagnosed="2018-11-10"
            ),
            Condition(
                name="Diabetic Nephropathy",
                icd_10_code="E11.21",
                severity="severe",
                confidence_score=0.89,
                status="active",
                first_diagnosed="2021-04-05"
            )
        ]
        
        return MedicalSummary(
            patient_id="INTEGRATION_RPT_456",
            summary_text="58-year-old female with complex medical history including advanced diabetes with nephropathy, chronic kidney disease, and hypertensive heart disease. Patient requires comprehensive multidisciplinary care and close monitoring.",
            key_conditions=conditions,
            medication_summary="Insulin glargine 40 units daily, Metformin 1000mg BID, Lisinopril 20mg daily, Furosemide 40mg daily, Atorvastatin 80mg daily",
            procedure_summary="Regular nephrology consultations, annual ophthalmologic exams, quarterly HbA1c monitoring",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.93,
            missing_data_indicators=["recent_echocardiogram", "latest_microalbumin"]
        )
    
    @pytest.fixture
    def comprehensive_research_analysis(self):
        """Create comprehensive research analysis for integration testing."""
        research_findings = [
            ResearchFinding(
                title="SGLT2 Inhibitors in Diabetic Nephropathy: Systematic Review and Meta-Analysis",
                authors=["Chen, L.", "Rodriguez, M.", "Kim, S.", "Patel, N."],
                publication_date="2023-09-15",
                journal="Kidney International",
                doi="10.1016/j.kint.2023.789",
                pmid="37789012",
                relevance_score=0.96,
                key_findings="SGLT2 inhibitors reduce progression of diabetic nephropathy by 35% and cardiovascular events by 28% in CKD patients",
                citation="Chen, L. et al. (2023). SGLT2 Inhibitors in Diabetic Nephropathy. Kidney Int.",
                abstract="Comprehensive meta-analysis of 23 RCTs involving 45,678 patients with diabetic nephropathy",
                study_type="meta-analysis",
                sample_size=45678,
                peer_reviewed=True
            ),
            ResearchFinding(
                title="Intensive Blood Pressure Control in CKD: Long-term Outcomes Study",
                authors=["Williams, R.", "Thompson, K.", "Davis, A."],
                publication_date="2023-11-20",
                journal="New England Journal of Medicine",
                doi="10.1056/nejm2023.567",
                relevance_score=0.93,
                key_findings="Intensive BP control (<130/80) in CKD patients reduces cardiovascular mortality by 22% but increases hypotension risk",
                citation="Williams, R. et al. (2023). Intensive BP Control in CKD. NEJM.",
                study_type="RCT",
                sample_size=15420,
                peer_reviewed=True
            ),
            ResearchFinding(
                title="Multidisciplinary Care in Advanced Diabetes: Quality Improvement Study",
                authors=["Martinez, A.", "Singh, P.", "Brown, J."],
                publication_date="2023-08-30",
                journal="Diabetes Care",
                doi="10.2337/dc23-2345",
                relevance_score=0.88,
                key_findings="Multidisciplinary diabetes care reduces HbA1c by 1.2% and hospitalizations by 40% in complex patients",
                citation="Martinez, A. et al. (2023). Multidisciplinary Diabetes Care. Diabetes Care.",
                study_type="cohort",
                sample_size=8750,
                peer_reviewed=True
            ),
            ResearchFinding(
                title="Chronic Kidney Disease Progression Prediction Models: Machine Learning Approach",
                authors=["Liu, X.", "Foster, K.", "Anderson, T."],
                publication_date="2023-10-05",
                journal="Journal of the American Society of Nephrology",
                doi="10.1681/jasn.2023.456",
                relevance_score=0.85,
                key_findings="ML models predict CKD progression with 87% accuracy, enabling early intervention strategies",
                citation="Liu, X. et al. (2023). CKD Progression Prediction. JASN.",
                study_type="observational",
                sample_size=12300,
                peer_reviewed=True
            )
        ]
        
        conditions = [
            Condition(name="Chronic Kidney Disease Stage 3", confidence_score=0.94),
            Condition(name="Type 2 Diabetes Mellitus with Complications", confidence_score=0.91),
            Condition(name="Hypertensive Heart Disease", confidence_score=0.87),
            Condition(name="Diabetic Nephropathy", confidence_score=0.89)
        ]
        
        return ResearchAnalysis(
            patient_id="INTEGRATION_RPT_456",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=conditions,
            research_findings=research_findings,
            condition_research_correlations={
                "Chronic Kidney Disease Stage 3": research_findings[:2],
                "Type 2 Diabetes Mellitus with Complications": research_findings[:3],
                "Hypertensive Heart Disease": research_findings[1:2],
                "Diabetic Nephropathy": research_findings[:1]
            },
            categorized_findings={
                "systematic_reviews": research_findings[:1],
                "clinical_trials": research_findings[1:2],
                "observational": research_findings[2:]
            },
            research_insights=[
                "Research coverage: 4/4 conditions (100%) have extensive research literature available.",
                "Study quality: 4/4 papers are high-quality studies from top-tier nephrology and diabetes journals.",
                "Recent research: All papers published within the last 6 months, indicating cutting-edge evidence.",
                "Diabetic Nephropathy: Most relevant research focuses on SGLT2 inhibitor therapy for renal protection.",
                "Chronic Kidney Disease: Strong evidence supports intensive blood pressure control with careful monitoring.",
                "Multidisciplinary care approach strongly supported by recent quality improvement studies.",
                "Machine learning tools available for CKD progression prediction and risk stratification."
            ],
            clinical_recommendations=[
                "Consider SGLT2 inhibitor therapy for diabetic nephropathy based on strong meta-analysis evidence.",
                "Implement intensive blood pressure control (<130/80) with close monitoring for hypotension.",
                "Establish multidisciplinary care team including endocrinology, nephrology, and cardiology.",
                "Utilize CKD progression prediction models for personalized risk assessment and intervention timing.",
                "Regular monitoring of renal function, cardiovascular status, and glycemic control essential.",
                "Patient education on diabetes self-management and CKD progression prevention strategies.",
                "Consider clinical trial enrollment for novel therapies given complex disease profile."
            ],
            analysis_confidence=0.92,
            total_papers_reviewed=25,
            relevant_papers_found=4
        )
    
    def test_complete_report_generation_workflow(self, mock_audit_logger,
                                               comprehensive_patient_data,
                                               comprehensive_medical_summary,
                                               comprehensive_research_analysis):
        """Test the complete report generation workflow from data to final report."""
        # Initialize report generator
        report_generator = ReportGenerator(audit_logger=mock_audit_logger)
        
        # Generate comprehensive analysis report
        analysis_report = report_generator.generate_analysis_report(
            comprehensive_patient_data,
            comprehensive_medical_summary,
            comprehensive_research_analysis
        )
        
        # Verify report structure and content
        assert isinstance(analysis_report, AnalysisReport)
        assert analysis_report.patient_data.patient_id == "INTEGRATION_RPT_456"
        assert analysis_report.report_id.startswith("RPT_")
        
        # Verify comprehensive content generation
        assert hasattr(analysis_report, 'executive_summary')
        assert len(analysis_report.executive_summary) > 200  # Should be comprehensive
        
        assert hasattr(analysis_report, 'key_findings')
        assert len(analysis_report.key_findings) >= 5  # Should have multiple findings
        
        assert hasattr(analysis_report, 'recommendations')
        assert len(analysis_report.recommendations) >= 7  # Should include all research recommendations
        
        # Verify quality metrics for complex case
        quality_metrics = analysis_report.quality_metrics
        assert quality_metrics["overall_quality_score"] > 0.8  # Should be high quality
        assert quality_metrics["research_analysis_quality"]["papers_found"] == 4
        assert quality_metrics["medical_summary_quality"]["conditions_identified"] == 4
        
        # Verify executive summary contains key information
        summary = analysis_report.executive_summary
        assert "58-year-old" in summary
        assert "female" in summary.lower() or "F" in summary
        assert "kidney disease" in summary.lower() or "nephropathy" in summary.lower()
        assert "diabetes" in summary.lower()
        assert "research" in summary.lower()
        
        # Verify key findings include primary conditions
        findings_text = " ".join(analysis_report.key_findings)
        assert "kidney disease" in findings_text.lower() or "nephropathy" in findings_text.lower()
        assert "diabetes" in findings_text.lower()
        
        # Verify recommendations include research-based suggestions
        recommendations_text = " ".join(analysis_report.recommendations)
        assert "sglt2" in recommendations_text.lower() or "inhibitor" in recommendations_text.lower()
        assert "blood pressure" in recommendations_text.lower()
        assert "multidisciplinary" in recommendations_text.lower()
        
        # Verify audit logging occurred
        mock_audit_logger.log_data_access.assert_called()
        
        print(f"✅ Comprehensive Report Generated:")
        print(f"   - Report ID: {analysis_report.report_id}")
        print(f"   - Patient: {analysis_report.patient_data.name} (ID: {analysis_report.patient_data.patient_id})")
        print(f"   - Conditions: {len(comprehensive_medical_summary.key_conditions)}")
        print(f"   - Research Papers: {len(comprehensive_research_analysis.research_findings)}")
        print(f"   - Quality Score: {quality_metrics['overall_quality_score']:.2f}")
        print(f"   - Executive Summary Length: {len(analysis_report.executive_summary)} chars")
        print(f"   - Key Findings: {len(analysis_report.key_findings)}")
        print(f"   - Recommendations: {len(analysis_report.recommendations)}")
    
    @patch('src.agents.s3_report_persister.get_config')
    @patch('src.agents.s3_report_persister.boto3.client')
    def test_complete_report_persistence_workflow(self, mock_boto3_client, mock_get_config,
                                                mock_audit_logger,
                                                comprehensive_patient_data,
                                                comprehensive_medical_summary,
                                                comprehensive_research_analysis):
        """Test the complete report persistence workflow including S3 storage."""
        # Setup mocks
        mock_config = Mock()
        mock_config.aws = Mock()
        mock_config.aws.region = "us-east-1"
        mock_config.aws.access_key_id = "test_key"
        mock_config.aws.secret_access_key = "test_secret"
        mock_config.aws.s3_bucket = "test-medical-reports"
        mock_config.aws.s3_endpoint_url = None
        mock_get_config.return_value = mock_config
        
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Generate report
        report_generator = ReportGenerator(audit_logger=mock_audit_logger)
        analysis_report = report_generator.generate_analysis_report(
            comprehensive_patient_data,
            comprehensive_medical_summary,
            comprehensive_research_analysis
        )
        
        # Persist report to S3
        s3_persister = S3ReportPersister(audit_logger=mock_audit_logger)
        s3_persister.s3_client = mock_s3_client
        
        s3_key = s3_persister.save_analysis_report(analysis_report)
        
        # Verify S3 persistence
        assert s3_key.startswith("analysis-reports/patient-INTEGRATION_RPT_456/analysis-")
        assert s3_key.endswith(f"-{analysis_report.report_id}.json")
        
        # Verify S3 put_object was called with correct parameters
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args
        
        # Verify encryption and metadata
        assert call_args[1]['ServerSideEncryption'] == 'aws:kms'
        assert call_args[1]['ContentType'] == 'application/json'
        
        metadata = call_args[1]['Metadata']
        assert metadata['patient-id'] == "INTEGRATION_RPT_456"
        assert metadata['report-id'] == analysis_report.report_id
        assert metadata['content-type'] == 'medical-analysis-report'
        
        # Verify tagging for compliance
        tagging = call_args[1]['Tagging']
        assert "PatientID=INTEGRATION_RPT_456" in tagging
        assert "Confidential=true" in tagging
        
        # Verify report content was serialized
        report_body = call_args[1]['Body']
        assert isinstance(report_body, str)
        assert len(report_body) > 1000  # Should be substantial
        
        # Verify it's valid JSON
        parsed_report = json.loads(report_body)
        assert parsed_report['report_id'] == analysis_report.report_id
        assert parsed_report['patient_data']['patient_id'] == "INTEGRATION_RPT_456"
        
        print(f"✅ Report Persistence Complete:")
        print(f"   - S3 Key: {s3_key}")
        print(f"   - Report Size: {len(report_body)} bytes")
        print(f"   - Encryption: KMS")
        print(f"   - Metadata: Patient ID, Report ID, Content Type")
        print(f"   - Compliance Tags: Applied")
    
    @patch('src.agents.s3_report_persister.get_config')
    @patch('src.agents.s3_report_persister.boto3.client')
    def test_report_retrieval_workflow(self, mock_boto3_client, mock_get_config,
                                     mock_audit_logger,
                                     comprehensive_patient_data,
                                     comprehensive_medical_summary,
                                     comprehensive_research_analysis):
        """Test the complete report retrieval workflow from S3."""
        # Setup mocks
        mock_config = Mock()
        mock_config.aws = Mock()
        mock_config.aws.region = "us-east-1"
        mock_config.aws.access_key_id = "test_key"
        mock_config.aws.secret_access_key = "test_secret"
        mock_config.aws.s3_bucket = "test-medical-reports"
        mock_config.aws.s3_endpoint_url = None
        mock_get_config.return_value = mock_config
        
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Generate and serialize report
        report_generator = ReportGenerator(audit_logger=mock_audit_logger)
        original_report = report_generator.generate_analysis_report(
            comprehensive_patient_data,
            comprehensive_medical_summary,
            comprehensive_research_analysis
        )
        
        # Mock S3 responses for retrieval
        report_json = json.dumps(original_report.to_dict(), default=str)
        s3_key = f"analysis-reports/patient-INTEGRATION_RPT_456/analysis-20241102_120000-{original_report.report_id}.json"
        
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [{
                'Key': s3_key,
                'Size': len(report_json),
                'LastModified': datetime.now()
            }]
        }
        
        mock_response = Mock()
        mock_response.read.return_value = report_json.encode('utf-8')
        mock_s3_client.get_object.return_value = {'Body': mock_response}
        
        # Retrieve report
        s3_persister = S3ReportPersister(audit_logger=mock_audit_logger)
        s3_persister.s3_client = mock_s3_client
        
        retrieved_report = s3_persister.retrieve_analysis_report(
            original_report.report_id, "INTEGRATION_RPT_456"
        )
        
        # Verify retrieval
        assert isinstance(retrieved_report, AnalysisReport)
        assert retrieved_report.report_id == original_report.report_id
        assert retrieved_report.patient_data.patient_id == "INTEGRATION_RPT_456"
        assert retrieved_report.patient_data.name == "Sarah Martinez"
        
        # Verify S3 operations
        mock_s3_client.list_objects_v2.assert_called_once()
        mock_s3_client.get_object.assert_called_once()
        
        # Verify audit logging
        assert mock_audit_logger.log_data_access.call_count >= 2  # Save and retrieve
        
        print(f"✅ Report Retrieval Complete:")
        print(f"   - Retrieved Report ID: {retrieved_report.report_id}")
        print(f"   - Patient Match: {retrieved_report.patient_data.patient_id}")
        print(f"   - Data Integrity: Verified")
        print(f"   - Audit Trail: Complete")
    
    def test_report_quality_validation(self, mock_audit_logger,
                                     comprehensive_patient_data,
                                     comprehensive_medical_summary,
                                     comprehensive_research_analysis):
        """Test report quality validation for complex medical cases."""
        report_generator = ReportGenerator(audit_logger=mock_audit_logger)
        
        analysis_report = report_generator.generate_analysis_report(
            comprehensive_patient_data,
            comprehensive_medical_summary,
            comprehensive_research_analysis
        )
        
        # Validate report completeness
        validation_errors = analysis_report.validate()
        assert len(validation_errors) == 0, f"Report validation failed: {validation_errors}"
        
        # Verify quality metrics meet standards
        quality_metrics = analysis_report.quality_metrics
        
        # Data completeness should be high
        assert quality_metrics["data_completeness_score"] >= 0.8
        
        # Medical summary quality should be high
        med_quality = quality_metrics["medical_summary_quality"]
        assert med_quality["conditions_identified"] >= 4
        assert med_quality["data_quality_score"] >= 0.9
        
        # Research analysis quality should be high
        research_quality = quality_metrics["research_analysis_quality"]
        assert research_quality["papers_found"] >= 4
        assert research_quality["analysis_confidence"] >= 0.9
        assert research_quality["high_quality_papers"] >= 3
        
        # Overall quality should be high
        assert quality_metrics["overall_quality_score"] >= 0.85
        assert "High quality" in quality_metrics["quality_assessment"]
        
        print(f"✅ Quality Validation Complete:")
        print(f"   - Overall Quality Score: {quality_metrics['overall_quality_score']:.2f}")
        print(f"   - Data Completeness: {quality_metrics['data_completeness_score']:.2f}")
        print(f"   - Medical Summary Quality: {med_quality['data_quality_score']:.2f}")
        print(f"   - Research Analysis Confidence: {research_quality['analysis_confidence']:.2f}")
        print(f"   - Quality Assessment: {quality_metrics['quality_assessment']}")
    
    def test_end_to_end_workflow_performance(self, mock_audit_logger,
                                           comprehensive_patient_data,
                                           comprehensive_medical_summary,
                                           comprehensive_research_analysis):
        """Test end-to-end workflow performance and timing."""
        start_time = datetime.now()
        
        # Generate report
        report_generator = ReportGenerator(audit_logger=mock_audit_logger)
        analysis_report = report_generator.generate_analysis_report(
            comprehensive_patient_data,
            comprehensive_medical_summary,
            comprehensive_research_analysis
        )
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Verify performance
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert analysis_report.processing_time_seconds < 5.0
        
        # Verify report size is reasonable
        report_json = json.dumps(analysis_report.to_dict(), default=str)
        report_size_kb = len(report_json) / 1024
        
        assert 10 < report_size_kb < 500  # Should be between 10KB and 500KB
        
        print(f"✅ Performance Validation Complete:")
        print(f"   - Processing Time: {processing_time:.2f} seconds")
        print(f"   - Report Generation Time: {analysis_report.processing_time_seconds:.2f} seconds")
        print(f"   - Report Size: {report_size_kb:.1f} KB")
        print(f"   - Performance: {'✅ Acceptable' if processing_time < 5.0 else '❌ Too Slow'}")