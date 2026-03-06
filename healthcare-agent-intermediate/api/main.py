from fastapi import FastAPI
from pydantic import BaseModel
from graph import create_graph

app = FastAPI()
graph = create_graph()

class AnalyzeRequest(BaseModel):
    case: str
    top_k: int = 3

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    initial_state = {
        "case": request.case,
        "top_k": min(max(request.top_k, 1), 20),
        "selected_specialists": [],
        "assessments": [],
        "final_summary": "",
        "reasoning": ""
    }
    
    result = graph.invoke(initial_state)
    
    return {
        "final_summary": result["final_summary"],
        "assessments": result["assessments"],
        "selected_count": len(result["assessments"]),
        "selected_specialists": result.get("selected_specialists", []),
        "reasoning": result.get("reasoning", "")
    }