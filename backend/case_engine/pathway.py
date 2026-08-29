from typing import List, Dict, Any

def generate_case_expected_pathway(case_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Generates a structured, case-specific clinical reasoning pathway.
    If 'expected_pathway' is explicitly defined in case_data, it returns that.
    Otherwise, it dynamically generates the optimal sequence from the case's:
    - Patient presentation & chief complaint
    - Targeted history questions & symptoms
    - Physical examinations
    - Required investigations & key findings
    - Differential diagnoses
    - Correct final diagnosis
    """
    if not case_data or not isinstance(case_data, dict):
        return [
            {"label": "Patient Encounter Review", "type": "system"},
            {"label": "Clinical History & Risk Assessment", "type": "question"},
            {"label": "Targeted Physical Examination", "type": "examination"},
            {"label": "Diagnostic Investigations", "type": "investigation"},
            {"label": "Submit Clinical Diagnosis", "type": "decision"}
        ]

    # 1. Use explicitly defined pathway if provided
    raw_pathway = case_data.get("expected_pathway")
    if raw_pathway and isinstance(raw_pathway, list) and len(raw_pathway) > 0:
        cleaned = []
        for node in raw_pathway:
            if isinstance(node, dict) and "label" in node:
                cleaned.append({
                    "label": str(node["label"]),
                    "type": str(node.get("type", "system"))
                })
            elif isinstance(node, str):
                cleaned.append({
                    "label": node,
                    "type": "system"
                })
        if cleaned:
            return cleaned

    # 2. Dynamic generation from case attributes
    pathway: List[Dict[str, str]] = []

    patient = case_data.get("patient", {})
    patient_name = patient.get("name", "Patient")
    chief_complaint = patient.get("chief_complaint") or case_data.get("title", "Clinical Presentation")
    
    # Step 1: Initial Encounter / System Briefing
    pathway.append({
        "label": f"Meet {patient_name} ({chief_complaint})",
        "type": "system"
    })

    # Step 2: Targeted History & Risk Factors
    criteria = case_data.get("evaluation_criteria", {})
    crit_questions = criteria.get("critical_questions", [])
    complaint_lower = chief_complaint.lower()
    
    if "chest" in complaint_lower or "heart" in complaint_lower:
        hist_label = "Interview Pain Characteristics & Cardiac Risk Factors"
    elif "breath" in complaint_lower or "wheez" in complaint_lower or "cough" in complaint_lower:
        hist_label = "Interview Dyspnea Onset, Triggers & Medication History"
    elif "abdom" in complaint_lower or "stomach" in complaint_lower or "quadrant" in complaint_lower:
        hist_label = "Interview Pain Progression, GI Symptoms & Anorexia"
    elif "speech" in complaint_lower or "weakness" in complaint_lower or "stroke" in complaint_lower:
        hist_label = "Interview Exact Time of Onset & Neurological Progression"
    elif "headache" in complaint_lower or "head" in complaint_lower:
        hist_label = "Interview Aura, Photophobia & Previous Headache Pattern"
    elif "flank" in complaint_lower or "fever" in complaint_lower or "urin" in complaint_lower:
        hist_label = "Interview Urinary Symptoms, Fever Chills & Flank Pain"
    elif "leg" in complaint_lower or "calf" in complaint_lower or "swell" in complaint_lower:
        hist_label = "Interview Travel History, Immobility & Swelling Onset"
    else:
        hist_label = "Targeted Patient Interview & Risk Factor Identification"
        
    pathway.append({
        "label": hist_label,
        "type": "question"
    })

    # Step 3: Targeted Physical Examination
    examinations = case_data.get("examinations", [])
    exam_label = "Perform General & Targeted Physical Exam"
    
    if examinations:
        # Find exam that aligns best with complaint
        if "speech" in complaint_lower or "weakness" in complaint_lower or "headache" in complaint_lower:
            neuro_exam = next((e for e in examinations if e.get("type") == "neurological"), None)
            exam_label = "Perform Comprehensive Neurological Examination" if neuro_exam else "Perform Neurological Exam"
        elif "abdom" in complaint_lower or "stomach" in complaint_lower:
            exam_label = "Perform Abdominal Examination (Assess Peritoneal Signs)"
        elif "breath" in complaint_lower or "wheez" in complaint_lower:
            exam_label = "Perform Respiratory Examination (Auscultate Breath Sounds)"
        elif "flank" in complaint_lower or "urin" in complaint_lower:
            exam_label = "Perform CVA Tenderness & Abdominal Physical Exam"
        elif "leg" in complaint_lower or "calf" in complaint_lower:
            exam_label = "Perform Lower Extremity Vascular & Palpation Exam"
        elif "chest" in complaint_lower:
            if "pericarditis" in (criteria.get("correct_diagnosis", "").lower()):
                exam_label = "Perform Cardiovascular Exam (Auscultate Friction Rub)"
            else:
                exam_label = "Perform Cardiovascular & General Physical Exam"
                
    pathway.append({
        "label": exam_label,
        "type": "examination"
    })

    # Step 4: Required Diagnostic Investigations
    investigations = case_data.get("investigations", [])
    inv_map = {inv.get("id"): inv for inv in investigations if isinstance(inv, dict) and "id" in inv}
    req_inv_ids = criteria.get("required_investigations", [])

    # Purpose hints for common investigations
    inv_purpose_hints = {
        "ecg": "Identify Ischemic Changes & Rhythm",
        "troponin": "Assess Myocardial Necrosis",
        "ct_head": "Rule Out Intracranial Hemorrhage",
        "ct_abdomen": "Confirm Acute Appendiceal Inflammation",
        "cbc": "Assess Inflammatory & Hematologic Markers",
        "cxr": "Evaluate Lung Fields & Rule Out Pneumothorax",
        "leg_ultrasound": "Detect Venous Occlusion / Thrombus",
        "urinalysis": "Detect Pyuria, Nitrites & Bacteriuria",
        "glucose": "Evaluate Glycemic Control",
        "electrolytes": "Check Serum Chemistry",
    }

    if req_inv_ids:
        for inv_id in req_inv_ids:
            inv_obj = inv_map.get(inv_id)
            inv_name = inv_obj.get("name") if inv_obj else inv_id.upper()
            purpose = inv_purpose_hints.get(inv_id, "Diagnostic Evaluation")
            pathway.append({
                "label": f"Order {inv_name} ({purpose})",
                "type": "investigation"
            })
    else:
        # Fallback to first 2 investigations
        for inv in investigations[:2]:
            pathway.append({
                "label": f"Order {inv.get('name', 'Investigation')}",
                "type": "investigation"
            })

    # Step 5: Final Decision / Correct Diagnosis
    correct_diagnosis = criteria.get("correct_diagnosis") or case_data.get("title", "Final Diagnosis")
    pathway.append({
        "label": f"Diagnose {correct_diagnosis}",
        "type": "decision"
    })

    return pathway
