import os
import json
from typing import List, Dict, Any, Optional

class CaseEngine:
    def __init__(self, cases_dir: str = None):
        if cases_dir is None:
            # Locate relative to current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            cases_dir = os.path.join(current_dir, "cases")
        
        self.cases_dir = cases_dir
        self.cases: Dict[str, Dict[str, Any]] = {}
        self.load_all_cases()

    def load_all_cases(self):
        if not os.path.exists(self.cases_dir):
            os.makedirs(self.cases_dir, exist_ok=True)
            return

        for filename in os.listdir(self.cases_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(self.cases_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        case_data = json.load(f)
                        case_id = case_data.get("id")
                        if case_id:
                            self.cases[case_id] = case_data
                except Exception as e:
                    print(f"Error loading case file {filename}: {e}")

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        return self.cases.get(case_id)

    def list_cases(self) -> List[Dict[str, Any]]:
        briefs = []
        for cid, cdata in self.cases.items():
            patient = cdata.get("patient", {})
            briefs.append({
                "id": cid,
                "title": cdata.get("title"),
                "specialty": cdata.get("specialty"),
                "difficulty": cdata.get("difficulty"),
                "duration_mins": cdata.get("duration_mins", 20),
                "patient_age": patient.get("age"),
                "patient_sex": patient.get("sex"),
                "chief_complaint": patient.get("chief_complaint")
            })
        return briefs

# Instantiate a global case engine
case_engine = CaseEngine()
