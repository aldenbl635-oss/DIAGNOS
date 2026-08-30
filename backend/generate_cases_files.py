import os
import json
import random

# Lists of patient identity parameters
first_names_m = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian", "George", "Timothy"]
first_names_f = ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Sandra", "Margaret", "Ashley", "Kimberly", "Emily", "Donna", "Michelle", "Carol", "Amanda", "Dorothy", "Melissa", "Deborah"]
last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"]

occupations = ["Office Manager", "High School Teacher", "Software Engineer", "Truck Driver", "Corporate Accountant", "Construction Foreman", "Registered Nurse", "Retail Store Manager", "Electrician", "Sous Chef", "Graphic Designer", "Librarian", "Bank Teller", "Post Office Clerk", "Security Guard", "Real Estate Agent", "Paralegal", "Plumber", "Warehouse Supervisor", "Journalist"]

def generate_50_cases():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cases_dir = os.path.join(base_dir, "case_engine", "cases")
    os.makedirs(cases_dir, exist_ok=True)
    
    # 11 distinct corporate/clinical templates covering all body parts
    templates = ["ACS", "GERD", "Stable Angina", "Pericarditis", "Panic Attack", "Stroke", "Appendicitis", "Asthma", "Pyelonephritis", "DVT", "Migraine"]
    
    # Generate 50 new distinct cases starting from chest_pain_002
    for i in range(2, 52):
        sex = "Male" if random.random() > 0.45 else "Female"
        first = random.choice(first_names_m) if sex == "Male" else random.choice(first_names_f)
        last = random.choice(last_names)
        name = f"{first} {last}"
        age = random.randint(25, 75)
        occ = random.choice(occupations)
        
        diag_choice = templates[(i - 2) % len(templates)]
        case_id = f"chest_pain_{i:03d}"
        
        personality = {
            "baseline_anxiety": random.randint(40, 85),
            "emotional_sensitivity": random.randint(50, 85),
            "trustfulness": random.randint(45, 75),
            "cooperativeness": random.randint(50, 85),
            "health_literacy": random.choice([30, 40, 50, 60, 70]),
            "fear_of_death": random.randint(40, 90),
            "privacy_sensitivity": random.randint(30, 65),
            "assertiveness": random.randint(35, 70),
            "pain_tolerance": random.randint(25, 70),
            "distrust_of_medical": random.randint(15, 45)
        }
        
        # Default/Normal values for investigative results
        n_ecg_res, n_ecg_int = "Normal sinus rhythm, regular rate 72 bpm, no ST/T abnormalities.", "Normal ECG showing sinus rhythm."
        n_trop_res, n_trop_int = "Troponin I is < 0.01 ng/mL.", "Normal cardiac enzyme profile."
        n_cbc_res, n_cbc_int = "WBC: 6.4 x10^9/L, Hb: 13.8 g/dL, Platelets: 220 x10^9/L.", "Complete blood count is within normal references."
        n_gluc_res, n_gluc_int = "Random Blood Glucose: 98 mg/dL.", "Normal arterial glucose levels."
        n_elec_res, n_elec_int = "Sodium: 140 mEq/L, Potassium: 4.0 mEq/L.", "Serum electrolytes are within normal range."
        n_cxr_res, n_cxr_int = "Both lungs are hypolucent, no vascular congestion or consolidation.", "Normal chest X-ray profile."
        n_ct_angio_res, n_ct_angio_int = "Normal caliber aorta, no luminal narrowing, no dissection flap visible.", "Normal chest CT Angiography."
        n_ct_head_res, n_ct_head_int = "No acute hemorrhage, infarct, or midline shifts found in cranial structures.", "Normal CT Scan of the Head."
        n_ct_abd_res, n_ct_abd_int = "Stomach, liver, bowel loops, and appendix are normal size with no inflammatory changes.", "Normal CT Scan of the Abdomen."
        n_uri_res, n_uri_int = "Clear yellow appearance, negative nitrite, negative leukocyte esterase.", "Urinalysis is clear of infection signs."
        n_us_res, n_us_int = "Normal patency of left and right femoral veins with complete color Doppler signal.", "Normal leg vascular ultrasound."
        
        # Override based on diagnosis
        if diag_choice == "ACS":
            title = f"Cardiac Chest Pressure Variant {i-1}"
            specialty = "Emergency Medicine / Cardiology"
            difficulty = "Intermediate"
            chief_complaint = "Chest pressure"
            initial_statement = f"I've got this crushing, heavy weight right in the center of my chest. It started about 30 minutes ago and it's making me feel quite sick."
            
            bp = f"{random.randint(135, 160)}/{random.randint(85, 100)} mmHg"
            hr = f"{random.randint(95, 115)} bpm"
            spo2 = f"{random.randint(94, 97)}%"
            temp = f"36.{random.randint(5, 9)}°C"
            
            symptoms = [
                "Severe crushing chest pain/pressure under the breastbone",
                "Radiating to the left shoulder and left forearm",
                "Clammy cold sweating (diaphoresis) since pain onset",
                "Shortness of breath and mild stomach nausea (no vomiting)",
                "Constant discomfort, unaffected by deep breaths or positional shifts"
            ]
            pmh = ["Hypertension", "Hypercholesterolaemia", "Smoker"] if age > 40 else ["Hypertension", "Borderline Diabetes"]
            meds = ["Lisinopril 10mg once daily", "Atorvastatin 20mg once daily"]
            family = [f"Father had a myocardial infarction at age {random.randint(50, 60)}"]
            social = ["Smokes 1 pack of cigarettes per day", "High stress office job"]
            
            exam_gen = "Moderate distress, pale and sweating. Clutching chest."
            exam_cv = f"Tachycardia ({hr}) normal heart sounds, no murmurs."
            exam_resp = "Lungs clear to auscultation bilaterally."
            exam_abd = "Soft, non-distended, non-tender abdominal exam."
            exam_neuro = "Grossly intact, pupils responsive, no deficit."
            
            n_ecg_res = "ST-segment elevation of 2mm noted in anterior leads V1-V4."
            n_ecg_int = "Abnormal ECG showing acute anterior ST-elevation myocardial infarction (STEMI)."
            n_trop_res = "Troponin I is elevated at 2.1 ng/mL (Normal < 0.04 ng/mL)."
            n_trop_int = "Elevated cardiac enzymes matching myocardial necrosis."
            n_gluc_res = "Random Blood Glucose: 165 mg/dL."
            n_gluc_int = "Mild stress-induced hyperglycemia."
            
            diag_str = "Acute coronary syndrome"
            diag_subtypes = ["acute coronary syndrome", "stemi", "myocardial infarction", "acs"]
            req_inv = ["ecg", "troponin"]
            unnec_inv = ["ct_angio"]
            
        elif diag_choice == "GERD":
            title = f"Retrosternal Burning Variant {i-1}"
            specialty = "Emergency Medicine / Gastroenterology"
            difficulty = "Beginner"
            chief_complaint = "Heartburn"
            initial_statement = "My chest is burning, mostly right under my breastbone. It feels worse when I lie flat on my back or bend over."
            
            bp = f"{random.randint(118, 130)}/{random.randint(75, 85)} mmHg"
            hr = f"{random.randint(72, 88)} bpm"
            spo2 = "99%"
            temp = f"36.{random.randint(6, 8)}°C"
            
            symptoms = [
                "Burning substernal chest discomfort (heartburn)",
                "Worse in recumbent position (lying down flat)",
                "Associated with sour, acidic regurgitation in the throat",
                "Partially relieved by drinking water or taking antacids",
                "No sweating, no arm pain, normal breathing"
            ]
            pmh = ["Acid reflux", "Mild obesity"]
            meds = ["Antacids over-the-counter as needed"]
            family = ["Mother has history of gallstones"]
            social = ["Drinks 3-4 cups of coffee daily", "Eats late dinner before sleeping"]
            
            exam_gen = "Alert, comfortable, no acute distress."
            exam_cv = f"Regular heart rate ({hr}), normal chest sounds."
            exam_resp = "Normal breathing, no dyspnea."
            exam_abd = "Soft, abdomen is non-tender throughout except for very mild epigastric tenderness."
            exam_neuro = "Grossly intact, no motor or sensory loss."
            
            diag_str = "Gastroesophageal reflux disease"
            diag_subtypes = ["gerd", "acid reflux", "heartburn", "gastroesophageal reflux disease"]
            req_inv = ["ecg"]
            unnec_inv = ["ct_angio"]
            
        elif diag_choice == "Stable Angina":
            title = f"Exertional Chest Tightness Variant {i-1}"
            specialty = "Emergency Medicine / Cardiology"
            difficulty = "Intermediate"
            chief_complaint = "Chest tightness on effort"
            initial_statement = "I get this squeezing tightness in my chest when I walk quickly or climb stairs. It stops after I rest for a few minutes."
            
            bp = f"{random.randint(125, 142)}/{random.randint(80, 90)} mmHg"
            hr = f"{random.randint(80, 95)} bpm"
            spo2 = "98%"
            temp = f"36.{random.randint(6, 7)}°C"
            
            symptoms = [
                "Squeezing chest pressure triggered by physical exertion",
                "Relieved completely within 5 minutes of resting",
                "Does not radiate, no nausea or cold sweating",
                "Occurring intermittently for the past few weeks"
            ]
            pmh = ["Hypercholesterolaemia", "Type 2 Diabetes"]
            meds = ["Metformin 500mg twice daily", "Simvastatin 20mg nightly"]
            family = ["Uncle had bypass surgery in his late 50s"]
            social = ["Sedentary, minimal routine physical activity"]
            
            exam_gen = "Comfortable at rest, no distress."
            exam_cv = f"Regular rhythm, rate {hr}."
            exam_resp = "Clear breath sounds bilaterally."
            exam_abd = "Soft, non-tender abdominal exam."
            exam_neuro = "Intact neurology."
            
            diag_str = "Stable Angina"
            diag_subtypes = ["angina", "stable angina", "exertional chest pain"]
            req_inv = ["ecg", "troponin"]
            unnec_inv = ["ct_angio"]
            
        elif diag_choice == "Pericarditis":
            title = f"Positional Chest Pain Variant {i-1}"
            specialty = "Emergency Medicine / Cardiology"
            difficulty = "Intermediate"
            chief_complaint = "Sharp chest pain"
            initial_statement = "I have this sharp, stabbing pain in my chest. It gets a lot worse when I take a deep breath or lie down, but feels better when I sit forward."
            
            bp = f"{random.randint(110, 128)}/{random.randint(70, 82)} mmHg"
            hr = f"{random.randint(90, 105)} bpm"
            spo2 = "99%"
            temp = f"37.{random.randint(4, 9)}°C"
            
            symptoms = [
                "Sharp, stabbing pleuritic chest pain in the center of the chest",
                "Worse when taking a deep breath or coughing",
                "Severely worsened by lying flat on the back",
                "Significantly relieved by sitting up and leaning forward",
                "Had a common cold/runny nose about two weeks ago"
            ]
            pmh = ["Otherwise healthy, recent viral upper respiratory tract infection"]
            meds = ["None regularly"]
            family = ["No history of early heart disease"]
            social = ["Non-smoker, active runner"]
            
            exam_gen = "Alert, leans forward in chair to relieve pain. Appears in mild pain on deep inspiration."
            exam_cv = f"Mild tachycardia ({hr}). Scrubbing friction rub heard at left sternal border."
            exam_resp = "Clear lungs, shallow breaths due to pleural sharp pain."
            exam_abd = "Abdomen is soft, non-tender, non-distended."
            exam_neuro = "Intact, normal speech."
            
            n_ecg_res = "Diffuse ST-segment elevation with PR-segment depression in multiple leads."
            n_ecg_int = "ECG changes highly suggestive of acute pericarditis."
            
            diag_str = "Pericarditis"
            diag_subtypes = ["pericarditis", "acute pericarditis"]
            req_inv = ["ecg"]
            unnec_inv = ["ct_angio"]
            
        elif diag_choice == "Panic Attack":
            title = f"Acute Panic Presentation Variant {i-1}"
            specialty = "Emergency Medicine / Psychiatry"
            difficulty = "Beginner"
            chief_complaint = "Chest tightness & palpitations"
            initial_statement = "My heart is racing so fast and my chest feels extremely tight. I can't catch my breath, and I feel like I'm going to collapse."
            
            bp = f"{random.randint(130, 145)}/{random.randint(82, 92)} mmHg"
            hr = f"{random.randint(110, 125)} bpm"
            spo2 = "100%"
            temp = "36.7°C"
            
            symptoms = [
                "Severe chest tightness, rapid heart palpitations",
                "Shortness of breath, feeling like suffocating (hyperventilating)",
                "Numbness/tingling in fingers (paresthesias) and around mouth",
                "Extreme sense of doom, dizziness, feeling of falling"
            ]
            pmh = ["Generalized anxiety disorder", "Stressful life events"]
            meds = ["Alprazolam 0.25mg as needed for panic attacks"]
            family = ["Mother has history of anxiety and panic disorder"]
            social = ["Works long hours, high caffeine/energy drink intake"]
            
            exam_gen = "Highly anxious, breathing rapidly (hyperventilating). Trembling."
            exam_cv = f"Tachycardia ({hr}), regular, no murmurs."
            exam_resp = "Tachypnoea, lungs clear."
            exam_abd = "Soft, non-tender."
            exam_neuro = "Grossly intact, though patient complains of finger numbness."
            
            n_ecg_res = f"Sinus tachycardia with rate of {hr} bpm, normal axis, no ST change."
            n_ecg_int = "Sinus tachycardia, otherwise normal electrocardiogram."
            
            diag_str = "Panic attack"
            diag_subtypes = ["panic attack", "anxiety", "panic disorder"]
            req_inv = ["ecg"]
            unnec_inv = ["ct_angio"]
            
        elif diag_choice == "Stroke":
            title = f"Sudden Left-Sided Weakness Variant {i-1}"
            specialty = "Emergency Medicine / Neurology"
            difficulty = "Advanced"
            chief_complaint = "Slurred speech and arm weakness"
            initial_statement = "All of a sudden, my left arm and left leg felt extremely heavy and numb. My partner says my mouth is drooping on the left side."
            
            bp = f"{random.randint(165, 185)}/{random.randint(95, 105)} mmHg"
            hr = f"{random.randint(75, 90)} bpm"
            spo2 = f"{random.randint(96, 98)}%"
            temp = "36.6°C"
            
            symptoms = [
                "Sudden weakness and motor deficit in left arm and left leg",
                "Difficulty speaking clearly (slurred speech / dysarthria)",
                "Left-sided facial droop noticed by family",
                "Onset approximately 45 minutes ago",
                "No chest pain or dyspnoea"
            ]
            pmh = ["Hypertension", "Atrial Fibrillation", "High Cholesterol"]
            meds = ["Amlodipine 5mg daily", "Atorvastatin 20mg daily", "Aspirin 81mg daily"]
            family = ["Grandfather died of a stroke at age 70"]
            social = ["Non-smoker, drinks alcohol occasionally, retired clerk"]
            
            exam_gen = "Alert, slightly confused, appears anxious but speech is slurry."
            exam_cv = f"Regular heart rate ({hr}), pulse is strong."
            exam_resp = "Breathing normally, lungs clear bilaterally."
            exam_abd = "Soft, non-distended, non-tender."
            exam_neuro = "Left facial droop (sparing forehead). Significant motor weakness: left upper extremity 1/5 grip, left lower extremity 3/5. Speech is dysarthric. Right side normal."
            
            n_ct_head_res = "Non-contrast CT Head shows no acute intracranial hemorrhage. Early loss of gray-white matter differentiation in the right insular cortex is suggestive of acute ischemic infarct in the right MCA territory."
            n_ct_head_int = "Acute right middle cerebral artery (MCA) ischemic stroke. No cerebral bleed detected."
            
            diag_str = "Acute ischemic stroke"
            diag_subtypes = ["stroke", "ischemic stroke", "acute ischemic stroke", "brain stroke"]
            req_inv = ["ct_head"]
            unnec_inv = ["ct_angio"]
            
        elif diag_choice == "Appendicitis":
            title = f"Right Lower Quadrant Pain Variant {i-1}"
            specialty = "Emergency Medicine / General Surgery"
            difficulty = "Intermediate"
            chief_complaint = "Right lower quadrant abdominal pain"
            initial_statement = "My stomach started hurting this morning around my belly button. Over the afternoon, it moved down to my lower right side and is hurting so much now."
            
            bp = f"{random.randint(115, 128)}/{random.randint(75, 84)} mmHg"
            hr = f"{random.randint(90, 105)} bpm"
            spo2 = "99%"
            temp = f"38.{random.randint(1, 4)}°C"  # Fever
            
            symptoms = [
                "Migrating abdominal pain: starting in periumbilical area, shifting to RLQ",
                "Nausea, lost appetite (anorexia) since this morning",
                "Pain is severe, throbbing, and worsened by walking or jumping",
                "Low-grade fever and mild chills"
            ]
            pmh = ["Generally healthy, no prior surgeries"]
            meds = ["None regular"]
            family = ["Brother had appendectomy at age 14"]
            social = ["Non-smoker, college student, active lifestyle"]
            
            exam_gen = "Alert, looks flushed and uncomfortable. Lies still with knees slightly bent."
            exam_cv = f"Regular heart rate ({hr}), normal cardiovascular sounds."
            exam_resp = "Normal chest rise, lungs clear."
            exam_abd = "Soft, guarded. Exquisite tenderness in the Right Lower Quadrant (RLQ) at McBurney's point. Positive rebound tenderness and positive Rovsing's sign."
            exam_neuro = "Normal cranial nerves, reflexes intact."
            
            n_cbc_res = "WBC: 14.8 x10^9/L (Elevated; Normal 4.0-11.0), Neutrophils: 85% (Elevated), Hb: 14.0 g/dL."
            n_cbc_int = "Leukocytosis with left shift, highly indicative of acute bacterial inflammation/infection."
            n_ct_abd_res = "CT of the Abdomen/Pelvis shows a dilated, thick-walled appendix measuring 10.5 mm in diameter, surrounding fat stranding, hyperenhancement of the wall, and trace fluid in the right lower quadrant."
            n_ct_abd_int = "Acute appendicitis. Surgical consultation is recommended."
            
            diag_str = "Acute appendicitis"
            diag_subtypes = ["appendicitis", "acute appendicitis", "appendix infection"]
            req_inv = ["ct_abdomen", "cbc"]
            unnec_inv = ["ct_head"]
            
        elif diag_choice == "Asthma":
            title = f"Acute Bronchospasm & Wheezing Variant {i-1}"
            specialty = "Emergency Medicine / Pulmonology"
            difficulty = "Intermediate"
            chief_complaint = "Shortness of breath"
            initial_statement = "I can't breathe properly. My chest feels incredibly tight and I've been wheezing all morning. My albuterol inhaler isn't giving me any relief."
            
            bp = f"{random.randint(124, 138)}/{random.randint(80, 88)} mmHg"
            hr = f"{random.randint(102, 118)} bpm"
            spo2 = f"{random.randint(91, 93)}%"  # Hypoxia
            temp = "36.8°C"
            
            symptoms = [
                "Severe dyspnoea (shortness of breath) with difficulty exhaling",
                "Dry cough and audible expiratory wheezing",
                "Bilateral chest tightness",
                "Rescue inhaler (albuterol) failed to relieve symptoms today",
                "Triggers: yesterday was heavy pollen exposure outdoors"
            ]
            pmh = ["Asthma since childhood", "Allergic rhinitis"]
            meds = ["Fluticasone inhaler daily", "Albuterol inhaler as needed"]
            family = ["Mother has asthma and eczema"]
            social = ["Non-smoker, owns two cats, works as landscape architect"]
            
            exam_gen = "Attending physician notes tachypnoea and talking in short phrases. Mild accessory muscle use."
            exam_cv = f"Tachycardia ({hr}), regular rhythm, no murmurs."
            exam_resp = "Severe, diffuse expiratory wheezing throughout all lung fields bilaterally. Prolonged expiratory phase."
            exam_abd = "Soft, non-tender, non-distended abdominal wall."
            exam_neuro = "Grossly intact."
            
            n_cxr_res = "Chest X-ray shows hyperinflated lung fields and flattening of the diaphragms. No pneumothorax, effusion, or consolidated lobar pneumonia."
            n_cxr_int = "Hyperinflation consistent with diffuse airway obstruction (bronchospasm). No signs of pneumonia."
            
            diag_str = "Asthma exacerbation"
            diag_subtypes = ["asthma", "asthma exacerbation", "bronchospasm", "reactive airway"]
            req_inv = ["cxr"]
            unnec_inv = ["ct_head"]
            
        elif diag_choice == "Pyelonephritis":
            title = f"Flank Pain & Urinary Infection Variant {i-1}"
            specialty = "Emergency Medicine / Urology"
            difficulty = "Intermediate"
            chief_complaint = "Left flank pain and high fever"
            initial_statement = "I have this severe throbbing pain in my lower left back. It extends to my side. I've also had high fevers, shaking chills, and it hurts when I pee."
            
            bp = f"{random.randint(110, 122)}/{random.randint(68, 78)} mmHg"
            hr = f"{random.randint(98, 110)} bpm"
            spo2 = "98%"
            temp = f"39.{random.randint(0, 4)}°C"  # High Fever
            
            symptoms = [
                "Sharp throbbing pain in the left back (flank / costovertebral angle)",
                "Documented high fever and systemic chills",
                "Dysuria (burning painful urination) and urinating frequently",
                "Stomach nausea and vomiting twice this morning",
                "Symptoms started as mild bladder pressure 3 days ago"
            ]
            pmh = ["Frequent UTIs, none previously requiring hospitalization"]
            meds = ["Oral contraceptives daily"]
            family = ["Mother has history of kidney stones"]
            social = ["Non-smoker, high school teacher, drinks about 1L of water daily"]
            
            exam_gen = "Alert, looks moderately ill, shivering due to fever. In moderate distress."
            exam_cv = f"Tachycardia ({hr}), regular pulses."
            exam_resp = "Normal respiratory effort, lungs clear."
            exam_abd = "Abdomen is soft, completely non-tender on superficial and deep palpation. Epigastrium non-tender."
            exam_back = "Exquisite tenderness to percussion over the left Costovertebral Angle (CVA). Right CVA is normal."
            exam_neuro = "Intact, pupillary reflexes normal."
            
            n_cbc_res = "WBC: 15.2 x10^9/L (Elevated), Hb: 12.8 g/dL, Platelets: 280 x10^9/L."
            n_cbc_int = "Marked leukocytosis confirming active systemic bacterial infection."
            n_uri_res = "Turbid color, pH 6.5, Positive Nitrites, Positive Leukocyte Esterase, WBC: >50 per high-power-field (hpf), Urine Bacteria: Moderate."
            n_uri_int = "Active bacterial urinary tract infection (UTI) involving pyuria and bacteriuria; matches Pyelonephritis."
            
            diag_str = "Acute pyelonephritis"
            diag_subtypes = ["pyelonephritis", "acute pyelonephritis", "kidney infection", "urinary tract infection", "uti"]
            req_inv = ["urinalysis", "cbc"]
            unnec_inv = ["ct_head"]
            
        elif diag_choice == "DVT":
            title = f"Unilateral Calf Swelling & Pain Variant {i-1}"
            specialty = "Emergency Medicine / Vascular Medicine"
            difficulty = "Intermediate"
            chief_complaint = "Left leg swelling and pain"
            initial_statement = "My left calf has expanded, turned reddish, and is extremely tender to walk on. It started yesterday afternoon and got worse overnight."
            
            bp = f"{random.randint(120, 134)}/{random.randint(75, 84)} mmHg"
            hr = f"{random.randint(80, 92)} bpm"
            spo2 = "99%"
            temp = "37.1°C"
            
            symptoms = [
                "Severe aching, throbbing pain in the left calf",
                "Left leg swelling extending from the ankle to below the knee",
                "Local warmth and redness over the calf area",
                "Onset after returning from an 11-hour flight from Tokyo",
                "No dyspnoea, no chest tightness (no PE signs)"
            ]
            pmh = ["Mild varicose veins, none other"]
            meds = ["None regular"]
            family = ["Mother has history of cardiovascular events and blood clots"]
            social = ["Non-smoker, drinks alcohol socially, travel photographer"]
            
            exam_gen = "Alert, comfortable at rest, limping when standing."
            exam_cv = f"Regular heart rate ({hr}), pulse is symmetric."
            exam_resp = "Normal chest sounds, clear breath sounds."
            exam_abd = "Soft, abdomen is non-tender."
            exam_ext = "Left calf appears grossly swollen and erythematous (red). Left calf measures 38cm, right calf measures 34.5cm. Local warmth. Exquisite tenderness to deep calf muscle compression (positive Homans sign)."
            exam_neuro = "Gross muscle strength in toes intact."
            
            n_us_res = "Duplex Ultrasound of the left lower extremity shows non-compressibility of the popliteal vein with absent color flow, indicating total thrombotic occlusion."
            n_us_int = "Acute Deep Vein Thrombosis (DVT) of the left popliteal vein."
            
            diag_str = "Deep vein thrombosis"
            diag_subtypes = ["dvt", "deep vein thrombosis", "blood clot in leg", "popliteal dvt"]
            req_inv = ["leg_ultrasound"]
            unnec_inv = ["ct_head"]
            
        else: # Migraine
            title = f"Unilateral Throbbing Headache Variant {i-1}"
            specialty = "Emergency Medicine / Neurology"
            difficulty = "Beginner"
            chief_complaint = "Severe headache"
            initial_statement = "I have this blinding, throbbing pain behind my right eye and temple. The light in here is killing me, and I feel like I'm going to throw up."
            
            bp = f"{random.randint(126, 136)}/{random.randint(78, 86)} mmHg"
            hr = f"{random.randint(75, 88)} bpm"
            spo2 = "99%"
            temp = "36.7°C"
            
            symptoms = [
                "Severe throbbing/pulsating right-sided headache",
                "Onset preceded by seeing shimmering zigzag lines (visual aura)",
                "Severe sensitivity to light (photophobia) and sound (phonophobia)",
                "Nausea and loss of appetite",
                "No neck stiffness, no fever, scalp not tender"
            ]
            pmh = ["History of similar migraine headaches, usually relieved by sumatriptan"]
            meds = ["Sumatriptan 50mg as needed for migraine onset"]
            family = ["Mother has chronic migraines"]
            social = ["Graphic designer, long hours looking at bright computer monitors"]
            
            exam_gen = "Alert, in mild discomfort, keeps eyes covered. Prefers a dim room. No distress."
            exam_cv = f"Regular heart rate ({hr}), heart sounds normal."
            exam_resp = "Breathing normally."
            exam_abd = "Soft, non-tender abdominal exam."
            exam_neuro = "Neurological examination is completely normal. No focal motor weakness, no sensory loss. Cranial nerves II to XII are fully intact. Reflexes symmetric."
            
            diag_str = "Migraine headache"
            diag_subtypes = ["migraine", "headache", "migraine headache", "hemicrania"]
            req_inv = ["cbc"]  # screening
            unnec_inv = ["ct_head"] # clinically not required since it matches their historic pattern
            
        case_data = {
            "id": case_id,
            "title": title,
            "specialty": specialty,
            "difficulty": difficulty,
            "duration_mins": random.choice([15, 20, 25]),
            "patient": {
                "name": name,
                "age": age,
                "sex": sex,
                "occupation": occ,
                "vitals": {
                    "bp": bp,
                    "hr": hr,
                    "spo2": spo2,
                    "temp": temp
                },
                "chief_complaint": chief_complaint,
                "initial_statement": initial_statement
            },
            "clinical_facts": {
                "symptoms": symptoms,
                "past_medical_history": pmh,
                "medications": meds,
                "allergies": ["No known drug or food allergies"],
                "family_history": family,
                "social_history": social,
                "review_of_systems": [
                    f"Cardiovascular: pulse rate is {hr}, no active chest pain except as noted.",
                    "Respiratory: airways are open.",
                    "GI: abdominal sounds active.",
                    "Neuro: intact."
                ]
            },
            "patient_personality": personality,
            "patient_beliefs": [
                "I hope this is just a temporary strain that will pass.",
                "I've been under a lot of stress with my job.",
                "I'm terrified this might be something permanent or fatal."
            ],
            "patient_goals": [
                "Determine the core cause of these symptoms.",
                "Verify whether there is emergency intervention required.",
                "Get diagnostic results explained to me step by step."
            ],
            "examinations": [
                {"type": "general", "name": "General Physical Examination", "result": exam_gen},
                {"type": "cardiovascular", "name": "Cardiovascular Examination", "result": exam_cv},
                {"type": "respiratory", "name": "Respiratory Examination", "result": exam_resp},
                {"type": "abdominal", "name": "Abdominal Examination", "result": exam_abd},
                {"type": "neurological", "name": "Neurological Examination", "result": exam_neuro}
            ],
            "investigations": [
                {
                    "id": "ecg",
                    "name": "12-Lead Electrocardiogram (ECG)",
                    "cost": 100,
                    "category": "CARDIAC",
                    "turnaround": "Immediate",
                    "result": n_ecg_res,
                    "interpretation": n_ecg_int
                },
                {
                    "id": "troponin",
                    "name": "Cardiac Troponin I",
                    "cost": 150,
                    "category": "BLOOD TESTS",
                    "turnaround": "30 mins",
                    "result": n_trop_res,
                    "interpretation": n_trop_int
                },
                {
                    "id": "cbc",
                    "name": "Complete Blood Count (CBC)",
                    "cost": 80,
                    "category": "BLOOD TESTS",
                    "turnaround": "30 mins",
                    "result": n_cbc_res,
                    "interpretation": n_cbc_int
                },
                {
                    "id": "glucose",
                    "name": "Random Blood Glucose",
                    "cost": 50,
                    "category": "BLOOD TESTS",
                    "turnaround": "Immediate",
                    "result": n_gluc_res,
                    "interpretation": n_gluc_int
                },
                {
                    "id": "electrolytes",
                    "name": "Serum Electrolytes Panel",
                    "cost": 90,
                    "category": "BLOOD TESTS",
                    "turnaround": "30 mins",
                    "result": n_elec_res,
                    "interpretation": n_elec_int
                },
                {
                    "id": "cxr",
                    "name": "Chest X-ray (CXR)",
                    "cost": 180,
                    "category": "IMAGING",
                    "turnaround": "15 mins",
                    "result": n_cxr_res,
                    "interpretation": n_cxr_int
                },
                {
                    "id": "ct_angio",
                    "name": "CT Angiography of Chest",
                    "cost": 550,
                    "category": "IMAGING",
                    "turnaround": "45 mins",
                    "result": n_ct_angio_res,
                    "interpretation": n_ct_angio_int
                },
                {
                    "id": "ct_head",
                    "name": "CT Scan of Head (cranial assessment)",
                    "cost": 350,
                    "category": "IMAGING",
                    "turnaround": "30 mins",
                    "result": n_ct_head_res,
                    "interpretation": n_ct_head_int
                },
                {
                    "id": "ct_abdomen",
                    "name": "CT Scan of Abdomen & Pelvis",
                    "cost": 450,
                    "category": "IMAGING",
                    "turnaround": "45 mins",
                    "result": n_ct_abd_res,
                    "interpretation": n_ct_abd_int
                },
                {
                    "id": "urinalysis",
                    "name": "Urinalysis and Urine Culture",
                    "cost": 70,
                    "category": "URINE TESTS",
                    "turnaround": "15 mins",
                    "result": n_uri_res,
                    "interpretation": n_uri_int
                },
                {
                    "id": "leg_ultrasound",
                    "name": "Duplex Vascular Leg Ultrasound",
                    "cost": 220,
                    "category": "IMAGING",
                    "turnaround": "30 mins",
                    "result": n_us_res,
                    "interpretation": n_us_int
                }
            ],
            "differential_diagnoses": [
                "Acute coronary syndrome",
                "Gastroesophageal reflux disease",
                "Stable Angina",
                "Pericarditis",
                "Panic attack",
                "Acute ischemic stroke",
                "Acute appendicitis",
                "Asthma exacerbation",
                "Acute pyelonephritis",
                "Deep vein thrombosis",
                "Migraine headache"
            ],
            "evaluation_criteria": {
                "correct_diagnosis": diag_str,
                "correct_subtypes": diag_subtypes,
                "immediate_priority_keywords": [diag_str.lower()] + ([
                    "salvage", "aspirin", "tPA", "thrombolysis", "bronchodilator", "albuterol",
                    "antibiotic", "heparin", "coagualtion", "fluid resuscitation"
                ][:random.randint(2, 5)]),
                "critical_questions": [
                    "pain_characteristics",
                    "lifestyle_risk_factors",
                    "past_medical_history",
                    "associated_symptoms",
                    "family_history"
                ],
                "required_investigations": req_inv,
                "unnecessary_investigations": unnec_inv,
                "referral_criteria": {
                    "red_flags": ["Severe acute presentation or unstable vitals"],
                    "correct_disposition_by_tier": {
                        "tertiary": "manage_locally",
                        "chc": "manage_locally",
                        "phc": "refer" if diag_choice not in ["GERD", "Migraine", "Panic Attack", "Asthma"] else "manage_locally"
                    }
                }
            }
        }
        
        file_path = os.path.join(cases_dir, f"{case_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(case_data, f, indent=2)
            
    print(f"Generated 50 clinical case files representing all body parts in {cases_dir}")

if __name__ == "__main__":
    generate_50_cases()
