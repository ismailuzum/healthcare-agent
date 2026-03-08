"""
Unified Healthcare Agent API
Step-by-step endpoints with file upload support.
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid

from graph import create_analyze_graph, recommend_specialists, create_consult_graph
from specialists import SPECIALISTS
from utils import process_file

app = FastAPI(
    title="Healthcare Agent Unified API",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create graph instances
analyze_graph = create_analyze_graph()

# In-memory session storage
sessions = {}


# ── Request/Response Models ──────────────────────────────────

class AnalyzeRequest(BaseModel):
    patient_input: str

class RecommendRequest(BaseModel):
    case_summary: str
    top_k: int = 3

class ConsultRequest(BaseModel):
    session_id: str
    selected_specialists: List[str]

class FinalizeRequest(BaseModel):
    session_id: str
    edited_soap_note: str


# ── Endpoints ────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/specialists")
def get_specialists():
    """Return all 20 specialist definitions"""
    result = []
    for key, val in SPECIALISTS.items():
        result.append({
            "key": key,
            "name": val["name"],
            "description": val["description"],
            "icon": val.get("icon", "🩺")
        })
    return result


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    """
    STEP 1: Generator/Critic loop (text input)
    Takes patient complaint → returns approved professional summary
    """
    try:
        initial_state = {
            "patient_input": request.patient_input,
            "draft": "",
            "feedback": "",
            "is_approved": False,
            "iteration": 0,
            "messages": []
        }

        result = analyze_graph.invoke(
            initial_state,
            {"recursion_limit": 12}
        )

        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "patient_input": request.patient_input,
            "approved_summary": result["draft"],
        }

        return {
            "session_id": session_id,
            "approved_summary": result["draft"],
            "is_approved": result["is_approved"],
            "iterations": result.get("iteration", 0),
            "messages": result["messages"]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-analyze")
async def upload_analyze(
    files: List[UploadFile] = File(...),
    additional_text: Optional[str] = Form(default="")
):
    """
    STEP 1 (file upload): Accept PDF/TXT files + optional text
    Extract text from files → run Generator/Critic loop → return summary
    """
    try:
        # Extract text from all uploaded files
        combined_text = ""
        for file in files:
            file_bytes = await file.read()
            text = process_file(file.filename, file_bytes)
            combined_text += f"\n\n--- {file.filename} ---\n{text}"

        # Add any additional text
        if additional_text:
            combined_text = additional_text.strip() + "\n\n" + combined_text

        combined_text = combined_text.strip()

        if not combined_text:
            raise HTTPException(status_code=400, detail="No text could be extracted from uploaded files")

        # Run the analyzer
        initial_state = {
            "patient_input": combined_text,
            "draft": "",
            "feedback": "",
            "is_approved": False,
            "iteration": 0,
            "messages": []
        }

        result = analyze_graph.invoke(
            initial_state,
            {"recursion_limit": 12}
        )

        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "patient_input": combined_text,
            "approved_summary": result["draft"],
        }

        return {
            "session_id": session_id,
            "approved_summary": result["draft"],
            "is_approved": result["is_approved"],
            "iterations": result.get("iteration", 0),
            "messages": result["messages"]
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommend-specialists")
def recommend(request: RecommendRequest):
    """
    STEP 2: Supervisor agent recommends specialists
    """
    try:
        result = recommend_specialists(
            case=request.case_summary,
            top_k=min(max(request.top_k, 1), 20)
        )

        return {
            "recommended_specialists": result["selected_specialists"],
            "reasoning": result["reasoning"]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/consult")
def consult(request: ConsultRequest):
    """
    STEP 3: Specialist consultations + extraction + coding + SOAP
    Full pipeline: Specialists → Aggregator → Extraction → Coding → SOAP
    """
    try:
        session = sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        valid_specialists = [
            s for s in request.selected_specialists
            if s in SPECIALISTS
        ]
        if not valid_specialists:
            raise HTTPException(status_code=400, detail="No valid specialists selected")

        # Run full consultation pipeline
        consult_graph = create_consult_graph()

        initial_state = {
            "case": session["approved_summary"],
            "selected_specialists": valid_specialists,
            "assessments": [],
            "aggregated_summary": "",
            "conditions": [],
            "medications": [],
            "condition_codes": [],
            "medication_codes": [],
            "soap_note": ""
        }

        result = consult_graph.invoke(initial_state)

        # Update session
        session["assessments"] = result["assessments"]
        session["aggregated_summary"] = result["aggregated_summary"]
        session["soap_note"] = result["soap_note"]
        session["selected_specialists"] = valid_specialists
        session["conditions"] = result.get("conditions", [])
        session["medications"] = result.get("medications", [])
        session["condition_codes"] = result.get("condition_codes", [])
        session["medication_codes"] = result.get("medication_codes", [])

        return {
            "assessments": result["assessments"],
            "aggregated_summary": result["aggregated_summary"],
            "soap_note": result["soap_note"],
            "specialist_count": len(result["assessments"]),
            "conditions": result.get("conditions", []),
            "medications": result.get("medications", []),
            "condition_codes": result.get("condition_codes", []),
            "medication_codes": result.get("medication_codes", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/finalize")
def finalize(request: FinalizeRequest):
    """
    STEP 4: Accept edited SOAP note and produce final report
    """
    try:
        session = sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        final_report = {
            "status": "completed",
            "patient_input": session.get("patient_input", ""),
            "approved_summary": session.get("approved_summary", ""),
            "selected_specialists": session.get("selected_specialists", []),
            "assessments": session.get("assessments", []),
            "aggregated_summary": session.get("aggregated_summary", ""),
            "conditions": session.get("conditions", []),
            "medications": session.get("medications", []),
            "condition_codes": session.get("condition_codes", []),
            "medication_codes": session.get("medication_codes", []),
            "final_soap_note": request.edited_soap_note
        }

        del sessions[request.session_id]

        return final_report

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
