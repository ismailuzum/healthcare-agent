from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List
import uuid
from graph import create_graph
from utils import process_file

app = FastAPI()
graph = create_graph()

# In-memory storage
thread_storage = {}

class ResumeRequest(BaseModel):
    thread_id: str
    edited_soap_note: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Upload and process clinical documents
    Returns thread_id and SOAP draft for review
    """
    try:
        # Combine all files
        combined_text = ""
        for file in files:
            file_bytes = await file.read()
            text = process_file(file.filename, file_bytes)
            combined_text += f"\n\n--- {file.filename} ---\n{text}"
        
        # Create thread ID
        thread_id = str(uuid.uuid4())
        
        # Initial state
        initial_state = {
            "document_text": combined_text.strip(),
            "conditions": [],
            "medications": [],
            "condition_codes": [],
            "medication_codes": [],
            "soap_note": "",
            "final_note": ""
        }
        
        # Run pipeline (will pause after soap_drafter)
        config = {"configurable": {"thread_id": thread_id}}
        
        # Invoke - will stop at interrupt
        result = graph.invoke(initial_state, config)
        
        # Store result
        thread_storage[thread_id] = result
        
        return {
            "thread_id": thread_id,
            "status": "awaiting_approval",
            "soap_draft": result.get("soap_note", ""),
            "conditions": result.get("conditions", []),
            "medications": result.get("medications", []),
            "condition_codes": result.get("condition_codes", []),
            "medication_codes": result.get("medication_codes", [])
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resume")
def resume_workflow(request: ResumeRequest):
    """Finalize with human-edited SOAP note"""
    try:
        thread_id = request.thread_id
        edited_note = request.edited_soap_note
        
        print(f"\n📥 RESUME REQUEST")
        print(f"   Thread ID: {thread_id}")
        print(f"   Edited note length: {len(edited_note)}")
        print(f"   Available threads: {list(thread_storage.keys())}")
        
        # Validate request
        if not thread_id:
            raise HTTPException(status_code=400, detail="Missing thread_id")
        
        if not edited_note:
            raise HTTPException(status_code=400, detail="Missing edited_soap_note")
        
        # Check if thread exists
        if thread_id not in thread_storage:
            available = list(thread_storage.keys())
            raise HTTPException(
                status_code=404, 
                detail=f"Thread '{thread_id}' not found. Available threads: {available}"
            )
        
        # Get stored data
        stored_data = thread_storage[thread_id]
        print(f"   Retrieved stored data: {type(stored_data)}")
        
        # Validate stored data
        if stored_data is None:
            raise HTTPException(
                status_code=500, 
                detail="Stored data is None - this should not happen"
            )
        
        if not isinstance(stored_data, dict):
            raise HTTPException(
                status_code=500,
                detail=f"Stored data is {type(stored_data).__name__}, expected dict"
            )
        
        # Build result safely
        result = {
            "status": "completed",
            "final_note": edited_note,
            "conditions": stored_data.get("conditions", []),
            "medications": stored_data.get("medications", []),
            "condition_codes": stored_data.get("condition_codes", []),
            "medication_codes": stored_data.get("medication_codes", [])
        }
        
        print(f"✅ Result built successfully")
        print(f"   Conditions: {len(result['conditions'])}")
        print(f"   Medications: {len(result['medications'])}")
        
        # Cleanup
        del thread_storage[thread_id]
        print(f"✅ Thread {thread_id} cleaned up")
        
        return result
        
    except HTTPException as he:
        print(f"❌ HTTP Exception: {he.detail}")
        raise he
        
    except KeyError as ke:
        print(f"❌ KeyError: {ke}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"KeyError accessing stored data: {str(ke)}"
        )
        
    except AttributeError as ae:
        print(f"❌ AttributeError: {ae}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"AttributeError: {str(ae)} - check data structure"
        )
        
    except Exception as e:
        print(f"❌ Unexpected Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {str(e)}"
        )

@app.get("/status/{thread_id}")
def get_status(thread_id: str):
    """Check thread status"""
    if thread_id in thread_storage:
        return {"status": "awaiting_approval"}
    return {"status": "not_found"}