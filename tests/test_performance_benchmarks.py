"""Performance benchmark tests for medical record analysis system."""
import pytest
import time
import asyncio
import psutil
import threading
from unittest.mock import Mock, patch
from datetime import datetime
import xml.etree.ElementTree as ET

from src.workflow.main_workflow import MainWorkflow
from src.agents.xml_parser_agent import XMLParserAgent
from src.agents.medical_summarization_agent import MedicalSummarizationAgent
from src.agents.research_correlation_agent import ResearchCorrelationAgent
from src.models import PatientData, MedicalSummary, ResearchAnalysis, AnalysisReport
from tests.fixtures.sample_patient_data import PERFORMANCE_BENCHMARKS

class PerformanceMonitor:
    """Monitor system performance during tests."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.start_memory = None
        self.end_memory = None
        self.peak_memory = None
        self.cpu_usage = []
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory
        self.cpu_usage = []
        self.monitoring = True
        
        # Start CPU monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_cpu)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring and return metrics."""
        self.monitoring = False
        self.end_time = time.time()
        self.end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        
        return {
            'execution_time': self.end_time - self.start_time,
            'memory_start': self.start_memory,
            'memory_end': self.end_memory,
            'memory_peak': self.peak_memory,
            'memory_delta': self.end_memory - self.start_memory,
            'avg_cpu_usage': sum(self.cpu_usage) / len(self.cpu_usage) if self.cpu_usage else 0,
            'peak_cpu_usage': max(self.cpu_usage) if self.cpu_usage else 0
        }
    
    def _monitor_cpu(self):
        """Monitor CPU usage in background thread."""
        while self.monitoring:
            try:
                cpu_percent = psutil.Process().cpu_percent()
                self.cpu_usage.append(cpu_percent)
                
                # Update peak memory
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                self.peak_memory = max(self.peak_memory, current_memory)
                
                time.sleep(0.1)  # Sample every 100ms
            except:
                break

def generate_large_patient_xml(num_diagnoses=50, num_medications=30, num_procedures=40):
    """Generate large patient XML for performance testing."""
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<patient_record>',
        '  <demographics>',
        '    <patient_id>PERF_TEST_001</patient_id>',
        '    <name>Performance Test Patient</name>',
        '    <date_of_birth>1970-01-01</date_of_birth>',
        '    <age>53</age>',
        '    <gender>Male</gender>',
        '  </demographics>',
        '  <medical_history>',
        '    <diagnoses>'
    ]
    
    # Add many diagnoses
    for i in range(num_diagnoses):
        xml_parts.extend([
            '      <diagnosis>',
            f'        <code>E{i:02d}.{i%10}</code>',
            f'        <description>Test diagnosis {i+1}</description>',
            f'        <date_diagnosed>202{i%4}-{(i%12)+1:02d}-{(i%28)+1:02d}</date_diagnosed>',
            '        <status>Active</status>',
            '        <severity>Moderate</severity>',
            '      </diagnosis>'
        ])
    
    xml_parts.append('    </diagnoses>')
    xml_parts.append('    <medications>')
    
    # Add many medications
    for i in range(num_medications):
        xml_parts.extend([
            '      <medication>',
            f'        <name>TestMedication{i+1}</name>',
            f'        <dosage>{(i%10)+1}0mg</dosage>',
            '        <frequency>Once daily</frequency>',
            f'        <start_date>202{i%4}-{(i%12)+1:02d}-01</start_date>',
            '        <status>Active</status>',
            f'        <indication>Test condition {i+1}</indication>',
            '      </medication>'
        ])
    
    xml_parts.append('    </medications>')
    xml_parts.append('    <procedures>')
    
    # Add many procedures
    for i in range(num_procedures):
        xml_parts.extend([
            '      <procedure>',
            f'        <code>{80000+i}</code>',
            f'        <description>Test procedure {i+1}</description>',
            f'        <date>202{i%4}-{(i%12)+1:02d}-{(i%28)+1:02d}</date>',
            f'        <provider>Dr. Test{i%10}</provider>',
            f'        <results>Normal results for procedure {i+1}</results>',
            '      </procedure>'
        ])
    
    xml_parts.extend([
        '    </procedures>',
        '  </medical_history>',
        '</patient_record>'
    ])
    
    return '\n'.join(xml_parts)

class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    def setup_method(self):
        """Set up performance test fixtures."""
        self.monitor = PerformanceMonitor()
        self.workflow = MainWorkflow(enable_enhanced_logging=False)
    
    @pytest.mark.performance
    def test_xml_parsing_large_file_performance(self):
        """Test XML parsing performance with large patient files."""
        # Generate large XML file
        large_xml = generate_large_patient_xml(num_diagnoses=100, num_medications=50, num_procedures=75)
        
        xml_parser = XMLParserAgent()
        
        # Mock S3 operations
        with patch('src.agents.xml_parser_agent.boto3.client') as mock_boto:
            mock_s3_client = Mock()
            mock_s3_client.get_object.return_value = {
                'Body': Mock(read=Mock(return_value=large_xml.encode('utf-8')))
            }
            mock_boto.return_value = mock_s3_client
            
            self.monitor.start_monitoring()
            
            # Parse large XML file
            result = xml_parser.parse_patient_record("Performance Test Patient")
            
            metrics = self.monitor.stop_monitoring()
            
            # Verify parsing succeeded
            assert result is not None
            assert result.patient_id == "PERF_TEST_001"
            assert len(result.medical_history.get('diagnoses', [])) == 100
            assert len(result.medical_history.get('medications', [])) == 50
            assert len(result.medical_history.get('procedures', [])) == 75
            
            # Verify performance benchmarks
            assert metrics['execution_time'] <= PERFORMANCE_BENCHMARKS["xml_parsing_max_time"] * 3  # Allow 3x for large files
            assert metrics['memory_delta'] < 100  # Should not use more than 100MB additional memory
            
            print(f"Large XML parsing metrics: {metrics}")
    
    @pytest.mark.performance
    def test_medical_summarization_large_data_performance(self):
        """Test medical summarization performance with large datasets."""
        # Create patient data with many conditions
        large_medical_history = {
            'diagnoses': [f"Test diagnosis {i}" for i in range(100)],
            'medications': [f"TestMed{i}" for i in range(50)],
            'procedures': [f"Test procedure {i}" for i in range(75)],
            'allergies': [f"Test allergy {i}" for i in range(20)],
            'vital_signs': [{'date': f'2023-{i%12+1:02d}-01', 'bp': f'{120+i%20}/{80+i%10}'} for i in range(30)]
        }
        
        patient_data = PatientData(
            name="Performance Test Patient",
            patient_id="PERF_TEST_001",
            age=53,
            gender="Male",
            medical_history=large_medical_history
        )
        
        summarizer = MedicalSummarizationAgent()
        
        self.monitor.start_monitoring()
        
        # Generate summary for large dataset
        result = summarizer.generate_summary(patient_data)
        
        metrics = self.monitor.stop_monitoring()
        
        # Verify summarization succeeded
        assert result is not None
        assert len(result.summary_text) > 100
        assert len(result.key_conditions) > 0
        
        # Verify performance benchmarks
        assert metrics['execution_time'] <= PERFORMANCE_BENCHMARKS["medical_summarization_max_time"] * 2
        assert metrics['memory_delta'] < 50  # Should not use excessive memory
        
        print(f"Large data summarization metrics: {metrics}")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_research_correlation_performance_stress(self):
        """Test research correlation performance under stress."""
        # Create medical summary with many conditions
        medical_summary = MedicalSummary(
            summary_text="Patient has multiple complex medical conditions requiring extensive research.",
            key_conditions=[
                {"name": f"Test condition {i}", "confidence_score": 0.8 + (i % 20) * 0.01}
                for i in range(20)  # Many conditions to research
            ],
            chronic_conditions=[f"Chronic condition {i}" for i in range(10)],
            medications=[f"TestMed{i}" for i in range(15)]
        )
        
        patient_data = PatientData(
            name="Performance Test Patient",
            patient_id="PERF_TEST_001"
        )
        
        correlator = ResearchCorrelationAgent()
        
        self.monitor.start_monitoring()
        
        # Correlate research for many conditions
        result = correlator.correlate_research(patient_data, medical_summary)
        
        metrics = self.monitor.stop_monitoring()
        
        # Verify correlation succeeded
        assert result is not None
        assert result.analysis_confidence > 0
        assert len(result.insights) > 0
        
        # Verify performance benchmarks
        assert metrics['execution_time'] <= PERFORMANCE_BENCHMARKS["research_correlation_max_time"] * 2
        assert metrics['memory_delta'] < 100
        
        print(f"Research correlation stress test metrics: {metrics}")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_end_to_end_workflow_performance(self):
        """Test complete workflow performance with realistic data."""
        large_xml = generate_large_patient_xml(num_diagnoses=25, num_medications=15, num_procedures=20)
        
        # Mock S3 operations
        with patch('src.agents.xml_parser_agent.boto3.client') as mock_boto:
            mock_s3_client = Mock()
            mock_s3_client.get_object.return_value = {
                'Body': Mock(read=Mock(return_value=large_xml.encode('utf-8')))
            }
            mock_boto.return_value = mock_s3_client
            
            # Mock S3 persistence
            with patch.object(self.workflow.s3_persister, 'save_analysis_report', return_value="s3://test/report.json"):
                
                self.monitor.start_monitoring()
                
                # Execute complete workflow
                result = await self.workflow.execute_complete_analysis("Performance Test Patient")
                
                metrics = self.monitor.stop_monitoring()
                
                # Verify workflow succeeded
                assert result is not None
                assert result.patient_data.patient_id == "PERF_TEST_001"
                assert result.medical_summary is not None
                assert result.research_analysis is not None
                
                # Verify performance benchmarks
                assert metrics['execution_time'] <= PERFORMANCE_BENCHMARKS["total_workflow_max_time"] * 1.5
                assert metrics['memory_delta'] < 200  # Should not use excessive memory
                assert metrics['peak_cpu_usage'] < 90  # Should not max out CPU
                
                print(f"End-to-end workflow performance metrics: {metrics}")
    
    @pytest.mark.performance
    def test_concurrent_workflow_performance(self):
        """Test performance under concurrent workflow execution."""
        import concurrent.futures
        
        def run_workflow_sync():
            """Run workflow synchronously for concurrent testing."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                workflow = MainWorkflow(enable_enhanced_logging=False)
                
                # Mock S3 operations
                with patch('src.agents.xml_parser_agent.boto3.client') as mock_boto:
                    mock_s3_client = Mock()
                    mock_s3_client.get_object.return_value = {
                        'Body': Mock(read=Mock(return_value=generate_large_patient_xml().encode('utf-8')))
                    }
                    mock_boto.return_value = mock_s3_client
                    
                    with patch.object(workflow.s3_persister, 'save_analysis_report', return_value="s3://test/report.json"):
                        return loop.run_until_complete(
                            workflow.execute_complete_analysis(f"Patient {threading.current_thread().ident}")
                        )
            finally:
                loop.close()
        
        self.monitor.start_monitoring()
        
        # Run multiple workflows concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_workflow_sync) for _ in range(3)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        metrics = self.monitor.stop_monitoring()
        
        # Verify all workflows succeeded
        assert len(results) == 3
        assert all(result is not None for result in results)
        
        # Verify concurrent performance
        assert metrics['execution_time'] <= PERFORMANCE_BENCHMARKS["total_workflow_max_time"] * 2  # Allow 2x for concurrency
        assert metrics['memory_delta'] < 500  # Should handle concurrent execution efficiently
        
        print(f"Concurrent workflow performance metrics: {metrics}")
    
    @pytest.mark.performance
    def test_memory_leak_detection(self):
        """Test for memory leaks during repeated operations."""
        import gc
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Run multiple iterations to detect memory leaks
        for i in range(10):
            workflow = MainWorkflow(enable_enhanced_logging=False)
            
            # Mock operations
            with patch('src.agents.xml_parser_agent.boto3.client') as mock_boto:
                mock_s3_client = Mock()
                mock_s3_client.get_object.return_value = {
                    'Body': Mock(read=Mock(return_value=generate_large_patient_xml().encode('utf-8')))
                }
                mock_boto.return_value = mock_s3_client
                
                # Create and destroy workflow objects
                xml_parser = XMLParserAgent()
                result = xml_parser.parse_patient_record(f"Test Patient {i}")
                
                # Clean up
                del xml_parser
                del workflow
                gc.collect()
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be minimal (less than 50MB after 10 iterations)
        assert memory_growth < 50, f"Potential memory leak detected: {memory_growth}MB growth"
        
        print(f"Memory leak test: Initial={initial_memory:.1f}MB, Final={final_memory:.1f}MB, Growth={memory_growth:.1f}MB")
    
    @pytest.mark.performance
    def test_quality_assurance_performance_impact(self):
        """Test performance impact of quality assurance system."""
        from src.models import Demographics
        from datetime import datetime
        
        # Create test report
        demographics = Demographics(
            date_of_birth="1978-01-01",
            gender="Male",
            age=45,
            address=None,
            phone=None,
            emergency_contact=None
        )
        
        patient_data = PatientData(
            name="Test Patient",
            patient_id="TEST_001",
            demographics=demographics,
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        medical_summary = MedicalSummary(
            summary_text="Patient has diabetes and hypertension with good control.",
            key_conditions=[
                {"name": "Type 2 Diabetes", "confidence_score": 0.95},
                {"name": "Hypertension", "confidence_score": 0.88}
            ]
        )
        research_analysis = ResearchAnalysis(
            research_findings=[],
            analysis_confidence=0.8,
            insights=["Good disease management"],
            recommendations=["Continue current treatment"]
        )
        
        analysis_report = AnalysisReport(
            report_id="TEST_R001",
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_at=datetime.now()
        )
        
        # Test without QA
        start_time = time.time()
        # Simulate report generation without QA
        time.sleep(0.1)  # Simulate processing time
        baseline_time = time.time() - start_time
        
        # Test with QA
        self.monitor.start_monitoring()
        
        # Run quality assurance
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            qa_result = loop.run_until_complete(
                self.workflow._execute_quality_assurance(analysis_report)
            )
        finally:
            loop.close()
        
        metrics = self.monitor.stop_monitoring()
        
        # Verify QA succeeded
        assert qa_result is not None
        
        # Verify QA performance impact is acceptable
        qa_overhead = metrics['execution_time'] - baseline_time
        assert qa_overhead <= PERFORMANCE_BENCHMARKS["quality_assurance_max_time"]
        
        print(f"QA performance impact: Baseline={baseline_time:.3f}s, QA={metrics['execution_time']:.3f}s, Overhead={qa_overhead:.3f}s")

class TestScalabilityBenchmarks:
    """Scalability benchmark tests."""
    
    @pytest.mark.performance
    @pytest.mark.parametrize("data_size", ["small", "medium", "large", "xlarge"])
    def test_scalability_with_data_size(self, data_size):
        """Test system scalability with different data sizes."""
        size_configs = {
            "small": {"diagnoses": 5, "medications": 3, "procedures": 5},
            "medium": {"diagnoses": 25, "medications": 15, "procedures": 20},
            "large": {"diagnoses": 50, "medications": 30, "procedures": 40},
            "xlarge": {"diagnoses": 100, "medications": 60, "procedures": 80}
        }
        
        config = size_configs[data_size]
        xml_data = generate_large_patient_xml(**config)
        
        xml_parser = XMLParserAgent()
        
        with patch('src.agents.xml_parser_agent.boto3.client') as mock_boto:
            mock_s3_client = Mock()
            mock_s3_client.get_object.return_value = {
                'Body': Mock(read=Mock(return_value=xml_data.encode('utf-8')))
            }
            mock_boto.return_value = mock_s3_client
            
            monitor = PerformanceMonitor()
            monitor.start_monitoring()
            
            result = xml_parser.parse_patient_record(f"Scalability Test {data_size}")
            
            metrics = monitor.stop_monitoring()
            
            # Verify parsing succeeded
            assert result is not None
            
            # Performance should scale reasonably
            expected_max_time = {
                "small": 2.0,
                "medium": 5.0,
                "large": 10.0,
                "xlarge": 20.0
            }
            
            assert metrics['execution_time'] <= expected_max_time[data_size]
            
            print(f"Scalability test {data_size}: {metrics}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])