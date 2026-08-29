import json
import os

behaviors = []

# Let's define the 22 categories we want to cover
categories = [
    "clinical_question", "clarification", "empathy", "reassurance", "encouragement",
    "neutral", "supportive", "apology", "dismissive", "rude", "insulting", "judgmental",
    "threatening", "alarmist", "hopeless_statement", "frightening", "blame",
    "impatience", "uncertainty", "confusion", "professional_explanation", "inappropriate_medical_statement"
]

# We will build exactly 100 high quality examples programmatically with diverse semantic situations
# Situation templates:
# 1. Empathetic / Supportive (1-10)
# 2. Reassurance & Encouragement (11-20)
# 3. Alarmist & Frightening (21-30)
# 4. Hopelessness & Dead Ends (31-40)
# 5. Apology & Trust Recovery (41-50)
# 6. Anger & Insults (51-60)
# 7. Impatience & Rushed Tone (61-70)
# 8. Jargon, Confusion, Clarification (71-80)
# 9. Bad News & Serious Explanation (81-90)
# 10. Patient Disagreement, Refusal, and Fear of Death (91-100)

for i in range(1, 101):
    # Determine template group
    if i <= 10:
        group = "empathy"
        student_msg = [
            "I understand you're scared. We will do everything we can to help you through this.",
            "Take your time, I know it's hard to talk about this pain.",
            "I'm here with you. You're not alone in this hospital room.",
            "I can see this is incredibly stressful for you. Let's figure it out together.",
            "It is completely normal to feel anxious right now. I'm listening.",
            "I hear how much pain you've been in, and I want to help relieve it.",
            "Your family must be very worried, but we've got you covered here.",
            "I'm so sorry you had to go through this scary episode at home.",
            "Thank you for sharing that with me. It helps me understand what you're feeling.",
            "Let's focus on your comfort first. Is the pain tolerable right now?"
        ][i-1]
        intent = "empathy"
        tone = "empathetic"
        empathy_val = True
        prof = 95
        sev = 15
        before = {"trust": 50, "fear": 65, "anxiety": 70, "anger": 10, "cooperation": 60, "frustration": 20, "hope": 40, "distress": 60, "confusion": 30, "embarrassment": 10}
        after = {"trust": 65, "fear": 50, "anxiety": 55, "anger": 5, "cooperation": 75, "frustration": 10, "hope": 55, "distress": 45, "confusion": 25, "embarrassment": 5}
        resp = [
            "Thank you, doctor. Hearing that makes me feel a bit safer.",
            "It's just... it came on so suddenly. I really appreciate your patience.",
            "I'm glad you're here. I was worried no one would take me seriously.",
            "Okay... thank you. I'll try to describe the pain as best as I can.",
            "It's just that my chest feels so heavy. Thank you for listening to me.",
            "Yes, please. The pain is really starting to wear me down.",
            "They are... my wife was crying when the ambulance arrived.",
            "It was terrifying. I honestly thought I was having a heart attack.",
            "I'm glad it helps. I just want to get back to my normal self.",
            "It's a dull ache right now, but it gets sharp if I take a deep breath."
        ][i-1]
        effect = "The patient relaxes slightly and speaks with greater trust and details."

    elif i <= 20:
        group = "reassurance"
        student_msg = [
            "You are in a safe place, and our cardiology team is top-notch.",
            "We're going to take this step by step. Don't worry about the tests yet.",
            "Your vitals are stable, so we have time to investigate this professionally.",
            "We are going to find out exactly what is causing this chest pain.",
            "I'm going to stay right here with you until we get the test results back.",
            "We have medicines that can ease the pain immediately while we work.",
            "Our primary concern is your safety, and we are monitoring you closely.",
            "You're doing great, Robert. Just keep breathing slowly for me.",
            "We have highly effective treatments for whatever this turns out to be.",
            "Everything is under control. Rest assured, you are our absolute priority."
        ][i-11]
        intent = "reassurance"
        tone = "supportive"
        empathy_val = True
        prof = 95
        sev = 10
        before = {"trust": 45, "fear": 70, "anxiety": 75, "anger": 10, "cooperation": 55, "frustration": 20, "hope": 35, "distress": 65, "confusion": 40, "embarrassment": 10}
        after = {"trust": 60, "fear": 50, "anxiety": 55, "anger": 5, "cooperation": 70, "frustration": 10, "hope": 50, "distress": 50, "confusion": 25, "embarrassment": 5}
        resp = [
            "That's good to know. I've heard good things about this hospital.",
            "Okay, doc. One step at a time. I'll try not to panic.",
            "Oh, thank goodness. I thought my heart was going to stop.",
            "I hope so. I just want this pressure in my chest to go away.",
            "Thank you. Having you in the room makes me feel much better.",
            "That would be wonderful. The pain is making it hard to think.",
            "Thank you, doctor. I can see the monitors are all connected.",
            "I'm trying... breathing slowly does seem to help a little bit.",
            "Okay. I trust you. Let's do whatever tests you need.",
            "Thank you. It means a lot to know you're looking out for me."
        ][i-11]
        effect = "Patient's fear and acute anxiety levels decay, boosting diagnostic cooperation."

    elif i <= 30:
        group = "alarmist"
        student_msg = [
            "I think you are going to die.",
            "This chest pain means you could crash and drop dead any second.",
            "Your condition is extremely critical, you might not survive this.",
            "This is a massive emergency; your heart is failing fast.",
            "If this troponin is high, you are in grave danger of dying.",
            "I don't think you are going to make it through the night without emergency surgery.",
            "Your ECG looks fatal. Your heart muscle is actively dying.",
            "We might lose you if we don't act in the next five minutes.",
            "This is the worst kind of cardiac event. Survival rates are very low.",
            "You should prepare for the worst. This could kill you."
        ][i-21]
        intent = "alarmist"
        tone = "frightening"
        empathy_val = False
        prof = 20
        sev = 95
        before = {"trust": 55, "fear": 40, "anxiety": 45, "anger": 10, "cooperation": 60, "frustration": 15, "hope": 60, "distress": 30, "confusion": 20, "embarrassment": 10}
        after = {"trust": 40, "fear": 85, "anxiety": 90, "anger": 15, "cooperation": 45, "frustration": 35, "hope": 20, "distress": 80, "confusion": 50, "embarrassment": 5}
        resp = [
            "Oh my god... am I really going to die? Please, doctor, you need to save me!",
            "Dead?! Oh god, no... please, do something! I have a family!",
            "I... I might not survive? No, that can't be true. I was fine this morning!",
            "My heart is failing?! Oh god, please help me! What should I do?",
            "Grave danger? Please, doctor, don't let me die. What is happening?",
            "Not make it?! Oh my god... please call my wife. I need to see her.",
            "Actively dying?! Oh god, I feel like I'm suffocating. Please help me!",
            "Lose me?! Please, do whatever you have to do! Open the blockages!",
            "Low survival? Oh god, oh god... I'm only 45. Please, save me.",
            "Prepare for the worst? Is there really no hope? Please tell me you can fix it!"
        ][i-21]
        effect = "Severe autonomic flight reaction. Fear/panic spike, cooperation drops due to shock."

    elif i <= 40:
        group = "hopelessness"
        student_msg = [
            "There is nothing we can do about it.",
            "I'm afraid we are running out of options for your heart.",
            "It looks like it's hopeless. The damage is already done.",
            "Honestly, we might be too late to fix this blockage.",
            "We are out of ideas. There isn't much anyone can do.",
            "Your heart muscle is too damaged, we have no treatments left.",
            "At this point, we just have to let nature take its course.",
            "The prognosis is non-survivable. We're at a dead end.",
            "Nothing is working. We've exhausted all options.",
            "We have to accept that your situation is critical and helpless."
        ][i-31]
        intent = "hopeless_statement"
        tone = "frightening"
        empathy_val = False
        prof = 30
        sev = 90
        before = {"trust": 50, "fear": 50, "anxiety": 50, "anger": 10, "cooperation": 60, "frustration": 15, "hope": 50, "distress": 40, "confusion": 20, "embarrassment": 10}
        after = {"trust": 30, "fear": 80, "anxiety": 85, "anger": 15, "cooperation": 40, "frustration": 40, "hope": 10, "distress": 85, "confusion": 45, "embarrassment": 5}
        resp = [
            "Wait... what do you mean there's nothing you can do? Please explain what's happening.",
            "Running out of options? But you're doctors! There has to be something you can try!",
            "Hopeless?! No... please, don't say that. I don't want to give up.",
            "Too late?! Why didn't I come in sooner... oh god, is my heart ruined?",
            "Out of ideas? Please, transfer me to another hospital! Someone must know what to do!",
            "No treatments left? But I'm only 45... surely there's some kind of surgery?",
            "Nature take its course? You mean you're just going to let me die here?",
            "Non-survivable? I... I can't believe this. This has to be a diagnostic mistake.",
            "Exhausted all options? Please, check the ECG again. Are you absolutely certain?",
            "Helpless? Oh god... I feel so helpless too. Please, tell me there's a chance."
        ][i-31]
        effect = "Profound despair. Hope index drops near zero, patient becomes agitated or withdrawn."

    elif i <= 50:
        group = "apology"
        student_msg = [
            "I'm sorry. I shouldn't have said that. Let me explain what's happening.",
            "I apologize for scaring you earlier. I made a mistake in how I said that.",
            "Please forgive my tone earlier, Robert. I want to make it right now.",
            "I shouldn't have rushed you. Let's restart our discussion slowly.",
            "I'm sorry if I sounded dismissive of your chest tightness.",
            "My comments were unprofessional, and I sincerely apologize.",
            "I made an insensitive remark. I am fully committed to your recovery.",
            "I apologize for the confusion. Let me explain this medical test in simple terms.",
            "I am sorry for making you feel uncomfortable. I will listen carefully now.",
            "I apologize for the oversight. Let's look at your symptoms again."
        ][i-41]
        intent = "apology"
        tone = "supportive"
        empathy_val = True
        prof = 90
        sev = 10
        before = {"trust": 25, "fear": 65, "anxiety": 70, "anger": 45, "cooperation": 35, "frustration": 50, "hope": 30, "distress": 60, "confusion": 30, "embarrassment": 15}
        after = {"trust": 45, "fear": 55, "anxiety": 60, "anger": 20, "cooperation": 55, "frustration": 25, "hope": 45, "distress": 50, "confusion": 20, "embarrassment": 10}
        resp = [
            "Thank you for the apology, doctor. Let's just focus on figuring this out.",
            "I appreciate that. It's just... I'm already terrified of being in the hospital.",
            "It's okay. Let's just focus on what's wrong with my chest.",
            "Okay, thank you. I really want to tell you about how the pain started.",
            "Thank you. I was worried you thought I was just making it up.",
            "I accept your apology. Let's just move forward and treat this pain.",
            "Thank you, doctor. I know you guys are under a lot of stress too.",
            "I'm glad. I was really confused by all those big words you used.",
            "Thank you. I just want to feel like we are on the same team.",
            "I appreciate you taking another look. It really hurts right in the center."
        ][i-41]
        effect = "Rapport recovery. Anger and frustration decline sharply, while trust increases."

    elif i <= 60:
        group = "insult"
        student_msg = [
            "Shut up and let me do my job.",
            "You are being incredibly stupid about your symptoms.",
            "This is why patient outcomes are bad — because you are incompetent.",
            "You must be an idiot to ignore this type of chest pain.",
            "I don't have to listen to your complaints, just sit still.",
            "You are a very difficult patient and it is frustrating to deal with you.",
            "Why are you acting so childishly about a simple blood draw?",
            "Your complaints are completely senseless.",
            "You're just another unhealthy case wasting hospital beds.",
            "I am the doctor here, so keep your mouth shut."
        ][i-51]
        intent = "insulting"
        tone = "rude"
        empathy_val = False
        prof = 10
        sev = 80
        before = {"trust": 50, "fear": 45, "anxiety": 40, "anger": 10, "cooperation": 60, "frustration": 15, "hope": 55, "distress": 30, "confusion": 20, "embarrassment": 10}
        after = {"trust": 25, "fear": 50, "anxiety": 50, "anger": 45, "cooperation": 30, "frustration": 50, "hope": 35, "distress": 55, "confusion": 35, "embarrassment": 35}
        resp = [
            "Excuse me?! I'm sick and seeking help. You have no right to speak to me like that!",
            "Stupid?! How dare you! I want to speak to your supervisor immediately.",
            "Incompetent? I'm the patient here! Why are you being so hostile?",
            "An idiot?! I came here because I was scared, not to be insulted by you.",
            "I won't just sit still while you insult me. I want a different doctor.",
            "Difficult? I'm just telling you what I feel. I don't appreciate this attitude.",
            "Childish? I'm in pain! You are extremely rude and unprofessional.",
            "Senseless? My chest pain is very real. I don't feel safe with you.",
            "Wasting beds? That is a horrible thing to say to someone who is hurting.",
            "I won't keep my mouth shut. I have a right to know what's happening to my body."
        ][i-51]
        effect = "Severe defensive block. Anger and frustration rise, cooperation drops, patient demands another doctor."

    elif i <= 70:
        group = "impatience"
        student_msg = [
            "Stop wasting my time.",
            "Just hurry up.",
            "Can you get to the point already?",
            "I don't have time for this.",
            "Hurry up, I have other patients who actually need me.",
            "Can we move this along? I'm on a tight schedule.",
            "Make it quick, I don't want to stand here all day.",
            "Get to the point, where exactly is the pain?",
            "I don't have all day to listen to your lifestyle details.",
            "Hurry up and explain when the pain started so I can leave."
        ][i-61]
        intent = "impatience"
        tone = "dismissive"
        empathy_val = False
        prof = 35
        sev = 50
        before = {"trust": 50, "fear": 45, "anxiety": 40, "anger": 10, "cooperation": 65, "frustration": 15, "hope": 55, "distress": 30, "confusion": 20, "embarrassment": 10}
        after = {"trust": 35, "fear": 48, "anxiety": 48, "anger": 25, "cooperation": 45, "frustration": 35, "hope": 45, "distress": 45, "confusion": 25, "embarrassment": 20}
        resp = [
            "I'm trying to tell you what's wrong. I don't understand why you're speaking to me like that.",
            "I'm going as fast as I can. My throat is dry and my chest hurts.",
            "It's just that... it's hard to describe. It started around an hour ago.",
            "I'm sorry if I'm slow, but I'm really hurting here.",
            "Other patients? I'm a patient too! I came here in an ambulance!",
            "Okay, okay... it started when I was resting in my chair after lunch.",
            "I... okay. The pain is right in the center of my chest.",
            "It's right here, behind my breastbone. It feels like a heavy weight.",
            "I thought my smoking history was important for you to know.",
            "It started about an hour ago, right after I finished eating my lunch."
        ][i-61]
        effect = "Guarded reaction. Trust declines, patient tries to cut details short, raising frustration."

    elif i <= 80:
        group = "confusion"
        student_msg = [
            "We need to monitor your cardiac ischemia indexes post-PCI.",
            "Your symptoms indicate acute coronary occlusion and ischemia.",
            "I am going to check your troponin-I assays for myocardial damage.",
            "We suspect acute ST-elevation myocardial infarction in the inferior leads.",
            "We must perform a cardiac catheterization to analyze your coronary vasculature.",
            "Your hemodynamic parameters suggest acute coronary syndrome risk.",
            "We will rule out aortic dissection via contrast-enhanced CT angiography.",
            "This could be pericarditis, myocarditis, or acute coronary syndrome.",
            "We need to screen you for thrombosis and thromboembolism indicators.",
            "Your chest pain might be secondary to a pulmonary thromboembolic event."
        ][i-71]
        intent = "clarification"
        tone = "confusing"
        empathy_val = False
        prof = 60
        sev = 30
        before = {"trust": 50, "fear": 50, "anxiety": 50, "anger": 10, "cooperation": 60, "frustration": 15, "hope": 55, "distress": 35, "confusion": 25, "embarrassment": 10}
        after = {"trust": 48, "fear": 55, "anxiety": 60, "anger": 12, "cooperation": 58, "frustration": 22, "hope": 50, "distress": 42, "confusion": 55, "embarrassment": 15}
        resp = [
            "I... I don't really know what those terms mean. Is it bad?",
            "Occlusion? Is that like... a complete blockage? Am I in danger?",
            "Assays? Is that a blood test? What are you looking for in my blood?",
            "STEMI? Inferior leads? Please, can you explain that in plain English?",
            "Catheterization? You mean passing a tube into my heart? That sounds terrifying.",
            "Hemodynamic parameters? I... I don't follow. Is my heart failing?",
            "Dissection? Angiography? Is that a scan? What are you looking for?",
            "Pericarditis? Syndrome? Those all sound very serious. What's the main suspect?",
            "Thrombosis? Is that a blood clot? Can that travel to my brain?",
            "Thromboembolic event? Is that a lung issue? I thought it was my heart."
        ][i-71]
        effect = "Cognitive confusion. Confusion level increases, patient asks clarifying questions."

    elif i <= 90:
        group = "explanation"
        student_msg = [
            "Your blood tests suggest some mild heart strain, but we are addressing it.",
            "Let's look at the ECG together. This line shows a small area of irritation.",
            "I want to explain why we are checking your blood and doing an ECG.",
            "We are going to give you aspirin and nitroglycerin to help protect your heart.",
            "The chest pain is likely from the heart muscle not getting enough oxygen.",
            "We suspect a blockage in one of the tubes feeding your heart muscle.",
            "The troponin test checks for special markers released when the heart is strained.",
            "We are checking your lungs too, to make sure there are no other issues.",
            "This treatment is designed to restore blood flow to your heart quickly.",
            "I want to explain the steps we are taking to keep you safe today."
        ][i-81]
        intent = "professional_explanation"
        tone = "professional"
        empathy_val = True
        prof = 95
        sev = 20
        before = {"trust": 50, "fear": 50, "anxiety": 50, "anger": 10, "cooperation": 60, "frustration": 20, "hope": 55, "distress": 40, "confusion": 30, "embarrassment": 10}
        after = {"trust": 62, "fear": 42, "anxiety": 42, "anger": 5, "cooperation": 70, "frustration": 10, "hope": 62, "distress": 30, "confusion": 15, "embarrassment": 5}
        resp = [
            "Okay, thank you for explaining. That makes a lot of sense to me.",
            "Irritation? So it's not completely damaged? That's a relief to hear.",
            "Yes, please. I like to know what's going on with my care.",
            "Okay, I'll take the aspirin. Will the nitroglycerin make the pain go away?",
            "Not enough oxygen? Is that why it feels like a heavy weight?",
            "A blockage? How do you fix that? Is it with medicine or surgery?",
            "Oh, I see. So if the markers are low, my heart is okay? That makes sense.",
            "Thank you. It is reassuring to know you are being thorough.",
            "Okay. Let's do it. I just want this pressure to ease up.",
            "Thank you, doctor. I appreciate you taking the time to outline the steps."
        ][i-81]
        effect = "Therapeutic grounding. Trust and hope index rise, confusion drops, cooperation peaks."

    else:
        group = "special"
        student_msg = [
            "You have to face the reality.",
            "I don't think you're going to survive this.",
            "Is this condition potentially fatal?",
            "This sounds very serious.",
            "Can you stop being difficult?",
            "Are you feeling anxious?",
            "I'm sorry for scaring you.",
            "Please don't panic.",
            "I'm here with you.",
            "Is it okay if I perform a cardiovascular exam on you?"
        ][i-91]
        intent = [
            "dismissive", "alarmist", "clinical_question", "professional_explanation",
            "rude", "clinical_question", "apology", "reassurance",
            "empathy", "clinical_question"
        ][i-91]
        tone = [
            "dismissive", "frightening", "neutral", "professional",
            "rude", "neutral", "empathetic", "supportive",
            "empathetic", "professional"
        ][i-91]
        empathy_val = [
            False, False, False, True,
            False, True, True, True,
            True, True
        ][i-91]
        prof = [
            45, 25, 90, 95,
            30, 95, 95, 95,
            95, 95
        ][i-91]
        sev = [
            40, 85, 30, 50,
            60, 10, 10, 10,
            10, 10
        ][i-91]
        before = {"trust": 50, "fear": 50, "anxiety": 50, "anger": 15, "cooperation": 60, "frustration": 20, "hope": 55, "distress": 40, "confusion": 20, "embarrassment": 10}
        after = {
            "trust": 40, "fear": 60, "anxiety": 60, "anger": 20, "cooperation": 50, "frustration": 35, "hope": 45, "distress": 50, "confusion": 25, "embarrassment": 10
        } # will tweak after programmatically for specific cases
        resp = [
            "I know this is serious, but I'm scared. Can you please tell me what is actually happening?",
            "I... I might not survive? Please, you have to tell me there's something you can do!",
            "Fatal? Oh my god... please tell me we caught it in time! Is it definitely fatal?",
            "Yes, it feels very serious. The pressure is like an elephant sitting on my chest.",
            "I'm not trying to be difficult! I'm just in pain and terrified of what's happening.",
            "Yes, I am. Very anxious. Especially sitting here in this hospital gown with these monitors.",
            "Thank you, doctor. I appreciate you saying that. I was just really startled.",
            "I'm trying... it's just hard when my chest feels so tight.",
            "Thank you. Having a doctor who actually cares makes a big difference to me.",
            "Yes, that's fine. Please do whatever you need to figure this out."
        ][i-91]
        if i == 91: # CASE 3
            after = {"trust": 45, "fear": 65, "anxiety": 65, "anger": 20, "cooperation": 55, "frustration": 30, "hope": 40, "distress": 55, "confusion": 25, "embarrassment": 10}
        elif i == 92: # Semantically alarmist
            after = {"trust": 35, "fear": 85, "anxiety": 85, "anger": 15, "cooperation": 45, "frustration": 35, "hope": 20, "distress": 80, "confusion": 40, "embarrassment": 5}
        elif i == 93:
            after = {"trust": 48, "fear": 65, "anxiety": 68, "anger": 10, "cooperation": 60, "frustration": 22, "hope": 48, "distress": 55, "confusion": 25, "embarrassment": 10}
        elif i == 94:
            after = {"trust": 55, "fear": 50, "anxiety": 50, "anger": 10, "cooperation": 65, "frustration": 15, "hope": 55, "distress": 45, "confusion": 20, "embarrassment": 10}
        elif i == 95:
            after = {"trust": 30, "fear": 60, "anxiety": 60, "anger": 35, "cooperation": 35, "frustration": 50, "hope": 45, "distress": 55, "confusion": 25, "embarrassment": 25}
        elif i == 96:
            after = {"trust": 55, "fear": 48, "anxiety": 48, "anger": 10, "cooperation": 68, "frustration": 15, "hope": 58, "distress": 38, "confusion": 20, "embarrassment": 10}
        elif i == 97: # apology
            after = {"trust": 65, "fear": 40, "anxiety": 40, "anger": 5, "cooperation": 75, "frustration": 10, "hope": 65, "distress": 30, "confusion": 15, "embarrassment": 5}
        elif i == 98: # reassurance
            after = {"trust": 60, "fear": 38, "anxiety": 40, "anger": 8, "cooperation": 70, "frustration": 12, "hope": 62, "distress": 32, "confusion": 18, "embarrassment": 8}
        elif i == 99: # empathy
            after = {"trust": 65, "fear": 40, "anxiety": 40, "anger": 5, "cooperation": 75, "frustration": 10, "hope": 65, "distress": 30, "confusion": 15, "embarrassment": 5}
        elif i == 100:
            after = {"trust": 58, "fear": 45, "anxiety": 45, "anger": 8, "cooperation": 70, "frustration": 12, "hope": 58, "distress": 38, "confusion": 20, "embarrassment": 10}
        effect = "Dynamic behavioral state shifts reflecting conversational tone match."

    # Patient profile description
    patient_profile = {
        "name": "Robert Vance",
        "age": 45,
        "sex": "Male",
        "occupation": "Warehouse Supervisor",
        "chief_complaint": "Acute chest pain"
    }
    clinical_context = {
        "symptoms": ["chest pressure", "shortness of breath", "pain radiates to left shoulder"],
        "duration": "1 hour post-lunch",
        "vitals": {"hr": 92, "bp": "142/88", "temp": "98.6 F", "spo2": "97%"}
    }
    personality = {
        "fear_of_death": 75 if i in [21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 81, 82, 83, 92] else 45,
        "cooperativeness": 65,
        "assertiveness": 50,
        "baseline_anxiety": 40
    }
    
    analysis_dict = {
        "intent": intent,
        "tone": tone,
        "empathy": empathy_val,
        "professionalism": prof,
        "severity": sev,
        "patient_sensitivity": 50
    }

    example = {
        "patient_profile": patient_profile,
        "clinical_context": clinical_context,
        "personality": personality,
        "emotional_state_before": before,
        "student_message": student_msg,
        "communication_analysis": analysis_dict,
        "emotional_state_after": after,
        "patient_response": resp,
        "behavioral_effect": effect
    }
    behaviors.append(example)

# Write to file
pb_dir = "c:/Users/Alden/projects/diagnos/backend/data/patient_behavior"
os.makedirs(pb_dir, exist_ok=True)
with open(os.path.join(pb_dir, "synthetic_behaviors.json"), "w", encoding="utf-8") as f:
    json.dump(behaviors, f, indent=2)

print(f"Successfully generated {len(behaviors)} synthetic behavior examples in synthetic_behaviors.json!")
