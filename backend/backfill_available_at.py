import os
import glob
import json

CASES_DIR = "case_engine/cases"

AVAILABLE_AT = {
    "ecg": ["tertiary", "chc", "phc"],
    "cbc": ["tertiary", "chc"],
    "glucose": ["tertiary", "chc", "phc"],
    "urinalysis": ["tertiary", "chc"],
    "troponin": ["tertiary"],
    "electrolytes": ["tertiary", "chc"],
    "cxr": ["tertiary", "chc"],
    "ct_angio": ["tertiary"],
    "ct_head": ["tertiary"],
    "ct_abdomen": ["tertiary"],
    "leg_ultrasound": ["tertiary"]
}

def get_referral_criteria(diagnosis: str):
    dx = diagnosis.lower()
    
    if any(x in dx for x in ["acute coronary syndrome", "stroke", "appendicitis", "pyelonephritis", "deep vein thrombosis", "dvt", "acute ischemic stroke"]):
        return {
            "red_flags": ["Severe acute presentation requiring advanced imaging or intervention", "Hemodynamic instability"],
            "correct_disposition_by_tier": {
                "tertiary": "manage_locally",
                "chc": "manage_locally",
                "phc": "refer"
            }
        }
    
    if any(x in dx for x in ["gastroesophageal reflux disease", "gerd", "migraine", "panic attack"]):
        return {
            "red_flags": ["Refractory symptoms despite initial treatment", "Presence of alarm symptoms (e.g. weight loss, focal neuro signs)"],
            "correct_disposition_by_tier": {
                "tertiary": "manage_locally",
                "chc": "manage_locally",
                "phc": "manage_locally"
            }
        }
    
    if "stable angina" in dx:
        return {
            "red_flags": ["Unstable angina symptoms (pain at rest)", "Refractory to nitroglycerin"],
            "correct_disposition_by_tier": {
                "tertiary": "manage_locally",
                "chc": "manage_locally",
                "phc": "refer" # Need cardiology referral for stress test
            }
        }
        
    if "pericarditis" in dx:
        return {
            "red_flags": ["Suspected cardiac tamponade", "Large effusion", "Hemodynamic compromise"],
            "correct_disposition_by_tier": {
                "tertiary": "manage_locally",
                "chc": "manage_locally",
                "phc": "refer" # Often requires echo to rule out effusion
            }
        }
        
    if "asthma" in dx:
        return {
            "red_flags": ["Status asthmaticus", "Silent chest", "SpO2 < 92% despite nebulization"],
            "correct_disposition_by_tier": {
                "tertiary": "manage_locally",
                "chc": "manage_locally",
                "phc": "manage_locally" # Basic nebulizers usually available at PHC
            }
        }

    return {
        "red_flags": ["Unstable vitals", "Diagnostic uncertainty requiring advanced workup"],
        "correct_disposition_by_tier": {
            "tertiary": "manage_locally",
            "chc": "manage_locally",
            "phc": "refer"
        }
    }

def process_cases():
    files = glob.glob(os.path.join(CASES_DIR, "*.json"))
    changed = 0
    for f in files:
        with open(f, "r") as fp:
            data = json.load(fp)
            
        for inv in data.get("investigations", []):
            iid = inv["id"]
            if iid in AVAILABLE_AT:
                inv["available_at"] = AVAILABLE_AT[iid]
            else:
                inv["available_at"] = ["tertiary", "chc", "phc"]
                
        eval_crit = data.get("evaluation_criteria", {})
        diag = eval_crit.get("correct_diagnosis", "")
        eval_crit["referral_criteria"] = get_referral_criteria(diag)
        data["evaluation_criteria"] = eval_crit
        
        with open(f, "w") as fp:
            json.dump(data, fp, indent=2)
        changed += 1
    print(f"Updated {changed} case files.")

if __name__ == "__main__":
    process_cases()
