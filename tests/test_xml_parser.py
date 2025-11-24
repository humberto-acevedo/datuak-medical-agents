"""Unit tests for XML Parser functionality."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.agents.xml_parser import XMLParser
from src.models.exceptions import XMLParsingError


class TestXMLParser:
    """Test XML Parser functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_audit_logger = Mock()
        self.parser = XMLParser(audit_logger=self.mock_audit_logger)
    
    def test_parse_simple_patient_xml(self):
        """Test parsing a simple patient XML structure."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <id>P001</id>
            <name>Jane Smith</name>
            <age>45</age>
            <gender>F</gender>
            <dateOfBirth>1978-05-15</dateOfBirth>
            <medications>
                <medication>
                    <id>M001</id>
                    <name>Lisinopril</name>
                    <dosage>10mg</dosage>
                    <frequency>daily</frequency>
                    <status>active</status>
                </medication>
            </medications>
            <diagnoses>
                <diagnosis>
                    <id>D001</id>
                    <condition>Hypertension</condition>
                    <dateDiagnosed>2023-01-15</dateDiagnosed>
                    <status>active</status>
                </diagnosis>
            </diagnoses>
        </patient>"""
        
        result = self.parser.parse_patient_xml(xml_content, "Jane Smith")
        
        assert result.patient_id == "P001"
        assert result.name == "Jane Smith"
        assert result.demographics.age == 45
        assert result.demographics.gender == "F"
        assert result.demographics.date_of_birth == "1978-05-15"
        assert len(result.medications) == 1
        assert result.medications[0].name == "Lisinopril"
        assert result.medications[0].dosage == "10mg"
        assert len(result.diagnoses) == 1
        assert result.diagnoses[0].condition == "Hypertension"
        assert result.raw_xml == xml_content
    
    def test_parse_structured_name_xml(self):
        """Test parsing XML with structured name (firstName, lastName)."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <id>P002</id>
            <name>
                <firstName>John</firstName>
                <lastName>Doe</lastName>
            </name>
            <age>35</age>
        </patient>"""
        
        result = self.parser.parse_patient_xml(xml_content, "John Doe")
        
        assert result.patient_id == "P002"
        assert result.name == "John Doe"
        assert result.demographics.age == 35
    
    def test_parse_nested_medical_history(self):
        """Test parsing nested medical history structure."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <id>P003</id>
            <name>Mary Johnson</name>
            <medicalHistory>
                <event>
                    <id>E001</id>
                    <date>2023-01-15</date>
                    <type>visit</type>
                    <description>Annual checkup</description>
                    <provider>Dr. Smith</provider>
                </event>
                <event>
                    <id>E002</id>
                    <date>2023-06-20</date>
                    <type>procedure</type>
                    <description>Blood work</description>
                    <provider>Lab Corp</provider>
                </event>
            </medicalHistory>
        </patient>"""
        
        result = self.parser.parse_patient_xml(xml_content, "Mary Johnson")
        
        assert result.patient_id == "P003"
        assert result.name == "Mary Johnson"
        assert len(result.medical_history) == 2
        assert result.medical_history[0].event_id == "E001"
        assert result.medical_history[0].description == "Annual checkup"
        assert result.medical_history[1].event_id == "E002"
        assert result.medical_history[1].description == "Blood work"
    
    def test_parse_multiple_medications(self):
        """Test parsing multiple medications."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <id>P004</id>
            <name>Bob Wilson</name>
            <medications>
                <medication>
                    <id>M001</id>
                    <name>Metformin</name>
                    <dosage>500mg</dosage>
                    <frequency>twice daily</frequency>
                    <indication>Diabetes</indication>
                </medication>
                <medication>
                    <id>M002</id>
                    <name>Atorvastatin</name>
                    <dosage>20mg</dosage>
                    <frequency>daily</frequency>
                    <indication>High cholesterol</indication>
                </medication>
            </medications>
        </patient>"""
        
        result = self.parser.parse_patient_xml(xml_content, "Bob Wilson")
        
        assert len(result.medications) == 2
        assert result.medications[0].name == "Metformin"
        assert result.medications[0].indication == "Diabetes"
        assert result.medications[1].name == "Atorvastatin"
        assert result.medications[1].indication == "High cholesterol"
    
    def test_parse_procedures_with_details(self):
        """Test parsing procedures with detailed information."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <id>P005</id>
            <name>Alice Brown</name>
            <procedures>
                <procedure>
                    <id>PR001</id>
                    <name>Colonoscopy</name>
                    <date>2023-03-10</date>
                    <provider>Dr. Johnson</provider>
                    <location>Outpatient Surgery Center</location>
                    <indication>Screening</indication>
                    <outcome>Normal findings</outcome>
                    <cptCode>45378</cptCode>
                </procedure>
            </procedures>
        </patient>"""
        
        result = self.parser.parse_patient_xml(xml_content, "Alice Brown")
        
        assert len(result.procedures) == 1
        procedure = result.procedures[0]
        assert procedure.name == "Colonoscopy"
        assert procedure.provider == "Dr. Johnson"
        assert procedure.location == "Outpatient Surgery Center"
        assert procedure.indication == "Screening"
        assert procedure.outcome == "Normal findings"
        assert procedure.cpt_code == "45378"
    
    def test_parse_xml_with_missing_patient_id(self):
        """Test parsing XML without explicit patient ID."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <name>Test Patient</name>
            <age>30</age>
        </patient>"""
        
        result = self.parser.parse_patient_xml(xml_content, "Test Patient")
        
        # Should generate ID from name
        assert result.patient_id == "patient_test_patient"
        assert result.name == "Test Patient"
    
    def test_parse_xml_with_text_elements(self):
        """Test parsing XML with #text elements (from xmltodict)."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <id>P006</id>
            <name>Sample Patient</name>
            <medications>
                <medication>
                    <name>Aspirin</name>
                    <dosage>81mg</dosage>
                    <frequency>daily</frequency>
                </medication>
            </medications>
        </patient>"""
        
        result = self.parser.parse_patient_xml(xml_content, "Sample Patient")
        
        assert result.patient_id == "P006"
        assert result.name == "Sample Patient"
        assert len(result.medications) == 1
        assert result.medications[0].name == "Aspirin"
    
    def test_name_matching_fuzzy(self):
        """Test fuzzy name matching functionality."""
        # Test exact match
        assert self.parser._names_match("John Smith", "John Smith") is True
        
        # Test case insensitive
        assert self.parser._names_match("john smith", "John Smith") is True
        
        # Test with punctuation
        assert self.parser._names_match("John-Smith", "John Smith") is True
        
        # Test partial match
        assert self.parser._names_match("John", "John Smith") is True
        
        # Test similar names
        assert self.parser._names_match("Jon Smith", "John Smith") is True
        
        # Test completely different names
        assert self.parser._names_match("Jane Doe", "John Smith") is False
        
        # Test empty names
        assert self.parser._names_match("", "John Smith") is False
        assert self.parser._names_match("John Smith", "") is False
    
    def test_invalid_xml_structure(self):
        """Test handling of invalid XML structure."""
        invalid_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <name>Test Patient</name>
            <unclosed_tag>
        </patient>"""
        
        with pytest.raises(XMLParsingError, match="Invalid XML syntax"):
            self.parser.parse_patient_xml(invalid_xml, "Test Patient")
    
    def test_empty_xml_content(self):
        """Test handling of empty XML content."""
        with pytest.raises(XMLParsingError):
            self.parser.parse_patient_xml("", "Test Patient")
    
    def test_xml_without_patient_data(self):
        """Test XML that doesn't contain patient data."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <root>
            <someOtherData>value</someOtherData>
        </root>"""
        
        with pytest.raises(XMLParsingError, match="No patient data found"):
            self.parser.parse_patient_xml(xml_content, "Test Patient")
    
    def test_audit_logging_on_success(self):
        """Test that successful parsing triggers audit logging."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <id>P007</id>
            <name>Audit Test</name>
            <age>40</age>
        </patient>"""
        
        result = self.parser.parse_patient_xml(xml_content, "Audit Test")
        
        # Verify audit logging was called
        self.mock_audit_logger.log_data_access.assert_called_once()
        call_args = self.mock_audit_logger.log_data_access.call_args
        
        assert call_args[1]['patient_id'] == "P007"
        assert call_args[1]['operation'] == "xml_parse_success"
        assert 'details' in call_args[1]
    
    def test_count_extracted_fields(self):
        """Test field counting for audit purposes."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <id>P008</id>
            <name>Field Count Test</name>
            <age>25</age>
            <medications>
                <medication>
                    <name>Med1</name>
                    <dosage>10mg</dosage>
                    <frequency>daily</frequency>
                </medication>
                <medication>
                    <name>Med2</name>
                    <dosage>20mg</dosage>
                    <frequency>twice daily</frequency>
                </medication>
            </medications>
            <diagnoses>
                <diagnosis>
                    <condition>Condition1</condition>
                    <dateDiagnosed>2023-01-01</dateDiagnosed>
                </diagnosis>
            </diagnoses>
        </patient>"""
        
        result = self.parser.parse_patient_xml(xml_content, "Field Count Test")
        field_count = self.parser._count_extracted_fields(result)
        
        assert field_count['medications'] == 2
        assert field_count['diagnoses'] == 1
        assert field_count['medical_events'] == 0
        assert field_count['procedures'] == 0
        assert field_count['has_demographics'] is True
    
    def test_parse_alternative_xml_structure(self):
        """Test parsing XML with alternative structure (Record root)."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <medicalRecord>
            <patient>
                <mrn>MRN123</mrn>
                <patientName>Alternative Structure</patientName>
                <patientAge>50</patientAge>
                <sex>M</sex>
            </patient>
        </medicalRecord>"""
        
        result = self.parser.parse_patient_xml(xml_content, "Alternative Structure")
        
        assert result.patient_id == "MRN123"
        assert result.name == "Alternative Structure"
        assert result.demographics.age == 50
        assert result.demographics.gender == "M"
    
    def test_parse_medication_with_dates(self):
        """Test parsing medications with start and end dates."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <id>P009</id>
            <name>Med Dates Test</name>
            <medications>
                <medication>
                    <name>Antibiotic</name>
                    <dosage>250mg</dosage>
                    <frequency>three times daily</frequency>
                    <startDate>2023-01-01</startDate>
                    <endDate>2023-01-10</endDate>
                    <prescribingPhysician>Dr. Wilson</prescribingPhysician>
                    <status>completed</status>
                </medication>
            </medications>
        </patient>"""
        
        result = self.parser.parse_patient_xml(xml_content, "Med Dates Test")
        
        assert len(result.medications) == 1
        med = result.medications[0]
        assert med.name == "Antibiotic"
        assert med.start_date == "2023-01-01"
        assert med.end_date == "2023-01-10"
        assert med.prescribing_physician == "Dr. Wilson"
        assert med.status == "completed"
    
    def test_parse_diagnosis_with_icd_code(self):
        """Test parsing diagnosis with ICD-10 code."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <id>P010</id>
            <name>ICD Test</name>
            <diagnoses>
                <diagnosis>
                    <condition>Essential Hypertension</condition>
                    <dateDiagnosed>2023-02-15</dateDiagnosed>
                    <icd10Code>I10</icd10Code>
                    <severity>moderate</severity>
                    <diagnosingPhysician>Dr. Heart</diagnosingPhysician>
                    <notes>Well controlled with medication</notes>
                </diagnosis>
            </diagnoses>
        </patient>"""
        
        result = self.parser.parse_patient_xml(xml_content, "ICD Test")
        
        assert len(result.diagnoses) == 1
        diag = result.diagnoses[0]
        assert diag.condition == "Essential Hypertension"
        assert diag.icd_10_code == "I10"
        assert diag.severity == "moderate"
        assert diag.diagnosing_physician == "Dr. Heart"
        assert diag.notes == "Well controlled with medication"