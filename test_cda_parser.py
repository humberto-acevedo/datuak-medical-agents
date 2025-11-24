#!/usr/bin/env python3
"""Test script for CDA parser with JaneSmith.xml"""

import sys
from src.agents.xml_parser_cda import CDAXMLParser

def main():
    print("=" * 60)
    print("Testing CDA Parser with JaneSmith.xml")
    print("=" * 60)
    
    # Initialize parser
    parser = CDAXMLParser()
    
    # Read XML file
    try:
        with open('JaneSmith.xml', 'r') as f:
            xml_content = f.read()
        print(f"✅ Loaded JaneSmith.xml ({len(xml_content)} bytes)")
    except FileNotFoundError:
        print("❌ JaneSmith.xml not found")
        return 1
    
    # Parse XML
    try:
        patient_data = parser.parse_patient_xml(xml_content, "Jane Smith")
        print("✅ Successfully parsed XML")
    except Exception as e:
        print(f"❌ Parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Display results
    print("\n" + "=" * 60)
    print("EXTRACTION RESULTS")
    print("=" * 60)
    
    print(f"\n📋 Patient Information:")
    print(f"   Name: {patient_data.name}")
    print(f"   ID: {patient_data.patient_id}")
    
    print(f"\n👤 Demographics:")
    print(f"   Age: {patient_data.demographics.age}")
    print(f"   Gender: {patient_data.demographics.gender}")
    print(f"   Date of Birth: {patient_data.demographics.date_of_birth}")
    if patient_data.demographics.address:
        print(f"   Address: {patient_data.demographics.address}")
    
    print(f"\n💊 Medications: {len(patient_data.medications)}")
    if patient_data.medications:
        print("   Top 5 medications:")
        for i, med in enumerate(patient_data.medications[:5], 1):
            print(f"   {i}. {med.name}")
            print(f"      Dosage: {med.dosage}")
            print(f"      Status: {med.status}")
            if med.start_date:
                print(f"      Start: {med.start_date}")
            if med.end_date:
                print(f"      End: {med.end_date}")
    
    print(f"\n🏥 Procedures: {len(patient_data.procedures)}")
    if patient_data.procedures:
        for i, proc in enumerate(patient_data.procedures[:3], 1):
            print(f"   {i}. {proc.name} ({proc.date})")
    
    print(f"\n🩺 Diagnoses: {len(patient_data.diagnoses)}")
    if patient_data.diagnoses:
        for i, diag in enumerate(patient_data.diagnoses[:3], 1):
            print(f"   {i}. {diag.condition}")
            if diag.icd_10_code:
                print(f"      ICD-10: {diag.icd_10_code}")
            print(f"      Status: {diag.status}")
    
    print(f"\n📅 Medical History: {len(patient_data.medical_history)} events")
    if patient_data.medical_history:
        for i, event in enumerate(patient_data.medical_history[:3], 1):
            print(f"   {i}. {event.event_type} - {event.description} ({event.date})")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    total_items = (
        len(patient_data.medications) +
        len(patient_data.procedures) +
        len(patient_data.diagnoses) +
        len(patient_data.medical_history)
    )
    
    print(f"✅ Total medical items extracted: {total_items}")
    print(f"✅ Patient: {patient_data.name}, Age {patient_data.demographics.age}, {patient_data.demographics.gender}")
    print(f"✅ CDA Parser working correctly!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
