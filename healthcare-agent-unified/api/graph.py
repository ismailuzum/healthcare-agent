"""
Unified Healthcare Agent Pipeline
Combines Basic (Generator/Critic), Intermediate (Multi-Specialist),
and Advanced (Extraction, Coding, SOAP/Human Review) agents.
All prompts are multi-language: respond in the same language as the input.
"""
from typing import TypedDict, Annotated, List, Literal
from langgraph.graph import StateGraph, END
import operator
from litellm import completion
import json
from specialists import SPECIALISTS
from utils import clean_llm_json, extract_json_from_text


# ============================================================
# STEP 1: Generator/Critic State & Nodes (from Basic project)
# ============================================================

class AnalyzeState(TypedDict):
    patient_input: str
    draft: str
    feedback: str
    is_approved: bool
    iteration: int
    messages: Annotated[list[str], operator.add]


def generator_node(state: AnalyzeState) -> dict:
    """Generate a professional medical symptom summary (NO diagnosis)"""
    prompt = f"""You are a medical assistant. Convert the patient's symptoms into a professional clinical summary.

RULES:
- NEVER make a diagnosis (words like migraine, COVID, flu, diabetes, cancer, stroke, etc. are FORBIDDEN)
- Only list and describe the symptoms professionally
- Recommend "Doctor consultation is advised" in English.

CRITICAL INSTRUCTION: You MUST write your entire response in English.

Patient Input: {state['patient_input']}
"""
    if state.get('feedback'):
        prompt += f"\n\nPrevious error: {state['feedback']}\nFix and rewrite."

    response = completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    draft = response.choices[0].message.content

    return {
        "draft": draft,
        "iteration": state.get("iteration", 0) + 1,
        "messages": [f"[GENERATOR] Iteration {state.get('iteration', 0) + 1}: Draft created"]
    }


def critic_node(state: AnalyzeState) -> dict:
    """Check the draft for diagnosis words and professionalism"""
    draft = state['draft']

    # Forbidden diagnosis words (multi-language)
    forbidden_words = [
        'migraine', 'migren', 'covid', 'flu', 'grip', 'influenza',
        'diabetes', 'diyabet', 'cancer', 'kanser', 'stroke', 'inme',
        'heart attack', 'kalp krizi', 'pneumonia', 'zatürre',
        'asthma', 'astım', 'bronchitis', 'bronşit',
        'diagnosed with', 'tanı', 'teşhis'
    ]

    has_diagnosis = any(word in draft.lower() for word in forbidden_words)

    if has_diagnosis:
        return {
            "is_approved": False,
            "feedback": "ERROR: Diagnosis word detected! Only list symptoms, never diagnose.",
            "messages": ["[CRITIC] ❌ REJECTED - Diagnosis detected"]
        }

    # Professionalism check via LLM
    prompt = f"""Is this text a professional medical summary? Answer only 'yes' or 'no'.

Text: {draft}

Answer:"""

    response = completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )

    is_professional = "yes" in response.choices[0].message.content.lower()

    if not is_professional:
        return {
            "is_approved": False,
            "feedback": "Not professional enough. Rewrite more formally.",
            "messages": ["[CRITIC] ❌ REJECTED - Not professional"]
        }

    return {
        "is_approved": True,
        "feedback": "",
        "messages": ["[CRITIC] ✅ APPROVED"]
    }


def should_continue_analyze(state: AnalyzeState) -> Literal["generator", "__end__"]:
    if state["is_approved"]:
        return "__end__"
    if state.get("iteration", 0) >= 5:
        return "__end__"
    return "generator"


def create_analyze_graph():
    """Create the Generator/Critic analysis pipeline"""
    workflow = StateGraph(AnalyzeState)

    workflow.add_node("generator", generator_node)
    workflow.add_node("critic", critic_node)

    workflow.set_entry_point("generator")
    workflow.add_edge("generator", "critic")
    workflow.add_conditional_edges(
        "critic",
        should_continue_analyze,
        {
            "generator": "generator",
            "__end__": END
        }
    )

    return workflow.compile()


# ============================================================
# STEP 2: Supervisor (Specialist Recommender)
# ============================================================

def recommend_specialists(case: str, top_k: int = 3) -> dict:
    """Supervisor agent: recommends which specialists should evaluate the case"""
    specialist_list = "\n".join([
        f"- {key}: {val['name']} - {val['description']}"
        for key, val in SPECIALISTS.items()
    ])

    prompt = f"""You are an experienced CHIEF PHYSICIAN. Analyze the patient case and select the {top_k} most appropriate specialists.

📋 PATIENT CASE:
{case}

👥 AVAILABLE SPECIALISTS (20 Total):
{specialist_list}

🎯 SELECTION CRITERIA:
1. PRIORITY ORDER:
   - Life-threatening (chest pain, breathing difficulty, loss of consciousness) → Emergency Medicine + relevant organ specialist
   - Chronic disease management → Relevant specialist + General Practitioner
   - Unclear/complex symptoms → General Practitioner MUST be included

2. SYMPTOM-SPECIALIST MATCHING:
   - Chest/heart issues → Cardiologist
   - Head/nerve/stroke → Neurologist
   - Respiratory/cough/breathing → Pulmonologist
   - Joint/muscle/bone → Rheumatologist or Orthopedist
   - Skin/rash/itching → Dermatologist
   - Abdominal/digestive → Gastroenterologist
   - Hormonal/diabetes/thyroid → Endocrinologist
   - Kidney/urinary → Nephrologist or Urologist
   - Eye problems → Ophthalmologist
   - Ear/nose/throat → ENT
   - Women's health → Gynecologist
   - Mental/psychological → Psychiatrist
   - Allergies/asthma → Allergist
   - Infection/fever → Infectious Disease
   - Blood/anemia → Hematologist
   - Cancer suspicion → Oncologist

3. EMERGENCY FLAGS:
   - "Chest pain", "can't breathe", "severe headache", "loss of consciousness" → Emergency Medicine MANDATORY

CRITICAL INSTRUCTION: You MUST write your `reasoning` in English.

📤 OUTPUT FORMAT (JSON only):
{{
  "selected_specialists": ["key1", "key2", "key3"],
  "reasoning": "Brief explanation in English"
}}
"""

    try:
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = clean_llm_json(response.choices[0].message.content)
        result = json.loads(content)
        selected = result.get("selected_specialists", [])[:top_k]
        reasoning = result.get("reasoning", "")
    except Exception as e:
        print(f"❌ Supervisor parse error: {e}")
        selected = list(SPECIALISTS.keys())[:top_k]
        reasoning = "Could not parse model response, default specialists selected."

    # Pad if not enough
    if len(selected) < top_k:
        all_keys = list(SPECIALISTS.keys())
        for key in all_keys:
            if key not in selected:
                selected.append(key)
                if len(selected) == top_k:
                    break

    return {
        "selected_specialists": selected,
        "reasoning": reasoning
    }


# ===================================
# STEP 3: Consultation State & Nodes 
# ===================================

class ConsultState(TypedDict):
    case: str
    selected_specialists: List[str]
    assessments: Annotated[List[dict], operator.add]
    aggregated_summary: str
    conditions: List[str]
    medications: List[dict]
    condition_codes: List[dict]
    medication_codes: List[dict]
    soap_note: str


def analyze_specialists_node(state: ConsultState) -> dict:
    """Each selected specialist analyzes the case"""
    selected = state["selected_specialists"]
    case = state["case"]
    assessments = []

    for key in selected:
        specialist = SPECIALISTS.get(key)
        if not specialist:
            continue

        prompt = f"""You are a {specialist['name']}. ({specialist['description']})

CASE: {case}

Analyze the case from your specialty's perspective (max 150 words). Address:
1. Relevant findings from your specialty
2. Required tests/examinations
3. Treatment recommendations

CRITICAL INSTRUCTION: You MUST write your ENTIRE assessment in English. Your response must only be the assessment.
"""
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        assessments.append({
            "specialist": specialist['name'],
            "key": key,
            "icon": specialist.get('icon', '🩺'),
            "assessment": response.choices[0].message.content
        })

    return {"assessments": assessments}


def aggregator_node(state: ConsultState) -> dict:
    """Synthesize specialist assessments into unified summary"""
    assessments = state["assessments"]

    all_assessments = "\n\n".join([
        f"**{a['specialist']}:**\n{a['assessment']}"
        for a in assessments
    ])

    prompt = f"""Synthesize the following specialist assessments:

{all_assessments}

Provide a unified summary addressing:
1. Consensus / Unified view
2. Diverging opinions / Conflicts (if any)
3. Recommended action plan

Keep it under 200 words.

CRITICAL INSTRUCTION: You MUST write your ENTIRE summary in English. Your response must only be the summary.
"""

    response = completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return {"aggregated_summary": response.choices[0].message.content}


# ── Extraction Nodes (from Advanced project) ──────────────────

def condition_extractor_node(state: ConsultState) -> dict:
    """Extract medical conditions explicitly mentioned by the patient from the case"""
    case = state["case"]

    prompt = f"""Extract all medical conditions explicitly mentioned by the patient in this clinical data.

PATIENT CASE:
{case}

CRITICAL RULES:
1. ONLY extract conditions/diseases that the patient explicitly stated they already have or complain about.
2. DO NOT infer, guess, or create any new diagnoses. You are NOT allowed to diagnose.
3. If the patient does not explicitly mention a named medical condition, return an empty array [].

Return ONLY a JSON array of condition names (strings). No markdown, no explanation.
Example: ["hypertension", "diabetes mellitus type 2", "asthma"]
"""

    try:
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        conditions = extract_json_from_text(content)
        if not conditions or not isinstance(conditions, list):
            conditions = []
        print(f"✅ Extracted {len(conditions)} conditions: {conditions}")
    except Exception as e:
        print(f"❌ Condition extraction error: {e}")
        conditions = []

    return {"conditions": conditions}


def medication_extractor_node(state: ConsultState) -> dict:
    """Extract medications with dosage and route"""
    case = state["case"]
    assessments = state.get("assessments", [])

    assessments_text = "\n".join([
        f"- {a['specialist']}: {a['assessment'][:300]}"
        for a in assessments
    ])

    prompt = f"""Extract all medications mentioned or recommended in this clinical data.

PATIENT CASE:
{case}

SPECIALIST ASSESSMENTS:
{assessments_text}

For each medication, extract:
- drug: medication name
- dosage: dose amount (e.g., "500mg", "10mg") or "as prescribed"
- route: administration route (e.g., "oral", "IV", "topical") or "N/A"

Return ONLY a JSON array. No markdown:
[
  {{"drug": "metformin", "dosage": "500mg", "route": "oral"}},
  {{"drug": "lisinopril", "dosage": "10mg", "route": "oral"}}
]

If no medications found, return an empty array: []
"""

    try:
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        medications = extract_json_from_text(content)
        if not medications or not isinstance(medications, list):
            medications = []
        print(f"✅ Extracted {len(medications)} medications: {medications}")
    except Exception as e:
        print(f"❌ Medication extraction error: {e}")
        medications = []

    return {"medications": medications}


def condition_coder_node(state: ConsultState) -> dict:
    """Assign ICD-10-CM codes to conditions"""
    conditions = state.get('conditions', [])
    if not conditions:
        return {"condition_codes": []}

    conditions_text = "\n".join([f"- {c}" for c in conditions])

    prompt = f"""Assign ICD-10-CM codes to these medical conditions.

CONDITIONS:
{conditions_text}

For each condition, return:
- chunk: the condition text
- entity_type: "condition"
- code: ICD-10-CM code (e.g., "I10" for hypertension)

Return ONLY a JSON array. No markdown:
[
  {{"chunk": "hypertension", "entity_type": "condition", "code": "I10"}},
  {{"chunk": "diabetes mellitus type 2", "entity_type": "condition", "code": "E11.9"}}
]

If you don't know exact code, use closest match or "UNKNOWN".
"""

    try:
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        codes = extract_json_from_text(content)
        if not codes or not isinstance(codes, list):
            codes = []
        print(f"✅ Coded {len(codes)} conditions")
    except Exception as e:
        print(f"❌ Condition coding error: {e}")
        codes = []

    return {"condition_codes": codes}


def medication_coder_node(state: ConsultState) -> dict:
    """Assign ATC codes to medications"""
    medications = state.get('medications', [])
    if not medications:
        return {"medication_codes": []}

    meds_text = "\n".join([
        f"- {m.get('drug', 'unknown')} {m.get('dosage', '')} {m.get('route', '')}"
        for m in medications
    ])

    prompt = f"""Assign ATC codes (WHO standard) to these medications.

MEDICATIONS:
{meds_text}

For each medication, return:
- chunk: "drug dosage route"
- entity_type: "medication"
- code: ATC code (e.g., "A10BA02" for metformin)

Return ONLY a JSON array. No markdown:
[
  {{"chunk": "metformin 500mg oral", "entity_type": "medication", "code": "A10BA02"}},
  {{"chunk": "lisinopril 10mg oral", "entity_type": "medication", "code": "C09AA03"}}
]

If you don't know exact code, use "UNKNOWN".
"""

    try:
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        codes = extract_json_from_text(content)
        if not codes or not isinstance(codes, list):
            codes = []
        print(f"✅ Coded {len(codes)} medications")
    except Exception as e:
        print(f"❌ Medication coding error: {e}")
        codes = []

    return {"medication_codes": codes}


# ── SOAP Note Drafter ─────────────────────────────────────────

def soap_drafter_node(state: ConsultState) -> dict:
    """Generate a clinical note from all gathered data (no S/O/A/P labels en *** )"""
    case = state["case"]
    assessments = state.get("assessments", [])
    summary = state.get("aggregated_summary", "")
    conditions = state.get("conditions", [])
    medications = state.get("medications", [])
    condition_codes = state.get("condition_codes", [])
    medication_codes = state.get("medication_codes", [])

    assessments_text = "\n".join([
        f"- {a['specialist']}: {a['assessment'][:200]}"
        for a in assessments
    ])

    conditions_text = ", ".join(conditions) if conditions else "None documented"

    codes_text = ""
    if condition_codes:
        codes_text += "ICD-10 Codes:\n" + "\n".join([
            f"  - {c.get('chunk', '')}: {c.get('code', 'N/A')}"
            for c in condition_codes
        ])
    if medication_codes:
        codes_text += "\nATC Codes:\n" + "\n".join([
            f"  - {c.get('chunk', '')}: {c.get('code', 'N/A')}"
            for c in medication_codes
        ])

    meds_text = ", ".join([
        f"{m.get('drug', 'unknown')} {m.get('dosage', '')}"
        for m in medications
    ]) if medications else "None documented"

    prompt = f"""Create a professional clinical note from this consultation data.

ORIGINAL CASE:
{case}

SPECIALIST ASSESSMENTS:
{assessments_text}

AGGREGATED SUMMARY:
{summary}

IDENTIFIED CONDITIONS: {conditions_text}
IDENTIFIED MEDICATIONS: {meds_text}

MEDICAL CODES:
{codes_text}

INSTRUCTIONS:
- Write a flowing, professional clinical narrative
- Do NOT use section labels like "S:", "O:", "A:", "P:" or "Subjective:", "Objective:", etc.
- Instead, organize the content naturally with descriptive paragraph headers such as:
  "Chief Complaint & History", "Clinical Findings", "Assessment & Diagnosis", "Treatment Plan & Recommendations"
- Include the ICD-10 and ATC codes inline where relevant (e.g., "Hypertension (ICD-10: I10)")
- Keep it professional, concise, and clinically appropriate

CRITICAL INSTRUCTION: Write the ENTIRE clinical note in English.
"""

    try:
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        soap_note = response.choices[0].message.content
    except Exception as e:
        print(f"❌ SOAP drafting error: {e}")
        soap_note = "Error generating clinical note."

    return {"soap_note": soap_note}


# ── Graph Factory ─────────────────────────────────────────────

def create_consult_graph():
    """
    Create the full Consultation pipeline:
    Specialists → Aggregator → Condition Extractor → Medication Extractor
    → Condition Coder → Medication Coder → SOAP Drafter
    """
    workflow = StateGraph(ConsultState)

    workflow.add_node("analyze_specialists", analyze_specialists_node)
    workflow.add_node("aggregator", aggregator_node)
    workflow.add_node("condition_extractor", condition_extractor_node)
    workflow.add_node("medication_extractor", medication_extractor_node)
    workflow.add_node("condition_coder", condition_coder_node)
    workflow.add_node("medication_coder", medication_coder_node)
    workflow.add_node("soap_drafter", soap_drafter_node)

    workflow.set_entry_point("analyze_specialists")
    workflow.add_edge("analyze_specialists", "aggregator")
    workflow.add_edge("aggregator", "condition_extractor")
    workflow.add_edge("condition_extractor", "medication_extractor")
    workflow.add_edge("medication_extractor", "condition_coder")
    workflow.add_edge("condition_coder", "medication_coder")
    workflow.add_edge("medication_coder", "soap_drafter")
    workflow.add_edge("soap_drafter", END)

    return workflow.compile()
