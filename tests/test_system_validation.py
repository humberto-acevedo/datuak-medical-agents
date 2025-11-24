"""Comprehensive system validation tests."""
import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from src.workflow.main_workflow import MainWorkflow
from src.utils.quality_assurance import QualityLevel
from src.utils.hallucination_prevention import HallucinationRiskLevel
from src.models import PatientData, MedicalSummary, ResearchAnalysis, AnalysisReport
from tests.fixtures.sample_patient_data import SAMPLE_PATIENT_XML_GOOD, EXPECTED_ANALYSIS_RESULTS

class TestSystemValidation:
    """System validation tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.workflow = MainWorkflow(enable_enhanced_logging=False)
    
    @pytest.mark.asyncio
    async def test_end_to_end_validation(self):
        """Test complete end-to-end system validation."""
        with patch('src.agents.xml_parser_agent.boto3.client') as mock_boto:
            mock_s3_client = Mock()
            mock_s3_client.get_object.return_value = {
                'Body': Mock(read=Mock(return_value=SAMPLE_PATIENT_XML_GOOD.encode('utf-8')))
            }
            mock_boto.return_value = mock_s3_client
            
            with patch.object(self.workflow.s3_persister, 'save_analysis_report', return_value="s3://test/report.json"):
                result = await self.workflow.execute_complete_analysis("John Doe")
                
                # Validate complete system functionality
                assert result is not None
                assert result.patient_data.patient_id == "TEST_P001"
                assert result.medical_summary is not None
                assert result.research_analysis is not None
                assert 'quality_assessment' in result.processing_metadata
                
                qa_data = result.processing_metadata['quality_assessment']
                assert qa_data['quality_level'] in ['excellent', 'good', 'acceptable']
                assert qa_data['overall_score'] > 0.5

if __name__ == "__main__":
    pytest.main([__file__, "-v"])