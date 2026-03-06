import streamlit as st
import requests

st.title("🏥 Medical Summary Agent")

patient_input = st.text_area(
    "Hasta Semptomları:",
    placeholder="Örn: Başım ağrıyor, ateşim var, midem bulanıyor..."
)

if st.button("Analiz Et"):
    if patient_input:
        with st.spinner("Agent çalışıyor..."):
            response = requests.post(
                "http://api:8000/analyze",
                json={"patient_input": patient_input}
            )
            data = response.json()
        
        st.success("✅ Tamamlandı!")
        st.subheader("Final Özet:")
        st.write(data["final_summary"])
        
        with st.expander("🤔 Düşünme Süreci"):
            for msg in data["history"]:
                st.text(msg)