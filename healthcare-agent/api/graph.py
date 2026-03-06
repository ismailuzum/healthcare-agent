from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
import operator

class AgentState(TypedDict):
    patient_input: str
    draft: str
    feedback: str
    is_approved: bool
    messages: Annotated[list[str], operator.add]

def generator_node(state: AgentState) -> dict:
    from litellm import completion
    
    prompt = f"""Sen bir tıbbi asistansın. Hasta semptomlarını profesyonel bir özete dönüştür.

KURALLAR:
- ASLA teşhis koyma (migraine, COVID, flu gibi kelimeler YASAK)
- Sadece semptomları listele
- "Doktor muayenesi önerilir" de

Hasta: {state['patient_input']}
"""
    
    if state.get('feedback'):
        prompt += f"\n\nÖnceki hata: {state['feedback']}\nDüzelt ve yeniden yaz."
    
    response = completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    
    draft = response.choices[0].message.content
    
    return {
        "draft": draft,
        "messages": [f"[GENERATOR] {draft[:100]}..."]
    }

def critic_node(state: AgentState) -> dict:
    from litellm import completion
    import json
    
    draft = state['draft']
    
    # Teşhis kelimeleri listesi
    forbidden_words = [
        'migraine', 'migren', 'covid', 'flu', 'grip', 'influenza',
        'diabetes', 'diyabet', 'cancer', 'kanser', 'stroke', 'inme',
        'heart attack', 'kalp krizi', 'pneumonia', 'zatürre', 
        'asthma', 'astım', 'bronchitis', 'bronşit'
    ]
    
    # Basit kontrol
    has_diagnosis = any(word in draft.lower() for word in forbidden_words)
    
    if has_diagnosis:
        return {
            "is_approved": False,
            "feedback": "HATA: Teşhis kelimesi kullandın! Sadece semptomları yaz.",
            "messages": [f"[CRITIC] ❌ RED - Teşhis tespit edildi"]
        }
    
    # Profesyonellik kontrolü için LLM kullan
    prompt = f"""Bu metin profesyonel mi? Sadece 'yes' veya 'no' yaz.

Metin: {draft}

Cevap:"""
    
    response = completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    
    is_professional = "yes" in response.choices[0].message.content.lower()
    
    if not is_professional:
        return {
            "is_approved": False,
            "feedback": "Daha profesyonel yaz.",
            "messages": [f"[CRITIC] ❌ RED - Profesyonel değil"]
        }
    
    return {
        "is_approved": True,
        "feedback": "",
        "messages": [f"[CRITIC] ✅ ONAYLANDI"]
    }

def should_continue(state: AgentState) -> Literal["generator", "__end__"]:
    if state["is_approved"]:
        return "__end__"
    return "generator"

def create_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("generator", generator_node)
    workflow.add_node("critic", critic_node)
    
    workflow.set_entry_point("generator")
    workflow.add_edge("generator", "critic")
    workflow.add_conditional_edges(
        "critic",
        should_continue,
        {
            "generator": "generator",
            "__end__": END
        }
    )
    
    # ❌ YANLIŞ:
    # app = workflow.compile()
    # app.recursion_limit = 5
    
    # ✅ DOĞRU:
    app = workflow.compile()
    
    return app