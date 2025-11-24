"""Enhanced XML Parser for HL7 CDA medical records with proper section extraction."""

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


class CDAXMLParser:
    """Parses HL7 CDA medical XML records and extracts structured data."""
    
    # HL7 CDA Section LOINC codes
    SECTION_CODES = {
        'MEDICATIONS': '10160-0',
        'PROBLEMS': '11450-4',
        'PROCEDURES': '47519-4',
        'ALLERGIES': '48765-2',
        'VITAL_SIGNS': '8716-3',
        'RESULTS': '30954-2',
        'IMMUNIZATIONS': '11369-6',
        'SOCIAL_HISTORY': '29762-2',
        'ENCOUNTERS': '46240-8',
    }
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """Initialize CDA XML parser."""
        self.audit_logger = audit_logger or AuditLogger()
    
    def parse_patient_xml(self, xml_content: str, patient_name: str) -> PatientData:
        """
        Parse HL7 CDA patient XML content and extract structured medical data.
        
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
            
            # Parse XML to dictionary
            xml_dict = xmltodict.parse(xml_content)
            
            # Check if this is a CDA document
            if 'ClinicalDocument' not in xml_dict:
                logger.warning("Not a CDA document, falling back to generic parser")
                # Could fall back to original parser here
                raise XMLParsingError("Not an HL7 CDA document")
            
            clinical_doc = xml_dict['ClinicalDocument']
            
            # Extract patient information from CDA structure
            patient_data = self._extract_cda_patient_data(clinical_doc, xml_content, patient_name)
            
            # Validate extracted data
            validation_errors = patient_data.validate()
            if validation_errors:
                logger.warning(f"Patient data validation warnings: {validation_errors}")
            
            # Log successful parsing
            self.audit_logger.log_data_access(
                patient_id=patient_data.patient_id,
                operation="cda_xml_parse_success",
                details={"fields_extracted": self._count_extracted_fields(patient_data)}
            )
            
            return patient_data
            
        except ET.ParseError as e:
            error_msg = f"XML parsing failed: {str(e)}"
            logger.error(error_msg)
            raise XMLParsingError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during CDA XML parsing: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise XMLParsingError(error_msg)
    
    def _validate_xml_structure(self, xml_content: str) -> None:
        """Validate XML structure."""
        try:
            parser = etree.XMLParser(recover=False)
            etree.fromstring(xml_content.encode('utf-8'), parser)
        except etree.XMLSyntaxError as e:
            raise XMLParsingError(f"Invalid XML syntax: {str(e)}")
    
    def _extract_cda_patient_data(self, clinical_doc: Dict, raw_xml: str, expected_name: str) -> PatientData:
        """Extract patient data from CDA Clinical Document."""
        
        # Extract from recordTarget -> patientRole -> patient
        record_target = clinical_doc.get('recordTarget', {})
        patient_role = record_target.get('patientRole', {})
        patient = patient_role.get('patient', {})
        
        # Extract patient ID (use document ID as fallback)
        patient_id = self._extract_cda_patient_id(patient_role, clinical_doc)
        
        # Extract patient name
        patient_name = self._extract_cda_patient_name(patient)
        
        # Validate name match
        if not self._names_match(patient_name, expected_name):
            logger.warning(f"Patient name mismatch: expected '{expected_name}', found '{patient_name}'")
        
        # Extract demographics
        demographics = self._extract_cda_demographics(patient, patient_role)
        
        # Extract medical data from structured body sections
        structured_body = clinical_doc.get('component', {}).get('structuredBody', {})
        components = structured_body.get('component', [])
        
        # Ensure components is a list
        if not isinstance(components, list):
            components = [components] if components else []
        
        # Extract data from sections
        medications = self._extract_cda_medications(components)
        procedures = self._extract_cda_procedures(components)
        diagnoses = self._extract_cda_problems(components)
        medical_history = self._extract_cda_encounters(components)
        
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
    
    def _extract_cda_patient_id(self, patient_role: Dict, clinical_doc: Dict) -> str:
        """Extract patient ID from CDA structure."""
        # Try patient role ID first
        if 'id' in patient_role:
            id_obj = patient_role['id']
            if isinstance(id_obj, dict):
                # Check for extension (medical record number)
                if '@extension' in id_obj and id_obj['@extension'] != 'UNK':
                    return str(id_obj['@extension'])
                # Check for root
                if '@root' in id_obj:
                    return str(id_obj['@root'])
        
        # Fall back to document ID
        if 'id' in clinical_doc:
            doc_id = clinical_doc['id']
            if isinstance(doc_id, dict):
                if '@root' in doc_id:
                    root = doc_id['@root']
                    # Clean up the root to make it more readable
                    return root.replace('2.16.840.1.113883.3.', 'MRN-')
        
        return "unknown_patient_id"
    
    def _extract_cda_patient_name(self, patient: Dict) -> str:
        """Extract patient name from CDA patient element."""
        if 'name' not in patient:
            return "Unknown Patient"
        
        name_obj = patient['name']
        if isinstance(name_obj, dict):
            given = name_obj.get('given', '')
            family = name_obj.get('family', '')
            
            # Handle text nodes
            if isinstance(given, dict) and '#text' in given:
                given = given['#text']
            if isinstance(family, dict) and '#text' in family:
                family = family['#text']
            
            if given and family:
                return f"{given} {family}"
        
        return "Unknown Patient"
    
    def _extract_cda_demographics(self, patient: Dict, patient_role: Dict) -> Demographics:
        """Extract demographics from CDA patient element."""
        demographics_data = {}
        
        # Extract birth date
        if 'birthTime' in patient:
            birth_time = patient['birthTime']
            if isinstance(birth_time, dict) and '@value' in birth_time:
                birth_value = birth_time['@value']
                # Parse CDA date format (YYYYMMDD)
                try:
                    if len(birth_value) >= 8:
                        year = int(birth_value[0:4])
                        month = int(birth_value[4:6])
                        day = int(birth_value[6:8])
                        birth_date = datetime(year, month, day)
                        demographics_data['date_of_birth'] = birth_date.strftime('%Y-%m-%d')
                        
                        # Calculate age
                        today = datetime.now()
                        age = today.year - birth_date.year
                        if (today.month, today.day) < (birth_date.month, birth_date.day):
                            age -= 1
                        demographics_data['age'] = age
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse birth date: {birth_value}, error: {e}")
        
        # Extract gender
        if 'administrativeGenderCode' in patient:
            gender_code = patient['administrativeGenderCode']
            if isinstance(gender_code, dict) and '@code' in gender_code:
                code = gender_code['@code']
                # Map HL7 gender codes
                gender_map = {'M': 'Male', 'F': 'Female', 'UN': 'Unknown'}
                demographics_data['gender'] = gender_map.get(code, code)
        
        # Extract address
        if 'addr' in patient_role:
            addr = patient_role['addr']
            if isinstance(addr, dict):
                address_parts = []
                if 'streetAddressLine' in addr:
                    address_parts.append(str(addr['streetAddressLine']))
                if 'city' in addr:
                    address_parts.append(str(addr['city']))
                if 'state' in addr:
                    address_parts.append(str(addr['state']))
                if 'postalCode' in addr:
                    address_parts.append(str(addr['postalCode']))
                if address_parts:
                    demographics_data['address'] = ', '.join(address_parts)
        
        return Demographics(**demographics_data)
    
    def _find_section_by_code(self, components: List[Dict], code: str) -> Optional[Dict]:
        """Find a section by its LOINC code."""
        for component in components:
            if 'section' in component:
                section = component['section']
                if 'code' in section:
                    section_code = section['code']
                    if isinstance(section_code, dict) and section_code.get('@code') == code:
                        return section
        return None
    
    def _extract_cda_medications(self, components: List[Dict]) -> List[Medication]:
        """Extract medications from CDA medication section."""
        medications = []
        
        # Find medications section
        med_section = self._find_section_by_code(components, self.SECTION_CODES['MEDICATIONS'])
        if not med_section:
            logger.info("No medications section found")
            return medications
        
        # Get entries
        entries = med_section.get('entry', [])
        if not isinstance(entries, list):
            entries = [entries] if entries else []
        
        for entry in entries:
            if 'substanceAdministration' in entry:
                med = self._parse_cda_medication(entry['substanceAdministration'])
                if med:
                    medications.append(med)
        
        logger.info(f"Extracted {len(medications)} medications from CDA")
        return medications
    
    def _parse_cda_medication(self, substance_admin: Dict) -> Optional[Medication]:
        """Parse a CDA substanceAdministration entry."""
        try:
            # Extract medication ID
            med_id = "unknown"
            if 'id' in substance_admin:
                id_obj = substance_admin['id']
                if isinstance(id_obj, dict) and '@extension' in id_obj:
                    med_id = id_obj['@extension']
            
            # Extract medication name and code from consumable
            name = "Unknown medication"
            if 'consumable' in substance_admin:
                consumable = substance_admin['consumable']
                if 'manufacturedProduct' in consumable:
                    manufactured = consumable['manufacturedProduct']
                    if 'manufacturedMaterial' in manufactured:
                        material = manufactured['manufacturedMaterial']
                        if 'code' in material:
                            code_obj = material['code']
                            if isinstance(code_obj, dict):
                                name = code_obj.get('@displayName', name)
            
            # Extract dosage
            dosage = "Unknown dosage"
            if 'doseQuantity' in substance_admin:
                dose_qty = substance_admin['doseQuantity']
                if isinstance(dose_qty, dict) and '@value' in dose_qty:
                    dosage = f"{dose_qty['@value']} {dose_qty.get('@unit', '')}"
            
            # Extract dates
            start_date = None
            end_date = None
            if 'effectiveTime' in substance_admin:
                eff_time = substance_admin['effectiveTime']
                if isinstance(eff_time, dict):
                    if 'low' in eff_time:
                        low = eff_time['low']
                        if isinstance(low, dict) and '@value' in low:
                            start_date = self._parse_cda_date(low['@value'])
                    if 'high' in eff_time:
                        high = eff_time['high']
                        if isinstance(high, dict) and '@value' in high:
                            end_date = self._parse_cda_date(high['@value'])
            
            # Extract status
            status = "unknown"
            if 'statusCode' in substance_admin:
                status_code = substance_admin['statusCode']
                if isinstance(status_code, dict) and '@code' in status_code:
                    status = status_code['@code']
            
            return Medication(
                medication_id=med_id,
                name=name,
                dosage=dosage,
                frequency="Not Specified",  # CDA doesn't always have frequency
                start_date=start_date,
                end_date=end_date,
                status=status
            )
        except Exception as e:
            logger.warning(f"Failed to parse CDA medication: {e}")
            return None
    
    def _extract_cda_procedures(self, components: List[Dict]) -> List[Procedure]:
        """Extract procedures from CDA procedures section."""
        procedures = []
        
        # Find procedures section
        proc_section = self._find_section_by_code(components, self.SECTION_CODES['PROCEDURES'])
        if not proc_section:
            logger.info("No procedures section found")
            return procedures
        
        # Get entries
        entries = proc_section.get('entry', [])
        if not isinstance(entries, list):
            entries = [entries] if entries else []
        
        for entry in entries:
            if 'procedure' in entry:
                proc = self._parse_cda_procedure(entry['procedure'])
                if proc:
                    procedures.append(proc)
        
        logger.info(f"Extracted {len(procedures)} procedures from CDA")
        return procedures
    
    def _parse_cda_procedure(self, procedure: Dict) -> Optional[Procedure]:
        """Parse a CDA procedure entry."""
        try:
            # Extract procedure ID
            proc_id = "unknown"
            if 'id' in procedure:
                id_obj = procedure['id']
                if isinstance(id_obj, dict) and '@extension' in id_obj:
                    proc_id = id_obj['@extension']
            
            # Extract procedure name
            name = "Unknown procedure"
            if 'code' in procedure:
                code_obj = procedure['code']
                if isinstance(code_obj, dict):
                    name = code_obj.get('@displayName', name)
            
            # Extract date
            date = "unknown"
            if 'effectiveTime' in procedure:
                eff_time = procedure['effectiveTime']
                if isinstance(eff_time, dict) and '@value' in eff_time:
                    date = self._parse_cda_date(eff_time['@value'])
            
            return Procedure(
                procedure_id=proc_id,
                name=name,
                date=date,
                provider="Unknown provider"
            )
        except Exception as e:
            logger.warning(f"Failed to parse CDA procedure: {e}")
            return None
    
    def _extract_cda_problems(self, components: List[Dict]) -> List[Diagnosis]:
        """Extract problems/diagnoses from CDA problems section."""
        diagnoses = []
        
        # Find problems section
        prob_section = self._find_section_by_code(components, self.SECTION_CODES['PROBLEMS'])
        if not prob_section:
            logger.info("No problems section found")
            return diagnoses
        
        # Get entries
        entries = prob_section.get('entry', [])
        if not isinstance(entries, list):
            entries = [entries] if entries else []
        
        for entry in entries:
            # CDA problems are usually in act -> entryRelationship -> observation
            if 'act' in entry:
                act = entry['act']
                if 'entryRelationship' in act:
                    entry_rel = act['entryRelationship']
                    if not isinstance(entry_rel, list):
                        entry_rel = [entry_rel]
                    for rel in entry_rel:
                        if 'observation' in rel:
                            diag = self._parse_cda_problem(rel['observation'])
                            if diag:
                                diagnoses.append(diag)
        
        logger.info(f"Extracted {len(diagnoses)} diagnoses from CDA")
        return diagnoses
    
    def _parse_cda_problem(self, observation: Dict) -> Optional[Diagnosis]:
        """Parse a CDA problem observation."""
        try:
            # Extract diagnosis ID
            diag_id = "unknown"
            if 'id' in observation:
                id_obj = observation['id']
                if isinstance(id_obj, dict) and '@extension' in id_obj:
                    diag_id = id_obj['@extension']
            
            # Extract condition name
            condition = "Unknown condition"
            icd_10_code = None
            if 'value' in observation:
                value_obj = observation['value']
                if isinstance(value_obj, dict):
                    condition = value_obj.get('@displayName', condition)
                    # Check for ICD-10 code
                    if value_obj.get('@codeSystem') == '2.16.840.1.113883.6.90':
                        icd_10_code = value_obj.get('@code')
            
            # Extract date
            date_diagnosed = "unknown"
            if 'effectiveTime' in observation:
                eff_time = observation['effectiveTime']
                if isinstance(eff_time, dict):
                    if 'low' in eff_time:
                        low = eff_time['low']
                        if isinstance(low, dict) and '@value' in low:
                            date_diagnosed = self._parse_cda_date(low['@value'])
            
            # Extract status
            status = "active"
            if 'statusCode' in observation:
                status_code = observation['statusCode']
                if isinstance(status_code, dict) and '@code' in status_code:
                    status = status_code['@code']
            
            return Diagnosis(
                diagnosis_id=diag_id,
                condition=condition,
                date_diagnosed=date_diagnosed,
                icd_10_code=icd_10_code,
                status=status
            )
        except Exception as e:
            logger.warning(f"Failed to parse CDA problem: {e}")
            return None
    
    def _extract_cda_encounters(self, components: List[Dict]) -> List[MedicalEvent]:
        """Extract encounters from CDA encounters section."""
        events = []
        
        # Find encounters section
        enc_section = self._find_section_by_code(components, self.SECTION_CODES['ENCOUNTERS'])
        if not enc_section:
            logger.info("No encounters section found")
            return events
        
        # Get entries
        entries = enc_section.get('entry', [])
        if not isinstance(entries, list):
            entries = [entries] if entries else []
        
        for entry in entries:
            if 'encounter' in entry:
                event = self._parse_cda_encounter(entry['encounter'])
                if event:
                    events.append(event)
        
        logger.info(f"Extracted {len(events)} encounters from CDA")
        return events
    
    def _parse_cda_encounter(self, encounter: Dict) -> Optional[MedicalEvent]:
        """Parse a CDA encounter entry."""
        try:
            # Extract encounter ID
            event_id = "unknown"
            if 'id' in encounter:
                id_obj = encounter['id']
                if isinstance(id_obj, dict) and '@extension' in id_obj:
                    event_id = id_obj['@extension']
            
            # Extract encounter type
            event_type = "encounter"
            if 'code' in encounter:
                code_obj = encounter['code']
                if isinstance(code_obj, dict):
                    event_type = code_obj.get('@displayName', event_type)
            
            # Extract date
            date = "unknown"
            if 'effectiveTime' in encounter:
                eff_time = encounter['effectiveTime']
                if isinstance(eff_time, dict) and '@value' in eff_time:
                    date = self._parse_cda_date(eff_time['@value'])
            
            return MedicalEvent(
                event_id=event_id,
                date=date,
                event_type=event_type,
                description=f"Medical encounter: {event_type}"
            )
        except Exception as e:
            logger.warning(f"Failed to parse CDA encounter: {e}")
            return None
    
    def _parse_cda_date(self, date_str: str) -> str:
        """Parse CDA date format (YYYYMMDDHHMMSS) to readable format."""
        try:
            if len(date_str) >= 8:
                year = date_str[0:4]
                month = date_str[4:6]
                day = date_str[6:8]
                return f"{month}/{day}/{year}"
        except (ValueError, IndexError):
            pass
        return date_str
    
    def _names_match(self, extracted_name: str, expected_name: str) -> bool:
        """Check if extracted name matches expected name (fuzzy matching)."""
        if not extracted_name or not expected_name:
            return False
        
        # Normalize names
        extracted_norm = re.sub(r'[^a-zA-Z]', '', extracted_name.lower())
        expected_norm = re.sub(r'[^a-zA-Z]', '', expected_name.lower())
        
        # Exact match
        if extracted_norm == expected_norm:
            return True
        
        # Check if one contains the other
        if extracted_norm in expected_norm or expected_norm in extracted_norm:
            return True
        
        # Check similarity
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
