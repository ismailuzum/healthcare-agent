from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
import operator
from litellm import completion
import json
from specialists import SPECIALISTS

# State
class AgentState(TypedDict):
    case: str
    top_k: int
    selected_specialists: List[str]
    assessments: Annotated[List[dict], operator.add]
    final_summary: str
    reasoning: str

# 1. Supervisor
def supervisor_node(state: AgentState) -> dict:
    case = state['case']
    top_k = state.get('top_k', 3)
    
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

3. MULTI-SPECIALIST SCENARIOS:
   - Diabetes + Heart issues → Endocrinologist + Cardiologist
   - Rheumatism + Kidney → Rheumatologist + Nephrologist
   - Lung + Heart → Pulmonologist + Cardiologist

4. AVOID:
   ❌ Irrelevant specialists (e.g., cardiologist for skin issue)
   ❌ Two specialists from same field unless necessary
   ✅ Select most specific and essential specialists

5. EMERGENCY FLAGS:
   - "Chest pain", "can't breathe", "severe headache", "loss of consciousness" → Emergency Medicine MANDATORY
   - "Bleeding", "high fever (>39°C)", "stroke symptoms" → Emergency Medicine MANDATORY

CRITICAL INSTRUCTION FOR REASONING: Detect the language used in the CASE description. You MUST write your `reasoning` value in that EXACT SAME language (e.g., if the case is in Turkish, write the reasoning in Turkish).

📤 OUTPUT FORMAT:
Return ONLY JSON, nothing else:
{{
  "selected_specialists": ["key1", "key2", "key3"],
  "reasoning": "Brief explanation in the patient's language: Why these specialists were selected"
}}
"""
    
    try:
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = response.choices[0].message.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        result = json.loads(content)
        selected = result.get("selected_specialists", [])[:top_k]
        reasoning = result.get("reasoning", "")
        print(f"🧠 SUPERVISOR REASONING: {reasoning}")
    except Exception as e:
        print(f"❌ JSON parse error: {e}")
        selected = list(SPECIALISTS.keys())[:top_k]
        reasoning = "Could not parse reasoning from model response."
    
    # Padding if not enough specialists selected
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

# 2. Paralel Uzman Analizi
def analyze_specialists_node(state: AgentState) -> dict:
    selected = state["selected_specialists"]
    case = state["case"]
    assessments = []
    
    # Her uzman için sırayla analiz
    for key in selected:
        specialist = SPECIALISTS.get(key)
        if not specialist: continue
        
        prompt = f"""You are a {specialist['name']}. ({specialist['description']})

CASE: {case}

Analyze the case from your specialty's perspective (max 150 words). Address:
1. Relevant findings
2. Required tests
3. Treatment plan

CRITICAL INSTRUCTION: Detect the language used in the CASE description. You MUST write your ENTIRE assessment in that EXACT SAME language (e.g., if the case is in Turkish, respond completely in Turkish; if Dutch, respond in Dutch, etc.). Your response must only be the assessment.
"""
        
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        assessments.append({
            "specialist": specialist['name'],
            "key": key,
            "assessment": response.choices[0].message.content
        })
    
    return {"assessments": assessments}

# 3. Aggregator
def aggregator_node(state: AgentState) -> dict:
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

CRITICAL INSTRUCTION: Read the specialist assessments to detect the language. You MUST write your ENTIRE synthesis in that EXACT SAME language (e.g., if the assessments are in Turkish, write the synthesis in Turkish). Do not use English unless the assessments are actually in English.
"""
    
    response = completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    return {"final_summary": response.choices[0].message.content}

# Graph
def create_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("analyze_specialists", analyze_specialists_node)
    workflow.add_node("aggregator", aggregator_node)
    
    workflow.set_entry_point("supervisor")
    workflow.add_edge("supervisor", "analyze_specialists")
    workflow.add_edge("analyze_specialists", "aggregator")
    workflow.add_edge("aggregator", END)
    
    return workflow.compile()