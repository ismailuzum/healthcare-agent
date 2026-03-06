from fastapi import FastAPI
from pydantic import BaseModel
from graph import create_graph

app = FastAPI()
graph = create_graph()

class AnalyzeRequest(BaseModel):
    patient_input: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    initial_state = {
        "patient_input": request.patient_input,
        "draft": "",
        "feedback": "",
        "is_approved": False,
        "messages": []
    }
    
    # recursion_limit burada!
    result = graph.invoke(
        initial_state, 
        {"recursion_limit": 5}
    )
    
    return {
        "final_summary": result["draft"],
        "history": result["messages"],
        "approved": result["is_approved"]
    }