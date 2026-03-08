"""
Utility functions for file processing
"""
import PyPDF2
import io

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes"""
    try:
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
    except:
        return file_bytes.decode('latin-1')

def extract_text_from_csv(file_bytes: bytes) -> str:
    """Extract text from CSV bytes"""
    try:
        import csv
        import io
        
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
    """Process file based on extension"""
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.pdf'):
        return extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith('.txt'):
        return extract_text_from_txt(file_bytes)
    elif filename_lower.endswith('.csv'):
        return extract_text_from_csv(file_bytes)
    else:
        return "Unsupported file type"