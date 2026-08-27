import os
import json
import sys

# Ensure backend path is in Python environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai.patient_agent import PatientAgent
from ai.patient_state import PatientAgentState
from routes.simulation import get_dynamic_vitals

def load_case_data(case_id="chest_pain_001"):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    case_path = os.path.join(current_dir, "case_engine", "cases", f"{case_id}.json")
    if not os.path.exists(case_path):
        raise FileNotFoundError(f"Case file not found at: {case_path}")
    with open(case_path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_dryrun():
    print("=" * 60)
    print("   DIAGNOS SIMULATOR: DETAILED PATIENT INTERACTIVE DRYRUN")
    print("=" * 60)
    
    # Prompt for case ID choice
    print("Available cases for testing:")
    print(" 1. chest_pain_001 (Daniel Thomas - Acute Coronary Syndrome)")
    print(" 2. chest_pain_007 (Timothy White - Acute Ischemic Stroke)")
    print(" 3. chest_pain_008 (Betty Hernandez - Acute Appendicitis)")
    print(" 4. Enter custom case ID (e.g. chest_pain_003, chest_pain_025, etc.)")
    print("-" * 60)
    try:
        choice = input("Select a case [1-4, default is 1]: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting dryrun.")
        return
    case_id = "chest_pain_001"
    if choice == "2":
        case_id = "chest_pain_007"
    elif choice == "3":
        case_id = "chest_pain_008"
    elif choice == "4":
        try:
            case_id = input("Enter case ID: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting dryrun.")
            return
            
    try:
        case_data = load_case_data(case_id)
    except Exception as e:
        print(f"Error loading case: {e}")
        return

    patient = case_data.get("patient", {})
    print(f"Patient Name:    {patient.get('name', 'Unknown')}")
    print(f"Age & Sex:       {patient.get('age', 'Unknown')}yo {patient.get('sex', 'Unknown')}")
    print(f"Chief Complaint: {patient.get('chief_complaint', 'Unknown')}")
    print("-" * 60)

    # Initialize State
    agent_state = PatientAgentState.initialize_from_case(case_data)
    agent = PatientAgent(case_data)
    
    chat_history = []
    
    # Render Initial Statement
    initial_statement = patient.get("initial_statement", "Hello doctor.")
    print(f"\n[Patient Initial Statement]")
    print(f"Patient: \"{initial_statement}\"")
    chat_history.append({"role": "patient", "text": initial_statement})
    
    # Loop
    turn = 1
    while True:
        # Get current state details
        emotion_dict = agent_state.emotion.to_dict()
        label = agent_state.emotion.get_label()
        cue = agent_state.emotion.get_behavioral_cue()
        
        # Calculate dynamic vitals
        vitals = get_dynamic_vitals(patient.get("vitals", {}), emotion_dict)
        
        print("\n" + "-"*40)
        print(f"  [Turn {turn} Patient Status]")
        print(f"  Emotion Label:   {label}")
        print(f"  Behavioral Cue:  {cue}")
        print(f"  Vitals:          HR: {vitals['hr']} | BP: {vitals['bp']} | RR: {vitals['rr']}/min | SpO2: {vitals['spo2']} | Temp: {vitals['temp']}")
        print(f"  Internal States: Anxiety: {emotion_dict['anxiety']} | Fear: {emotion_dict['fear']} | Trust: {emotion_dict['trust']} | Pain: {emotion_dict['pain']}")
        print("-" * 40)
        
        try:
            student_msg = input("\nAsk Patient / Reassure (or type 'exit' to quit): ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting dryrun.")
            break
            
        if not student_msg.strip():
            continue
            
        if student_msg.lower().strip() in ["exit", "quit", "q"]:
            print("Exiting dryrun. Thank you!")
            break
            
        print(f"\nYou (Doctor): \"{student_msg}\"")
        
        # Add to history
        chat_history.append({"role": "student", "text": student_msg})
        
        # Generate response
        updated_state, output = agent.generate_response(
            state=agent_state,
            conversation_history=chat_history,
            student_message=student_msg
        )
        
        # Update current state
        agent_state = updated_state
        
        # Print response
        print(f"\nPatient: \"{output['response']}\"")
        if output.get("revealed_information"):
            print(f"  [System Log: Discovered facts: {output['revealed_information']}]")
            
        # Add response to history
        chat_history.append({"role": "patient", "text": output["response"]})
        turn += 1

if __name__ == "__main__":
    run_dryrun()
