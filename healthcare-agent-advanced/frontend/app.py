import streamlit as st
import requests
import time

st.set_page_config(page_title="Clinical Document Processor", layout="wide")

st.title("🏥 Clinical Document Processor with Human Review")

# Initialize session state
if 'state' not in st.session_state:
    st.session_state.state = 'idle'  # idle, awaiting_approval, completed
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = None
if 'soap_draft' not in st.session_state:
    st.session_state.soap_draft = ""
if 'data' not in st.session_state:
    st.session_state.data = {}

# STATE: IDLE - File Upload
if st.session_state.state == 'idle':
    st.subheader("📤 Upload Clinical Documents")
    st.caption("Supported formats: PDF, TXT, CSV")
    
    uploaded_files = st.file_uploader(
        "Choose file(s)",
        type=['pdf', 'txt', 'csv'],
        accept_multiple_files=True
    )
    
    if st.button("Process Documents", type="primary"):
        if uploaded_files:
            with st.spinner("Processing documents through AI pipeline..."):
                try:
                    files = [
                        ("files", (f.name, f.getvalue(), f.type))
                        for f in uploaded_files
                    ]
                    
                    response = requests.post(
                        "http://api:8000/upload",
                        files=files,
                        timeout=300
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Store in session state
                        st.session_state.thread_id = data['thread_id']
                        st.session_state.soap_draft = data['soap_draft']
                        st.session_state.data = data
                        st.session_state.state = 'awaiting_approval'
                        
                        st.rerun()
                    else:
                        st.error(f"Error: {response.text}")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please upload at least one file")

# STATE: AWAITING_APPROVAL - Human Review
elif st.session_state.state == 'awaiting_approval':
    st.success("✅ Pipeline completed! Awaiting your review...")
    
    # Show extracted data
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔍 Extracted Conditions")
        conditions = st.session_state.data.get('conditions', [])
        if conditions:
            for cond in conditions:
                st.write(f"• {cond}")
        else:
            st.write("None found")
    
    with col2:
        st.subheader("💊 Extracted Medications")
        medications = st.session_state.data.get('medications', [])
        if medications:
            for med in medications:
                st.write(f"• {med['drug']} {med['dosage']} ({med['route']})")
        else:
            st.write("None found")
    
    # Show codes in expander
    with st.expander("📋 View ICD-10 & RxNorm Codes"):
        st.write("**ICD-10-CM Codes:**")
        for code in st.session_state.data.get('condition_codes', []):
            st.write(f"• {code['chunk']} → `{code['code']}`")
        
        st.write("\n**RxNorm Codes:**")
        for code in st.session_state.data.get('medication_codes', []):
            st.write(f"• {code['chunk']} → `{code['code']}`")
    
    # SOAP Note Editor
    st.subheader("📝 SOAP Note - Review & Edit")
    st.caption("Edit the SOAP note below before approving")
    
    edited_soap = st.text_area(
        "SOAP Note",
        value=st.session_state.soap_draft,
        height=400,
        key="soap_editor"
    )
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("✅ Approve & Finalize", type="primary"):
            print(f"Thread ID: {st.session_state.thread_id}")
            print(f"Edited SOAP length: {len(edited_soap)}")
    
    with st.spinner("Finalizing..."):
        try:
            payload = {
                "thread_id": st.session_state.thread_id,
                "edited_soap_note": edited_soap
            }
            
            print(f"Sending payload: {payload}")
            
            response = requests.post(
                "http://api:8000/resume",
                json=payload,
                timeout=60
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            
            if response.status_code == 200:
                st.session_state.data = response.json()
                st.session_state.state = 'completed'
                st.rerun()
            else:
                st.error(f"Error {response.status_code}: {response.text}")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            import traceback
            st.text(traceback.format_exc())
    
    with col2:
        if st.button("🔄 Start Over"):
            st.session_state.state = 'idle'
            st.session_state.thread_id = None
            st.rerun()

# STATE: COMPLETED - Show Final Result
elif st.session_state.state == 'completed':
    st.success("🎉 Clinical Documentation Completed!")
    
    st.subheader("📄 Final Signed SOAP Note")
    st.text_area(
        "Final Note",
        value=st.session_state.data.get('final_note', ''),
        height=400,
        disabled=True
    )
    
    # Show all extracted data
    with st.expander("📊 View Complete Analysis"):
        st.write("**Conditions:**")
        for cond in st.session_state.data.get('conditions', []):
            st.write(f"• {cond}")
        
        st.write("\n**Medications:**")
        for med in st.session_state.data.get('medications', []):
            st.write(f"• {med}")
        
        st.write("\n**ICD-10 Codes:**")
        for code in st.session_state.data.get('condition_codes', []):
            st.write(f"• {code['chunk']} → `{code['code']}`")
        
        st.write("\n**RxNorm Codes:**")
        for code in st.session_state.data.get('medication_codes', []):
            st.write(f"• {code['chunk']} → `{code['code']}`")
    
    if st.button("🔄 Process New Documents"):
        st.session_state.state = 'idle'
        st.session_state.thread_id = None
        st.rerun()