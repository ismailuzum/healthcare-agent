from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import operator
from litellm import completion
import json
import re

# State Definition
class AgentState(TypedDict):
    document_text: str
    conditions: List[str]
    medications: Annotated[List[dict], operator.add]
    condition_codes: Annotated[List[dict], operator.add]
    medication_codes: Annotated[List[dict], operator.add]
    soap_note: str
    final_note: str

def extract_json_from_text(text: str):
    """Extract JSON from text that might have markdown or extra content"""
    # Try to find JSON in the text
    json_match = re.search(r'\[.*\]', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    
    # Try direct parse
    try:
        return json.loads(text)
    except:
        return None

# Node 1: Extract Conditions
def condition_extractor(state: AgentState) -> dict:
    """Extract medical conditions from document"""
    text = state['document_text']
    
    prompt = f"""Extract all medical conditions/diagnoses from this clinical document.

DOCUMENT:
{text}

Return ONLY a JSON array of condition names (strings). No markdown, no explanation.
["condition1", "condition2", "condition3"]

Example: ["hypertension", "diabetes mellitus type 2", "asthma"]
"""
    
    try:
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        
        content = response.choices[0].message.content.strip()
        print(f"Condition extractor raw response: {content}")
        
        # Try to extract JSON
        conditions = extract_json_from_text(content)
        
        if not conditions or not isinstance(conditions, list):
            print(f"⚠️ Failed to parse conditions, using fallback")
            conditions = []
        
        print(f"✅ Extracted {len(conditions)} conditions: {conditions}")
        
    except Exception as e:
        print(f"❌ Condition extraction error: {e}")
        conditions = []
    
    return {"conditions": conditions}

# Node 2: Extract Medications
def medication_extractor(state: AgentState) -> dict:
    """Extract medications with dosage and route"""
    text = state['document_text']
    
    prompt = f"""Extract all medications from this clinical document.

DOCUMENT:
{text}

For each medication, extract ONLY:
- drug: medication name
- dosage: dose amount (e.g., "500mg", "10mg")
- route: administration route (e.g., "oral", "IV")

DO NOT include frequency, duration, or instructions.

Return ONLY a JSON array. No markdown, no explanation:
[
  {{"drug": "metformin", "dosage": "500mg", "route": "oral"}},
  {{"drug": "lisinopril", "dosage": "10mg", "route": "oral"}}
]
"""
    
    try:
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        
        content = response.choices[0].message.content.strip()
        print(f"Medication extractor raw response: {content}")
        
        # Try to extract JSON
        medications = extract_json_from_text(content)
        
        if not medications or not isinstance(medications, list):
            print(f"⚠️ Failed to parse medications, using fallback")
            medications = []
        
        print(f"✅ Extracted {len(medications)} medications: {medications}")
        
    except Exception as e:
        print(f"❌ Medication extraction error: {e}")
        medications = []
    
    return {"medications": medications}

# Node 3: Code Conditions (ICD-10)
def condition_coder(state: AgentState) -> dict:
    """Assign ICD-10-CM codes to conditions"""
    conditions = state.get('conditions', [])
    
    if not conditions:
        print("⚠️ No conditions to code")
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
        print(f"Condition coder raw response: {content}")
        
        codes = extract_json_from_text(content)
        
        if not codes or not isinstance(codes, list):
            print(f"⚠️ Failed to parse condition codes")
            codes = []
        
        print(f"✅ Coded {len(codes)} conditions")
        
    except Exception as e:
        print(f"❌ Condition coding error: {e}")
        codes = []
    
    return {"condition_codes": codes}

# Node 4: Code Medications (RxNorm)
def medication_coder(state: AgentState) -> dict:
    """Assign RxNorm codes to medications"""
    medications = state.get('medications', [])
    
    if not medications:
        print("⚠️ No medications to code")
        return {"medication_codes": []}
    
    meds_text = "\n".join([
        f"- {m.get('drug', 'unknown')} {m.get('dosage', '')} {m.get('route', '')}" 
        for m in medications
    ])
    
    prompt = f"""Assign RxNorm (RxCUI) codes to these medications.

MEDICATIONS:
{meds_text}

For each medication, return:
- chunk: "drug dosage route"
- entity_type: "medication"
- code: RxNorm RxCUI code

Return ONLY a JSON array. No markdown:
[
  {{"chunk": "metformin 500mg oral", "entity_type": "medication", "code": "860975"}},
  {{"chunk": "lisinopril 10mg oral", "entity_type": "medication", "code": "314076"}}
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
        print(f"Medication coder raw response: {content}")
        
        codes = extract_json_from_text(content)
        
        if not codes or not isinstance(codes, list):
            print(f"⚠️ Failed to parse medication codes")
            codes = []
        
        print(f"✅ Coded {len(codes)} medications")
        
    except Exception as e:
        print(f"❌ Medication coding error: {e}")
        codes = []
    
    return {"medication_codes": codes}

# Node 5: Draft SOAP Note
def soap_drafter(state: AgentState) -> dict:
    """Generate SOAP note from extracted data"""
    text = state['document_text']
    conditions = state.get('conditions', [])
    medications = state.get('medications', [])
    
    conditions_text = ", ".join(conditions) if conditions else "None documented"
    meds_text = ", ".join([
        f"{m.get('drug', 'unknown')} {m.get('dosage', '')}" 
        for m in medications
    ]) if medications else "None documented"
    
    prompt = f"""Create a professional SOAP note from this clinical information.

ORIGINAL DOCUMENT:
{text}

EXTRACTED CONDITIONS: {conditions_text}
EXTRACTED MEDICATIONS: {meds_text}

Generate a complete SOAP note with these sections:

**S (Subjective):**
Patient's reported symptoms and complaints

**O (Objective):**
Observable findings, vital signs, examination results

**A (Assessment):**
Clinical assessment and diagnoses

**P (Plan):**
Treatment plan, medications, follow-up

Keep it professional, concise, and clinically appropriate.
"""
    
    try:
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        soap_note = response.choices[0].message.content
        print(f"✅ SOAP note drafted ({len(soap_note)} chars)")
        
    except Exception as e:
        print(f"❌ SOAP drafting error: {e}")
        soap_note = "Error generating SOAP note"
    
    return {"soap_note": soap_note}

def approval_gate(state: AgentState) -> dict:
    """Placeholder - actual approval happens in UI"""
    print("⏸️ Waiting for human approval...")
    # Just pass through
    return {}

def create_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("condition_extractor", condition_extractor)
    workflow.add_node("medication_extractor", medication_extractor)
    workflow.add_node("condition_coder", condition_coder)
    workflow.add_node("medication_coder", medication_coder)
    workflow.add_node("soap_drafter", soap_drafter)
    workflow.add_node("approval_gate", approval_gate)  # New node
    
    workflow.set_entry_point("condition_extractor")
    workflow.add_edge("condition_extractor", "medication_extractor")
    workflow.add_edge("medication_extractor", "condition_coder")
    workflow.add_edge("condition_coder", "medication_coder")
    workflow.add_edge("medication_coder", "soap_drafter")
    workflow.add_edge("soap_drafter", "approval_gate")  # Pause here
    workflow.add_edge("approval_gate", END)
    
    memory = MemorySaver()
    app = workflow.compile(
        checkpointer=memory,
        interrupt_before=["approval_gate"]  # Try interrupt_before instead
    )
    
    return app