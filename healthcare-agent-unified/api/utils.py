"""
Utility functions for file processing and JSON extraction
"""
import json
import re
import io


def extract_json_from_text(text: str):
    """Extract JSON from text that might have markdown or extra content"""
    # Try to find JSON array
    json_match = re.search(r'\[.*\]', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except Exception:
            pass

    # Try to find JSON object
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except Exception:
            pass

    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        return None


def clean_llm_json(content: str) -> str:
    """Clean LLM response to extract JSON string"""
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].strip()
        if content.startswith("\n"):
            content = content[1:]
    return content.strip()


# ── File Processing ──────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes"""
    try:
        import PyPDF2
        pdf_file = io.BytesIO(file_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"

        return text.strip()
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from TXT bytes"""
    try:
        return file_bytes.decode('utf-8')
    except Exception:
        return file_bytes.decode('latin-1')


def extract_text_from_csv(file_bytes: bytes) -> str:
    """Extract text from CSV bytes"""
    try:
        import csv
        text = file_bytes.decode('utf-8')
        csv_file = io.StringIO(text)
        reader = csv.reader(csv_file)

        rows = []
        for row in reader:
            rows.append(", ".join(row))

        return "\n".join(rows)
    except Exception as e:
        return f"Error extracting CSV: {str(e)}"


def process_file(filename: str, file_bytes: bytes) -> str:
    """Process file based on extension and return extracted text"""
    filename_lower = filename.lower()

    if filename_lower.endswith('.pdf'):
        return extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith('.txt'):
        return extract_text_from_txt(file_bytes)
    elif filename_lower.endswith('.csv'):
        return extract_text_from_csv(file_bytes)
    else:
        return f"Unsupported file type: {filename}"
