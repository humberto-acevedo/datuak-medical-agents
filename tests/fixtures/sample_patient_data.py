"""Sample anonymized patient data for integration testing."""

# Sample patient XML data for testing
SAMPLE_PATIENT_XML_GOOD = """<?xml version="1.0" encoding="UTF-8"?>
<patient_record>
    <demographics>
        <patient_id>TEST_P001</patient_id>
        <name>John Doe</name>
        <date_of_birth>1978-03-15</date_of_birth>
        <age>45</age>
        <gender>Male</gender>
        <address>
            <street>123 Main St</street>
            <city>Anytown</city>
            <state>NY</state>
            <zip>12345</zip>
        </address>
    </demographics>
    
    <medical_history>
        <diagnoses>
            <diagnosis>
                <code>E11.9</code>
                <description>Type 2 diabetes mellitus without complications</description>
                <date_diagnosed>2020-01-15</date_diagnosed>
                <status>Active</status>
                <severity>Moderate</severity>
            </diagnosis>
            <diagnosis>
                <code>I10</code>
                <description>Essential hypertension</description>
                <date_diagnosed>2019-06-20</date_diagnosed>
                <status>Active</status>
                <severity>Mild</severity>
            </diagnosis>
            <diagnosis>
                <code>Z87.891</code>
                <description>Personal history of nicotine dependence</description>
                <date_diagnosed>2018-03-10</date_diagnosed>
                <status>Resolved</status>
                <severity>Mild</severity>
            </diagnosis>
        </diagnoses>
        
        <medications>
            <medication>
                <name>Metformin</name>
                <dosage>500mg</dosage>
                <frequency>Twice daily</frequency>
                <start_date>2020-01-15</start_date>
                <status>Active</status>
                <indication>Type 2 diabetes</indication>
            </medication>
            <medication>
                <name>Lisinopril</name>
                <dosage>10mg</dosage>
                <frequency>Once daily</frequency>
                <start_date>2019-06-20</start_date>
                <status>Active</status>
                <indication>Hypertension</indication>
            </medication>
            <medication>
                <name>Atorvastatin</name>
                <dosage>20mg</dosage>
                <frequency>Once daily</frequency>
                <start_date>2021-02-10</start_date>
                <status>Active</status>
                <indication>Hyperlipidemia</indication>
            </medication>
        </medications>
        
        <procedures>
            <procedure>
                <code>80053</code>
                <description>Comprehensive metabolic panel</description>
                <date>2023-08-15</date>
                <provider>Dr. Smith</provider>
                <results>Normal glucose levels, well-controlled diabetes</results>
            </procedure>
            <procedure>
                <code>93000</code>
                <description>Electrocardiogram</description>
                <date>2023-06-10</date>
                <provider>Dr. Johnson</provider>
                <results>Normal sinus rhythm, no abnormalities</results>
            </procedure>
        </procedures>
        
        <allergies>
            <allergy>
                <allergen>Penicillin</allergen>
                <reaction>Rash</reaction>
                <severity>Moderate</severity>
                <date_identified>2015-05-20</date_identified>
            </allergy>
        </allergies>
        
        <vital_signs>
            <reading date="2023-08-15">
                <blood_pressure>
                    <systolic>128</systolic>
                    <diastolic>82</diastolic>
                </blood_pressure>
                <heart_rate>72</heart_rate>
                <temperature>98.6</temperature>
                <weight>180</weight>
                <height>70</height>
                <bmi>25.8</bmi>
            </reading>
        </vital_signs>
    </medical_history>
    
    <clinical_notes>
        <note date="2023-08-15" provider="Dr. Smith">
            Patient presents for routine diabetes follow-up. Blood glucose levels well-controlled 
            on current metformin regimen. Blood pressure slightly elevated but within acceptable 
            range on lisinopril. Patient reports good adherence to medications and dietary 
            modifications. Recommends continuing current treatment plan with follow-up in 3 months.
        </note>
        <note date="2023-06-10" provider="Dr. Johnson">
            Annual cardiovascular screening. ECG shows normal sinus rhythm. Patient has good 
            exercise tolerance. Blood pressure controlled on current antihypertensive therapy. 
            Lipid panel pending. Continue current medications.
        </note>
    </clinical_notes>
</patient_record>"""

SAMPLE_PATIENT_XML_COMPLEX = """<?xml version="1.0" encoding="UTF-8"?>
<patient_record>
    <demographics>
        <patient_id>TEST_P002</patient_id>
        <name>Jane Smith</name>
        <date_of_birth>1965-11-22</date_of_birth>
        <age>58</age>
        <gender>Female</gender>
        <address>
            <street>456 Oak Ave</street>
            <city>Springfield</city>
            <state>CA</state>
            <zip>90210</zip>
        </address>
    </demographics>
    
    <medical_history>
        <diagnoses>
            <diagnosis>
                <code>C50.911</code>
                <description>Malignant neoplasm of unspecified site of right female breast</description>
                <date_diagnosed>2022-03-10</date_diagnosed>
                <status>Active</status>
                <severity>Severe</severity>
                <stage>Stage II</stage>
            </diagnosis>
            <diagnosis>
                <code>F32.9</code>
                <description>Major depressive disorder, single episode, unspecified</description>
                <date_diagnosed>2022-04-15</date_diagnosed>
                <status>Active</status>
                <severity>Moderate</severity>
            </diagnosis>
            <diagnosis>
                <code>M79.3</code>
                <description>Panniculitis, unspecified</description>
                <date_diagnosed>2023-01-20</date_diagnosed>
                <status>Active</status>
                <severity>Mild</severity>
            </diagnosis>
            <diagnosis>
                <code>Z85.3</code>
                <description>Personal history of malignant neoplasm of breast</description>
                <date_diagnosed>2023-09-01</date_diagnosed>
                <status>Resolved</status>
                <severity>N/A</severity>
            </diagnosis>
        </diagnoses>
        
        <medications>
            <medication>
                <name>Tamoxifen</name>
                <dosage>20mg</dosage>
                <frequency>Once daily</frequency>
                <start_date>2022-05-01</start_date>
                <status>Active</status>
                <indication>Breast cancer treatment</indication>
            </medication>
            <medication>
                <name>Sertraline</name>
                <dosage>50mg</dosage>
                <frequency>Once daily</frequency>
                <start_date>2022-04-20</start_date>
                <status>Active</status>
                <indication>Depression</indication>
            </medication>
            <medication>
                <name>Ondansetron</name>
                <dosage>8mg</dosage>
                <frequency>As needed</frequency>
                <start_date>2022-03-15</start_date>
                <status>Active</status>
                <indication>Nausea from chemotherapy</indication>
            </medication>
        </medications>
        
        <procedures>
            <procedure>
                <code>19301</code>
                <description>Mastectomy, partial</description>
                <date>2022-03-25</date>
                <provider>Dr. Wilson</provider>
                <results>Successful tumor removal, clear margins</results>
            </procedure>
            <procedure>
                <code>96413</code>
                <description>Chemotherapy administration</description>
                <date>2022-04-10</date>
                <provider>Dr. Brown</provider>
                <results>Tolerated well, mild nausea</results>
            </procedure>
            <procedure>
                <code>77067</code>
                <description>Screening mammography</description>
                <date>2023-08-20</date>
                <provider>Dr. Davis</provider>
                <results>No evidence of recurrence</results>
            </procedure>
        </procedures>
        
        <allergies>
            <allergy>
                <allergen>Latex</allergen>
                <reaction>Contact dermatitis</reaction>
                <severity>Mild</severity>
                <date_identified>2020-01-15</date_identified>
            </allergy>
            <allergy>
                <allergen>Shellfish</allergen>
                <reaction>Anaphylaxis</reaction>
                <severity>Severe</severity>
                <date_identified>2018-07-04</date_identified>
            </allergy>
        </allergies>
        
        <vital_signs>
            <reading date="2023-08-20">
                <blood_pressure>
                    <systolic>118</systolic>
                    <diastolic>76</diastolic>
                </blood_pressure>
                <heart_rate>68</heart_rate>
                <temperature>98.4</temperature>
                <weight>145</weight>
                <height>65</height>
                <bmi>24.1</bmi>
            </reading>
        </vital_signs>
    </medical_history>
    
    <clinical_notes>
        <note date="2023-08-20" provider="Dr. Wilson">
            Patient doing well 18 months post-mastectomy. Recent mammography shows no evidence 
            of recurrence. Continuing tamoxifen therapy as planned. Patient reports improved 
            mood on sertraline. Discussed importance of regular follow-up and self-examination.
        </note>
        <note date="2023-05-15" provider="Dr. Brown">
            Oncology follow-up. Patient completed adjuvant chemotherapy successfully. 
            Tolerating tamoxifen well with minimal side effects. Blood work within normal 
            limits. Continue current treatment plan with quarterly monitoring.
        </note>
    </clinical_notes>
</patient_record>"""

SAMPLE_PATIENT_XML_MINIMAL = """<?xml version="1.0" encoding="UTF-8"?>
<patient_record>
    <demographics>
        <patient_id>TEST_P003</patient_id>
        <name>Bob Johnson</name>
        <date_of_birth>1990-07-08</date_of_birth>
        <age>33</age>
        <gender>Male</gender>
    </demographics>
    
    <medical_history>
        <diagnoses>
            <diagnosis>
                <code>J45.9</code>
                <description>Asthma, unspecified</description>
                <date_diagnosed>2021-09-15</date_diagnosed>
                <status>Active</status>
                <severity>Mild</severity>
            </diagnosis>
        </diagnoses>
        
        <medications>
            <medication>
                <name>Albuterol</name>
                <dosage>90mcg</dosage>
                <frequency>As needed</frequency>
                <start_date>2021-09-15</start_date>
                <status>Active</status>
                <indication>Asthma</indication>
            </medication>
        </medications>
        
        <procedures>
            <procedure>
                <code>94010</code>
                <description>Spirometry</description>
                <date>2021-09-15</date>
                <provider>Dr. Lee</provider>
                <results>Mild obstructive pattern consistent with asthma</results>
            </procedure>
        </procedures>
        
        <allergies>
            <allergy>
                <allergen>Dust mites</allergen>
                <reaction>Respiratory symptoms</reaction>
                <severity>Mild</severity>
                <date_identified>2021-08-01</date_identified>
            </allergy>
        </allergies>
    </medical_history>
    
    <clinical_notes>
        <note date="2021-09-15" provider="Dr. Lee">
            Young adult with new diagnosis of asthma. Symptoms well-controlled with 
            rescue inhaler. Educated on proper inhaler technique and trigger avoidance. 
            Follow-up as needed.
        </note>
    </clinical_notes>
</patient_record>"""

SAMPLE_PATIENT_XML_INVALID = """<?xml version="1.0" encoding="UTF-8"?>
<patient_record>
    <demographics>
        <patient_id></patient_id>
        <name></name>
        <age>invalid_age</age>
        <gender>Unknown</gender>
    </demographics>
    
    <medical_history>
        <diagnoses>
            <diagnosis>
                <code>INVALID_CODE</code>
                <description></description>
                <date_diagnosed>invalid_date</date_diagnosed>
                <status>Unknown</status>
            </diagnosis>
        </diagnoses>
        
        <medications>
            <medication>
                <name></name>
                <dosage>invalid_dosage</dosage>
                <frequency></frequency>
            </medication>
        </medications>
    </medical_history>
</patient_record>"""

# Expected analysis results for validation
EXPECTED_ANALYSIS_RESULTS = {
    "TEST_P001": {
        "patient_id": "TEST_P001",
        "name": "John Doe",
        "age": 45,
        "gender": "Male",
        "key_conditions": [
            "Type 2 diabetes mellitus without complications",
            "Essential hypertension",
            "Personal history of nicotine dependence"
        ],
        "medications": ["Metformin", "Lisinopril", "Atorvastatin"],
        "expected_research_topics": [
            "diabetes management",
            "hypertension treatment",
            "cardiovascular risk",
            "metabolic syndrome"
        ],
        "quality_expectations": {
            "min_quality_score": 0.8,
            "max_hallucination_risk": 0.2,
            "required_sections": ["summary", "conditions", "medications", "research"]
        }
    },
    
    "TEST_P002": {
        "patient_id": "TEST_P002",
        "name": "Jane Smith",
        "age": 58,
        "gender": "Female",
        "key_conditions": [
            "Malignant neoplasm of unspecified site of right female breast",
            "Major depressive disorder, single episode, unspecified",
            "Personal history of malignant neoplasm of breast"
        ],
        "medications": ["Tamoxifen", "Sertraline", "Ondansetron"],
        "expected_research_topics": [
            "breast cancer treatment",
            "tamoxifen therapy",
            "cancer survivorship",
            "depression in cancer patients"
        ],
        "quality_expectations": {
            "min_quality_score": 0.8,
            "max_hallucination_risk": 0.2,
            "required_sections": ["summary", "conditions", "medications", "research"]
        }
    },
    
    "TEST_P003": {
        "patient_id": "TEST_P003",
        "name": "Bob Johnson",
        "age": 33,
        "gender": "Male",
        "key_conditions": ["Asthma, unspecified"],
        "medications": ["Albuterol"],
        "expected_research_topics": [
            "asthma management",
            "bronchodilator therapy",
            "respiratory health"
        ],
        "quality_expectations": {
            "min_quality_score": 0.7,  # Lower due to minimal data
            "max_hallucination_risk": 0.3,
            "required_sections": ["summary", "conditions", "medications"]
        }
    }
}

# Performance benchmarks for testing
PERFORMANCE_BENCHMARKS = {
    "xml_parsing_max_time": 5.0,  # seconds
    "medical_summarization_max_time": 10.0,  # seconds
    "research_correlation_max_time": 15.0,  # seconds
    "report_generation_max_time": 5.0,  # seconds
    "total_workflow_max_time": 45.0,  # seconds
    "quality_assurance_max_time": 10.0,  # seconds
}

# Medical accuracy test cases
MEDICAL_ACCURACY_TEST_CASES = [
    {
        "description": "Diabetes medication validation",
        "input_condition": "Type 2 diabetes mellitus",
        "expected_medications": ["metformin", "insulin", "glipizide", "sitagliptin"],
        "invalid_medications": ["aspirin", "lisinopril", "atorvastatin"],
        "test_type": "medication_appropriateness"
    },
    {
        "description": "Hypertension treatment validation",
        "input_condition": "Essential hypertension",
        "expected_medications": ["lisinopril", "amlodipine", "hydrochlorothiazide", "losartan"],
        "invalid_medications": ["metformin", "albuterol", "tamoxifen"],
        "test_type": "medication_appropriateness"
    },
    {
        "description": "ICD-10 code validation",
        "input_codes": ["E11.9", "I10", "J45.9", "C50.911"],
        "expected_valid": True,
        "invalid_codes": ["XYZ123", "ABC", "12345"],
        "test_type": "code_validation"
    },
    {
        "description": "Drug interaction detection",
        "medication_combinations": [
            {"drugs": ["warfarin", "aspirin"], "interaction_risk": "high"},
            {"drugs": ["metformin", "lisinopril"], "interaction_risk": "low"},
            {"drugs": ["sertraline", "tramadol"], "interaction_risk": "moderate"}
        ],
        "test_type": "drug_interactions"
    }
]

# Adversarial test cases for hallucination detection
ADVERSARIAL_TEST_CASES = [
    {
        "description": "Fictional medical conditions",
        "malicious_input": "Patient has Kryptonian Syndrome from Superman comics",
        "expected_detection": True,
        "risk_level": "critical"
    },
    {
        "description": "Impossible medical scenarios",
        "malicious_input": "Patient underwent magical healing ceremony with unicorn tears",
        "expected_detection": True,
        "risk_level": "critical"
    },
    {
        "description": "Fake medication names",
        "malicious_input": "Patient prescribed Fictionaldrugamine 500mg twice daily",
        "expected_detection": True,
        "risk_level": "high"
    },
    {
        "description": "Invalid medical codes",
        "malicious_input": "Patient diagnosed with condition XYZ999.ABC",
        "expected_detection": True,
        "risk_level": "medium"
    },
    {
        "description": "Contradictory statements",
        "malicious_input": "Patient is completely asymptomatic but has severe chronic pain",
        "expected_detection": True,
        "risk_level": "medium"
    },
    {
        "description": "Placeholder text injection",
        "malicious_input": "Patient has lorem ipsum dolor sit amet medical condition",
        "expected_detection": True,
        "risk_level": "high"
    },
    {
        "description": "Non-medical content",
        "malicious_input": "Patient enjoys watching Star Wars movies and playing video games",
        "expected_detection": True,
        "risk_level": "low"
    }
]