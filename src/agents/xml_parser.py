"""XML Parser for medical records with validation and data extraction."""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from xml.etree import ElementTree as ET
from lxml import etree
import xmltodict

from ..models import (
    PatientData, Demographics, MedicalEvent, Medication, 
    Procedure, Diagnosis, XMLParsingError
)
from ..utils import AuditLogger


logger = logging.getLogger(__name__)


class XMLParser:
    """Parses medical XML records and extracts structured data."""
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize XML parser.
        
        Args:
            audit_logger: Optional audit logger for HIPAA compliance
        """
        self.audit_logger = audit_logger or AuditLogger()
    
    def parse_patient_xml(self, xml_content: str, patient_name: str) -> PatientData:
        """
        Parse patient XML content and extract structured medical data.
        
        Args:
            xml_content: Raw XML content as string
            patient_name: Expected patient name for validation
            
        Returns:
            PatientData: Structured patient medical data
            
        Raises:
            XMLParsingError: If XML parsing fails or validation errors occur
        """
        try:
            # Validate XML structure
            self._validate_xml_structure(xml_content)
            
            # Parse XML to dictionary for easier processing
            xml_dict = xmltodict.parse(xml_content)
            
            # Extract patient information
            patient_data = self._extract_patient_data(xml_dict, xml_content, patient_name)
            
            # Validate extracted data
            validation_errors = patient_data.validate()
            if validation_errors:
                logger.warning(f"Patient data validation warnings: {validation_errors}")
            
            # Log successful parsing
            self.audit_logger.log_data_access(
                patient_id=patient_data.patient_id,
                operation="xml_parse_success",
                details={"fields_extracted": self._count_extracted_fields(patient_data)}
            )
            
            return patient_data
            
        except ET.ParseError as e:
            error_msg = f"XML parsing failed: {str(e)}"
            logger.error(error_msg)
            raise XMLParsingError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during XML parsing: {str(e)}"
            logger.error(error_msg)
            raise XMLParsingError(error_msg)
    
    def _validate_xml_structure(self, xml_content: str) -> None:
        """
        Validate XML structure and basic medical record requirements.
        
        Args:
            xml_content: Raw XML content
            
        Raises:
            XMLParsingError: If XML structure is invalid
        """
        try:
            # Parse with lxml for better error reporting
            parser = etree.XMLParser(recover=False)
            etree.fromstring(xml_content.encode('utf-8'), parser)
            
            # Check for required medical record elements
            required_patterns = [
                r'<patient|<Patient',  # Patient root element
                r'name|Name',          # Patient name
            ]
            
            for pattern in required_patterns:
                if not re.search(pattern, xml_content, re.IGNORECASE):
                    logger.warning(f"Missing expected element pattern: {pattern}")
            
        except etree.XMLSyntaxError as e:
            raise XMLParsingError(f"Invalid XML syntax: {str(e)}")
    
    def _extract_patient_data(self, xml_dict: Dict, raw_xml: str, expected_name: str) -> PatientData:
        """
        Extract patient data from parsed XML dictionary.
        
        Args:
            xml_dict: Parsed XML as dictionary
            raw_xml: Original XML content for audit trail
            expected_name: Expected patient name for validation
            
        Returns:
            PatientData: Extracted patient data
        """
        # Find patient root element (handle different XML structures)
        patient_root = self._find_patient_root(xml_dict)
        
        if not patient_root:
            raise XMLParsingError("No patient data found in XML")
        
        # Validate that we have some patient-like data
        if not self._has_patient_data(patient_root):
            raise XMLParsingError("No patient data found in XML")
        
        # Extract basic patient information
        patient_id = self._extract_patient_id(patient_root)
        patient_name = self._extract_patient_name(patient_root)
        
        # Validate patient name matches expected
        if not self._names_match(patient_name, expected_name):
            logger.warning(f"Patient name mismatch: expected '{expected_name}', found '{patient_name}'")
        
        # Extract demographics
        demographics = self._extract_demographics(patient_root)
        
        # Extract medical history components
        medical_history = self._extract_medical_history(patient_root)
        medications = self._extract_medications(patient_root)
        procedures = self._extract_procedures(patient_root)
        diagnoses = self._extract_diagnoses(patient_root)
        
        return PatientData(
            patient_id=patient_id,
            name=patient_name,
            demographics=demographics,
            medical_history=medical_history,
            medications=medications,
            procedures=procedures,
            diagnoses=diagnoses,
            raw_xml=raw_xml,
            extraction_timestamp=datetime.now()
        )
    
    def _find_patient_root(self, xml_dict: Dict) -> Optional[Dict]:
        """Find the patient root element in various XML structures."""
        # Common patient root element names
        patient_keys = ['patient', 'Patient', 'PATIENT', 'record', 'Record']
        
        # Check for HL7 CDA ClinicalDocument structure
        if 'ClinicalDocument' in xml_dict:
            clinical_doc = xml_dict['ClinicalDocument']
            if isinstance(clinical_doc, dict):
                # Navigate: ClinicalDocument -> recordTarget -> patientRole -> patient
                if 'recordTarget' in clinical_doc:
                    record_target = clinical_doc['recordTarget']
                    if isinstance(record_target, dict) and 'patientRole' in record_target:
                        patient_role = record_target['patientRole']
                        if isinstance(patient_role, dict) and 'patient' in patient_role:
                            # Return the entire ClinicalDocument with patient info
                            # This allows us to extract medications, procedures, etc. from component sections
                            return clinical_doc
        
        # Check direct keys
        for key in patient_keys:
            if key in xml_dict:
                return xml_dict[key]
        
        # Check nested structures (like medicalRecord -> patient)
        for key, value in xml_dict.items():
            if isinstance(value, dict):
                for patient_key in patient_keys:
                    if patient_key in value:
                        return value[patient_key]
        
        # Check if root is medicalRecord and contains patient data directly
        if 'medicalRecord' in xml_dict:
            medical_record = xml_dict['medicalRecord']
            if isinstance(medical_record, dict):
                # Check if medicalRecord contains patient element
                for patient_key in patient_keys:
                    if patient_key in medical_record:
                        return medical_record[patient_key]
                # If no patient element, return medicalRecord itself
                return medical_record
        
        # If no specific patient element, return the root
        return xml_dict
    
    def _has_patient_data(self, patient_root: Dict) -> bool:
        """Check if the root contains patient-like data."""
        # Check for HL7 CDA ClinicalDocument structure
        if 'recordTarget' in patient_root:
            return True
        
        # Look for common patient data indicators
        patient_indicators = [
            'id', 'patientId', 'patient_id', 'ID', 'mrn', 'MRN',
            'name', 'Name', 'patientName', 'fullName',
            'age', 'Age', 'patientAge',
            'gender', 'Gender', 'sex', 'Sex',
            'medications', 'medication', 'diagnoses', 'diagnosis',
            'procedures', 'procedure', 'medicalHistory', 'history',
            'component', 'structuredBody'  # CDA components
        ]
        
        for indicator in patient_indicators:
            if indicator in patient_root:
                return True
        
        return False
    
    def _extract_patient_id(self, patient_root: Dict) -> str:
        """Extract patient ID from various possible locations."""
        # Check for HL7 CDA structure: recordTarget -> patientRole -> id
        if 'recordTarget' in patient_root:
            try:
                patient_role = patient_root['recordTarget']['patientRole']
                if 'id' in patient_role:
                    id_obj = patient_role['id']
                    if isinstance(id_obj, dict):
                        # Check for extension attribute (common in CDA)
                        if '@extension' in id_obj:
                            return str(id_obj['@extension'])
                        if '@root' in id_obj:
                            return str(id_obj['@root'])
            except (KeyError, TypeError):
                pass
        
        id_keys = ['id', 'patientId', 'patient_id', 'ID', 'mrn', 'MRN', 'recordNumber']
        
        for key in id_keys:
            if key in patient_root:
                value = patient_root[key]
                if isinstance(value, dict) and '#text' in value:
                    return str(value['#text'])
                return str(value)
        
        # Generate ID from name if not found
        name = self._extract_patient_name(patient_root)
        if name and name != "Unknown Patient":
            return f"patient_{name.replace(' ', '_').lower()}"
        return "unknown_patient"
    
    def _extract_patient_name(self, patient_root: Dict) -> str:
        """Extract patient name from various possible locations."""
        # Check for HL7 CDA structure: recordTarget -> patientRole -> patient -> name
        if 'recordTarget' in patient_root:
            try:
                patient = patient_root['recordTarget']['patientRole']['patient']
                if 'name' in patient:
                    name_obj = patient['name']
                    if isinstance(name_obj, dict):
                        given = name_obj.get('given', '')
                        family = name_obj.get('family', '')
                        if isinstance(given, dict) and '#text' in given:
                            given = given['#text']
                        if isinstance(family, dict) and '#text' in family:
                            family = family['#text']
                        if given and family:
                            return f"{given} {family}"
            except (KeyError, TypeError):
                pass
        
        name_keys = ['name', 'Name', 'patientName', 'fullName']
        
        for key in name_keys:
            if key in patient_root:
                value = patient_root[key]
                if isinstance(value, dict):
                    # Handle structured name (firstName, lastName)
                    if 'firstName' in value and 'lastName' in value:
                        first = value['firstName']
                        last = value['lastName']
                        if isinstance(first, dict) and '#text' in first:
                            first = first['#text']
                        if isinstance(last, dict) and '#text' in last:
                            last = last['#text']
                        return f"{first} {last}"
                    elif '#text' in value:
                        return str(value['#text'])
                return str(value)
        
        return "Unknown Patient"
    
    def _extract_demographics(self, patient_root: Dict) -> Demographics:
        """Extract demographic information."""
        demographics_data = {}
        
        # Age extraction
        age_keys = ['age', 'Age', 'patientAge']
        for key in age_keys:
            if key in patient_root:
                value = patient_root[key]
                if isinstance(value, dict) and '#text' in value:
                    value = value['#text']
                try:
                    demographics_data['age'] = int(value)
                    break
                except (ValueError, TypeError):
                    continue
        
        # Gender extraction
        gender_keys = ['gender', 'Gender', 'sex', 'Sex']
        for key in gender_keys:
            if key in patient_root:
                value = patient_root[key]
                if isinstance(value, dict) and '#text' in value:
                    value = value['#text']
                demographics_data['gender'] = str(value)
                break
        
        # Date of birth
        dob_keys = ['dateOfBirth', 'dob', 'birthDate', 'DOB']
        for key in dob_keys:
            if key in patient_root:
                value = patient_root[key]
                if isinstance(value, dict) and '#text' in value:
                    value = value['#text']
                demographics_data['date_of_birth'] = str(value)
                break
        
        # Contact information
        contact_keys = ['address', 'phone', 'emergencyContact']
        for key in contact_keys:
            if key in patient_root:
                value = patient_root[key]
                if isinstance(value, dict) and '#text' in value:
                    value = value['#text']
                demographics_data[key.lower()] = str(value)
        
        return Demographics(**demographics_data)
    
    def _extract_medical_history(self, patient_root: Dict) -> List[MedicalEvent]:
        """Extract medical history events."""
        events = []
        history_keys = ['medicalHistory', 'history', 'events', 'visits']
        
        for key in history_keys:
            if key in patient_root:
                history_data = patient_root[key]
                if isinstance(history_data, list):
                    for event_data in history_data:
                        event = self._parse_medical_event(event_data)
                        if event:
                            events.append(event)
                elif isinstance(history_data, dict):
                    # Single event or nested structure
                    if 'event' in history_data:
                        event_list = history_data['event']
                        if isinstance(event_list, list):
                            for event_data in event_list:
                                event = self._parse_medical_event(event_data)
                                if event:
                                    events.append(event)
                        else:
                            event = self._parse_medical_event(event_list)
                            if event:
                                events.append(event)
                    else:
                        event = self._parse_medical_event(history_data)
                        if event:
                            events.append(event)
        
        return events
    
    def _parse_medical_event(self, event_data: Dict) -> Optional[MedicalEvent]:
        """Parse individual medical event."""
        if not isinstance(event_data, dict):
            return None
        
        try:
            event_id = str(event_data.get('id', f"event_{len(str(event_data))}"))
            date = str(event_data.get('date', 'unknown'))
            event_type = str(event_data.get('type', 'visit'))
            description = str(event_data.get('description', 'Medical event'))
            
            return MedicalEvent(
                event_id=event_id,
                date=date,
                event_type=event_type,
                description=description,
                provider=event_data.get('provider'),
                location=event_data.get('location'),
                severity=event_data.get('severity'),
                status=event_data.get('status')
            )
        except Exception as e:
            logger.warning(f"Failed to parse medical event: {e}")
            return None
    
    def _extract_medications(self, patient_root: Dict) -> List[Medication]:
        """Extract medication information."""
        medications = []
        med_keys = ['medications', 'medication', 'drugs', 'prescriptions']
        
        for key in med_keys:
            if key in patient_root:
                med_data = patient_root[key]
                if isinstance(med_data, list):
                    for med in med_data:
                        medication = self._parse_medication(med)
                        if medication:
                            medications.append(medication)
                elif isinstance(med_data, dict):
                    if 'medication' in med_data:
                        med_list = med_data['medication']
                        if isinstance(med_list, list):
                            for med in med_list:
                                medication = self._parse_medication(med)
                                if medication:
                                    medications.append(medication)
                        else:
                            medication = self._parse_medication(med_list)
                            if medication:
                                medications.append(medication)
                    else:
                        medication = self._parse_medication(med_data)
                        if medication:
                            medications.append(medication)
        
        return medications
    
    def _parse_medication(self, med_data: Dict) -> Optional[Medication]:
        """Parse individual medication."""
        if not isinstance(med_data, dict):
            return None
        
        try:
            med_id = str(med_data.get('id', f"med_{len(str(med_data))}"))
            name = str(med_data.get('name', 'Unknown medication'))
            dosage = str(med_data.get('dosage', 'Unknown dosage'))
            frequency = str(med_data.get('frequency', 'Unknown frequency'))
            
            return Medication(
                medication_id=med_id,
                name=name,
                dosage=dosage,
                frequency=frequency,
                start_date=med_data.get('startDate'),
                end_date=med_data.get('endDate'),
                prescribing_physician=med_data.get('prescribingPhysician'),
                indication=med_data.get('indication'),
                status=med_data.get('status', 'active')
            )
        except Exception as e:
            logger.warning(f"Failed to parse medication: {e}")
            return None
    
    def _extract_procedures(self, patient_root: Dict) -> List[Procedure]:
        """Extract procedure information."""
        procedures = []
        proc_keys = ['procedures', 'procedure', 'surgeries', 'operations']
        
        for key in proc_keys:
            if key in patient_root:
                proc_data = patient_root[key]
                if isinstance(proc_data, list):
                    for proc in proc_data:
                        procedure = self._parse_procedure(proc)
                        if procedure:
                            procedures.append(procedure)
                elif isinstance(proc_data, dict):
                    if 'procedure' in proc_data:
                        proc_list = proc_data['procedure']
                        if isinstance(proc_list, list):
                            for proc in proc_list:
                                procedure = self._parse_procedure(proc)
                                if procedure:
                                    procedures.append(procedure)
                        else:
                            procedure = self._parse_procedure(proc_list)
                            if procedure:
                                procedures.append(procedure)
                    else:
                        procedure = self._parse_procedure(proc_data)
                        if procedure:
                            procedures.append(procedure)
        
        return procedures
    
    def _parse_procedure(self, proc_data: Dict) -> Optional[Procedure]:
        """Parse individual procedure."""
        if not isinstance(proc_data, dict):
            return None
        
        try:
            proc_id = str(proc_data.get('id', f"proc_{len(str(proc_data))}"))
            name = str(proc_data.get('name', 'Unknown procedure'))
            date = str(proc_data.get('date', 'unknown'))
            provider = str(proc_data.get('provider', 'Unknown provider'))
            
            return Procedure(
                procedure_id=proc_id,
                name=name,
                date=date,
                provider=provider,
                location=proc_data.get('location'),
                indication=proc_data.get('indication'),
                outcome=proc_data.get('outcome'),
                complications=proc_data.get('complications'),
                cpt_code=proc_data.get('cptCode')
            )
        except Exception as e:
            logger.warning(f"Failed to parse procedure: {e}")
            return None
    
    def _extract_diagnoses(self, patient_root: Dict) -> List[Diagnosis]:
        """Extract diagnosis information."""
        diagnoses = []
        diag_keys = ['diagnoses', 'diagnosis', 'conditions', 'problems']
        
        for key in diag_keys:
            if key in patient_root:
                diag_data = patient_root[key]
                if isinstance(diag_data, list):
                    for diag in diag_data:
                        diagnosis = self._parse_diagnosis(diag)
                        if diagnosis:
                            diagnoses.append(diagnosis)
                elif isinstance(diag_data, dict):
                    if 'diagnosis' in diag_data:
                        diag_list = diag_data['diagnosis']
                        if isinstance(diag_list, list):
                            for diag in diag_list:
                                diagnosis = self._parse_diagnosis(diag)
                                if diagnosis:
                                    diagnoses.append(diagnosis)
                        else:
                            diagnosis = self._parse_diagnosis(diag_list)
                            if diagnosis:
                                diagnoses.append(diagnosis)
                    else:
                        diagnosis = self._parse_diagnosis(diag_data)
                        if diagnosis:
                            diagnoses.append(diagnosis)
        
        return diagnoses
    
    def _parse_diagnosis(self, diag_data: Dict) -> Optional[Diagnosis]:
        """Parse individual diagnosis."""
        if not isinstance(diag_data, dict):
            return None
        
        try:
            diag_id = str(diag_data.get('id', f"diag_{len(str(diag_data))}"))
            condition = str(diag_data.get('condition', diag_data.get('name', 'Unknown condition')))
            date_diagnosed = str(diag_data.get('dateDiagnosed', diag_data.get('date', 'unknown')))
            
            return Diagnosis(
                diagnosis_id=diag_id,
                condition=condition,
                date_diagnosed=date_diagnosed,
                icd_10_code=diag_data.get('icd10Code'),
                severity=diag_data.get('severity'),
                status=diag_data.get('status', 'active'),
                diagnosing_physician=diag_data.get('diagnosingPhysician'),
                notes=diag_data.get('notes')
            )
        except Exception as e:
            logger.warning(f"Failed to parse diagnosis: {e}")
            return None
    
    def _names_match(self, extracted_name: str, expected_name: str) -> bool:
        """Check if extracted name matches expected name (fuzzy matching)."""
        if not extracted_name or not expected_name:
            return False
        
        # Normalize names for comparison
        extracted_norm = re.sub(r'[^a-zA-Z]', '', extracted_name.lower())
        expected_norm = re.sub(r'[^a-zA-Z]', '', expected_name.lower())
        
        # Exact match
        if extracted_norm == expected_norm:
            return True
        
        # Check if one contains the other
        if extracted_norm in expected_norm or expected_norm in extracted_norm:
            return True
        
        # Check similarity (simple character overlap)
        if len(extracted_norm) > 0 and len(expected_norm) > 0:
            overlap = len(set(extracted_norm) & set(expected_norm))
            total = len(set(extracted_norm) | set(expected_norm))
            similarity = overlap / total if total > 0 else 0
            return similarity > 0.7
        
        return False
    
    def _count_extracted_fields(self, patient_data: PatientData) -> Dict[str, int]:
        """Count extracted fields for audit logging."""
        return {
            'medical_events': len(patient_data.medical_history),
            'medications': len(patient_data.medications),
            'procedures': len(patient_data.procedures),
            'diagnoses': len(patient_data.diagnoses),
            'has_demographics': bool(patient_data.demographics.age or patient_data.demographics.gender)
        }