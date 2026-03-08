/**
 * HealthAI — Unified Healthcare Agent Frontend v3
 * File upload, multi-language, medical coding, visual report
 */

const API_BASE = '/api';

// ── State ────────────────────────────────────────────────────
const state = {
    currentStep: 1,
    sessionId: null,
    patientInput: '',
    uploadedFiles: [],       // File objects
    approvedSummary: '',
    recommendedSpecialists: [],
    allSpecialists: [],
    selectedSpecialists: [],
    aiReasoning: '',
    assessments: [],
    aggregatedSummary: '',
    conditions: [],
    medications: [],
    conditionCodes: [],
    medicationCodes: [],
    soapNote: '',
    originalSoapNote: '',
    finalReport: null,
    reportDate: '',
    reportTime: ''
};


// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const textarea = document.getElementById('patient-input');
    textarea.addEventListener('input', () => {
        document.getElementById('char-count').textContent = `${textarea.value.length} characters`;
    });

    updateSoapDateTime();
    loadSpecialists();
    setupFileUpload();
});


// ── File Upload ──────────────────────────────────────────────
function setupFileUpload() {
    const dropzone = document.getElementById('file-dropzone');
    const fileInput = document.getElementById('file-input');

    // Click to browse
    dropzone.addEventListener('click', () => fileInput.click());

    // File input change
    fileInput.addEventListener('change', (e) => {
        addFiles(e.target.files);
        fileInput.value = '';
    });

    // Drag & drop
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        addFiles(e.dataTransfer.files);
    });
}

function addFiles(fileList) {
    for (const file of fileList) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (['pdf', 'txt', 'csv'].includes(ext)) {
            // Avoid duplicates
            if (!state.uploadedFiles.some(f => f.name === file.name && f.size === file.size)) {
                state.uploadedFiles.push(file);
            }
        } else {
            showToast(`Unsupported file type: .${ext}`, 'error');
        }
    }
    renderFileList();
}

function removeFile(index) {
    state.uploadedFiles.splice(index, 1);
    renderFileList();
}

function renderFileList() {
    const container = document.getElementById('file-list');
    container.innerHTML = '';

    state.uploadedFiles.forEach((file, i) => {
        const chip = document.createElement('div');
        chip.className = 'file-chip';

        const icon = file.name.endsWith('.pdf') ? '📄' : '📝';
        const sizeKB = (file.size / 1024).toFixed(1);

        chip.innerHTML = `
            <span>${icon}</span>
            <span>${file.name}</span>
            <span style="color:var(--text-muted);font-size:.72rem;">(${sizeKB} KB)</span>
            <span class="file-chip-remove" onclick="removeFile(${i})">✕</span>
        `;
        container.appendChild(chip);
    });
}


// ── Navigation ───────────────────────────────────────────────
function goToStep(step) {
    document.querySelectorAll('.step-panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById(`step-${step}`);
    if (panel) panel.classList.add('active');
    updateStepIndicator(step);
    state.currentStep = step;
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updateStepIndicator(activeStep) {
    document.querySelectorAll('.step-item').forEach((item, i) => {
        const n = i + 1;
        item.classList.remove('active', 'completed');
        if (n < activeStep) item.classList.add('completed');
        else if (n === activeStep) item.classList.add('active');
    });
    document.querySelectorAll('.step-connector').forEach((c, i) => {
        c.classList.toggle('completed', i + 1 < activeStep);
    });
}

function updateSliderValue(slider) {
    document.getElementById('top-k-value').textContent = slider.value;
}

function updateSoapDateTime() {
    const now = new Date();
    state.reportDate = now.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    state.reportTime = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    const dateEl = document.getElementById('soap-date');
    const timeEl = document.getElementById('soap-time');
    if (dateEl) dateEl.textContent = state.reportDate;
    if (timeEl) timeEl.textContent = state.reportTime;
}


// ── API ──────────────────────────────────────────────────────
async function apiCall(endpoint, method = 'GET', body = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(`${API_BASE}${endpoint}`, opts);
    if (!r.ok) throw new Error(`API Error (${r.status}): ${await r.text()}`);
    return r.json();
}

async function apiFormData(endpoint, formData) {
    const r = await fetch(`${API_BASE}${endpoint}`, { method: 'POST', body: formData });
    if (!r.ok) throw new Error(`API Error (${r.status}): ${await r.text()}`);
    return r.json();
}


// ── Loading ──────────────────────────────────────────────────
function showLoading(text = 'Processing...', progress = 0) {
    document.getElementById('loading-text').textContent = text;
    document.getElementById('loading-progress').style.width = `${progress}%`;
    document.getElementById('loading-overlay').classList.remove('hidden');
}
function updateLoading(text, progress) {
    document.getElementById('loading-text').textContent = text;
    document.getElementById('loading-progress').style.width = `${progress}%`;
}
function hideLoading() { document.getElementById('loading-overlay').classList.add('hidden'); }


// ── Toast ────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
    const c = document.getElementById('toast-container');
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = message;
    c.appendChild(t);
    setTimeout(() => { t.classList.add('removing'); setTimeout(() => t.remove(), 300); }, duration);
}


// ══════════════════════════════════════════════════════════════
// STEP 1 → 2: Analyze (text OR file upload)
// ══════════════════════════════════════════════════════════════
async function startAnalysis() {
    const textInput = document.getElementById('patient-input').value.trim();
    const hasFiles = state.uploadedFiles.length > 0;

    if (!textInput && !hasFiles) {
        showToast('Please enter a complaint or upload a file.', 'error');
        return;
    }

    showLoading('🔬 Analyzing patient data...', 10);

    try {
        let data;

        if (hasFiles) {
            // Use file upload endpoint
            updateLoading('📎 Uploading files & analyzing...', 25);
            const formData = new FormData();
            state.uploadedFiles.forEach(f => formData.append('files', f));
            if (textInput) formData.append('additional_text', textInput);

            data = await apiFormData('/upload-analyze', formData);
        } else {
            // Text-only
            updateLoading('🔬 Generator/Critic loop running...', 30);
            data = await apiCall('/analyze', 'POST', { patient_input: textInput });
        }

        updateLoading('✅ Summary approved!', 100);

        state.sessionId = data.session_id;
        state.approvedSummary = data.approved_summary;
        state.patientInput = textInput || '(uploaded files)';

        document.getElementById('approved-summary').textContent = data.approved_summary;

        setTimeout(() => {
            hideLoading();
            goToStep(2);
            showToast(`Summary approved in ${data.iterations} iteration(s).`, 'success');
        }, 500);

    } catch (error) {
        hideLoading();
        showToast(`Error: ${error.message}`, 'error', 6000);
        console.error(error);
    }
}


// ══════════════════════════════════════════════════════════════
// Load Specialists
// ══════════════════════════════════════════════════════════════
async function loadSpecialists() {
    try { state.allSpecialists = await apiCall('/specialists'); }
    catch (e) { console.warn('Could not preload specialists:', e.message); }
}


// ══════════════════════════════════════════════════════════════
// STEP 2 → 3: Recommend Specialists
// ══════════════════════════════════════════════════════════════
async function recommendSpecialists() {
    const topK = parseInt(document.getElementById('top-k-slider').value);
    showLoading('🧠 Supervisor agent selecting specialists...', 15);

    try {
        updateLoading('👥 Selecting most relevant specialists...', 40);
        const data = await apiCall('/recommend-specialists', 'POST', {
            case_summary: state.approvedSummary, top_k: topK
        });

        updateLoading('✅ Recommendations ready!', 100);
        state.recommendedSpecialists = data.recommended_specialists;
        state.selectedSpecialists = [...data.recommended_specialists];
        state.aiReasoning = data.reasoning;

        document.getElementById('ai-reasoning').textContent = data.reasoning;
        renderSpecialistGrid();

        setTimeout(() => {
            hideLoading();
            goToStep(3);
            showToast(`${data.recommended_specialists.length} specialist(s) recommended.`, 'success');
        }, 500);
    } catch (error) {
        hideLoading();
        showToast(`Error: ${error.message}`, 'error', 6000);
    }
}

function renderSpecialistGrid() {
    const grid = document.getElementById('specialist-grid');
    grid.innerHTML = '';
    let specs = state.allSpecialists.length > 0 ? state.allSpecialists
        : state.recommendedSpecialists.map(k => ({ key: k, name: k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), description: '', icon: '🩺' }));

    specs.forEach(s => {
        const sel = state.selectedSpecialists.includes(s.key);
        const rec = state.recommendedSpecialists.includes(s.key);
        const card = document.createElement('div');
        card.className = `specialist-card ${sel ? 'selected' : ''}`;
        card.onclick = () => toggleSpecialist(s.key, card);
        card.innerHTML = `
            <div class="specialist-checkbox">${sel ? '✓' : ''}</div>
            <div class="specialist-info">
                <div class="specialist-name"><span>${s.icon}</span> ${s.name} ${rec ? '<span style="font-size:.7rem;color:var(--accent-amber)">★ AI</span>' : ''}</div>
                <div class="specialist-desc">${s.description}</div>
            </div>`;
        grid.appendChild(card);
    });
}

function toggleSpecialist(key, card) {
    const i = state.selectedSpecialists.indexOf(key);
    if (i >= 0) {
        state.selectedSpecialists.splice(i, 1);
        card.classList.remove('selected');
        card.querySelector('.specialist-checkbox').textContent = '';
    } else {
        state.selectedSpecialists.push(key);
        card.classList.add('selected');
        card.querySelector('.specialist-checkbox').textContent = '✓';
    }
}


// ══════════════════════════════════════════════════════════════
// STEP 3 → 4: Consultation (Specialists + Extraction + Coding)
// ══════════════════════════════════════════════════════════════
async function startConsultation() {
    if (state.selectedSpecialists.length === 0) {
        showToast('Please select at least one specialist.', 'error');
        return;
    }

    showLoading(`🩺 ${state.selectedSpecialists.length} specialist(s) analyzing...`, 10);

    try {
        const pI = setInterval(() => {
            const c = parseFloat(document.getElementById('loading-progress').style.width);
            if (c < 70) updateLoading('🧬 Running extraction & coding pipeline...', c + 2);
        }, 3000);

        const data = await apiCall('/consult', 'POST', {
            session_id: state.sessionId,
            selected_specialists: state.selectedSpecialists
        });

        clearInterval(pI);
        updateLoading('📋 Clinical note generated!', 100);

        state.assessments = data.assessments;
        state.aggregatedSummary = data.aggregated_summary;
        state.soapNote = data.soap_note;
        state.originalSoapNote = data.soap_note;
        state.conditions = data.conditions || [];
        state.medications = data.medications || [];
        state.conditionCodes = data.condition_codes || [];
        state.medicationCodes = data.medication_codes || [];

        renderSpecialistTabs(data.assessments);
        document.getElementById('aggregated-summary').textContent = data.aggregated_summary;
        renderExtractionResults();

        document.getElementById('soap-editor').value = data.soap_note;
        updateSoapDateTime();
        renderSoapSpecialists();

        setTimeout(() => {
            hideLoading();
            goToStep(4);
            showToast(`Analysis complete: ${data.specialist_count} specialists, ${state.conditionCodes.length} ICD-10, ${state.medicationCodes.length} RxNorm codes.`, 'success');
        }, 500);

    } catch (error) {
        hideLoading();
        showToast(`Error: ${error.message}`, 'error', 6000);
    }
}

function renderSpecialistTabs(assessments) {
    const hdr = document.getElementById('specialist-tabs-header');
    const cnt = document.getElementById('specialist-tabs-content');
    hdr.innerHTML = ''; cnt.innerHTML = '';

    assessments.forEach((a, i) => {
        const btn = document.createElement('button');
        btn.className = `tab-btn ${i === 0 ? 'active' : ''}`;
        btn.textContent = `${a.icon || '🩺'} ${a.specialist}`;
        btn.onclick = () => switchTab(i);
        btn.setAttribute('data-tab-index', i);
        hdr.appendChild(btn);

        const p = document.createElement('div');
        p.className = `tab-panel ${i === 0 ? 'active' : ''}`;
        p.setAttribute('data-tab-index', i);
        p.innerHTML = `<div class="tab-panel-content">${a.assessment}</div>`;
        cnt.appendChild(p);
    });
}

function switchTab(idx) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', +b.getAttribute('data-tab-index') === idx));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', +p.getAttribute('data-tab-index') === idx));
}

function renderExtractionResults() {
    // Conditions + ICD-10
    const condEl = document.getElementById('conditions-list');
    if (state.conditionCodes.length > 0) {
        condEl.innerHTML = state.conditionCodes.map(c => `
            <div class="code-pill">
                <span class="code-pill-name">${escapeHtml(c.chunk || '')}</span>
                <span class="code-pill-code">${escapeHtml(c.code || 'N/A')}</span>
            </div>
        `).join('');
    } else if (state.conditions.length > 0) {
        condEl.innerHTML = state.conditions.map(c => `
            <div class="code-pill"><span class="code-pill-name">${escapeHtml(c)}</span></div>
        `).join('');
    } else {
        condEl.innerHTML = '<span class="extraction-empty">No conditions extracted</span>';
    }

    // Medications + RxNorm
    const medEl = document.getElementById('medications-list');
    if (state.medicationCodes.length > 0) {
        medEl.innerHTML = state.medicationCodes.map(m => `
            <div class="code-pill">
                <span class="code-pill-name">${escapeHtml(m.chunk || '')}</span>
                <span class="code-pill-code">${escapeHtml(m.code || 'N/A')}</span>
            </div>
        `).join('');
    } else if (state.medications.length > 0) {
        medEl.innerHTML = state.medications.map(m => `
            <div class="code-pill"><span class="code-pill-name">${escapeHtml(m.drug || '')} ${m.dosage || ''}</span></div>
        `).join('');
    } else {
        medEl.innerHTML = '<span class="extraction-empty">No medications extracted</span>';
    }
}

function renderSoapSpecialists() {
    const c = document.getElementById('soap-specialists-row');
    c.innerHTML = '<span style="font-size:.78rem;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;margin-right:.5rem;align-self:center;">Consulting:</span>';
    state.selectedSpecialists.forEach(key => {
        const s = state.allSpecialists.find(x => x.key === key);
        const name = s ? s.name : key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        const icon = s ? s.icon : '🩺';
        const chip = document.createElement('span');
        chip.className = 'soap-specialist-chip';
        chip.innerHTML = `${icon} ${name}`;
        c.appendChild(chip);
    });
}


// ══════════════════════════════════════════════════════════════
// STEP 5
// ══════════════════════════════════════════════════════════════
function resetSoap() {
    document.getElementById('soap-editor').value = state.originalSoapNote;
    showToast('Clinical note reset.', 'info');
}


// ══════════════════════════════════════════════════════════════
// STEP 5 → 6: Finalize
// ══════════════════════════════════════════════════════════════
async function finalizeReport() {
    const editedSoap = document.getElementById('soap-editor').value.trim();
    const patientName = document.getElementById('patient-name').value.trim();
    const patientId = document.getElementById('patient-id').value.trim();
    const patientDob = document.getElementById('patient-dob').value;
    const approvingPhysician = document.getElementById('approving-physician').value.trim();
    const physicianTitle = document.getElementById('physician-title').value.trim();

    if (!editedSoap) { showToast('Clinical note cannot be empty.', 'error'); return; }

    showLoading('📄 Generating final report...', 30);

    try {
        updateLoading('✅ Building report...', 70);
        const data = await apiCall('/finalize', 'POST', {
            session_id: state.sessionId,
            edited_soap_note: editedSoap
        });

        updateLoading('🎉 Complete!', 100);

        data.patientName = patientName || 'N/A';
        data.patientId = patientId || 'N/A';
        data.patientDob = patientDob ? new Date(patientDob).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : 'N/A';
        data.approvingPhysician = approvingPhysician || 'N/A';
        data.physicianTitle = physicianTitle || '';
        data.reportDate = state.reportDate;
        data.reportTime = state.reportTime;

        state.finalReport = data;

        renderSOAPDocument(data, 'soap-document');
        renderSOAPDocument(data, 'print-soap-document');

        setTimeout(() => {
            hideLoading();
            goToStep(6);
            showToast('Report generated successfully!', 'success');
        }, 600);

    } catch (error) {
        hideLoading();
        showToast(`Error: ${error.message}`, 'error', 6000);
    }
}


function renderSOAPDocument(data, containerId) {
    const container = document.getElementById(containerId);

    // Specialist chips
    const specChips = (data.selected_specialists || []).map(key => {
        const s = state.allSpecialists.find(x => x.key === key);
        const name = s ? s.name : key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        const icon = s ? s.icon : '🩺';
        return `<span class="soap-doc-spec-chip">${icon} ${name}</span>`;
    }).join('');

    // Condition code tags
    const condCodes = (data.condition_codes || []).map(c =>
        `<span class="soap-doc-code-tag icd"><span>${escapeHtml(c.chunk || '')}</span> <span class="soap-doc-code-label icd">${escapeHtml(c.code || '')}</span></span>`
    ).join('');

    // Medication code tags
    const medCodes = (data.medication_codes || []).map(m =>
        `<span class="soap-doc-code-tag rxn"><span>${escapeHtml(m.chunk || '')}</span> <span class="soap-doc-code-label rxn">${escapeHtml(m.code || '')}</span></span>`
    ).join('');

    const hasCodes = condCodes || medCodes;

    container.innerHTML = `
        <div class="soap-document">
            <!-- Header -->
            <div class="soap-doc-header">
                <div class="soap-doc-patient">
                    <div class="soap-doc-clinic">🏥 HealthAI Medical Report</div>
                    <div class="soap-doc-field"><strong>Patient:</strong> ${escapeHtml(data.patientName)}</div>
                    <div class="soap-doc-field"><strong>Patient ID:</strong> ${escapeHtml(data.patientId)}</div>
                    <div class="soap-doc-field"><strong>Date of Birth:</strong> ${escapeHtml(data.patientDob)}</div>
                </div>
                <div class="soap-doc-date">
                    <div class="soap-doc-date-line"><strong>Date:</strong> ${escapeHtml(data.reportDate)}</div>
                    <div class="soap-doc-date-line"><strong>Time:</strong> ${escapeHtml(data.reportTime)}</div>
                </div>
            </div>

            <!-- Clinical Note Body -->
            <div class="soap-doc-body">
                <div class="soap-doc-body-text">${escapeHtml(data.final_soap_note || '')}</div>
            </div>

            ${hasCodes ? `
            <!-- Medical Codes -->
            <div class="soap-doc-codes">
                <div class="soap-doc-codes-grid">
                    ${condCodes ? `
                    <div class="soap-doc-codes-card">
                        <div class="soap-doc-codes-header icd">🔍 Conditions — ICD-10-CM</div>
                        <div class="soap-doc-codes-body">${condCodes}</div>
                    </div>` : ''}
                    ${medCodes ? `
                    <div class="soap-doc-codes-card">
                        <div class="soap-doc-codes-header rxn">💊 Medications — RxNorm</div>
                        <div class="soap-doc-codes-body">${medCodes}</div>
                    </div>` : ''}
                </div>
            </div>` : ''}

            <!-- Specialists -->
            <div class="soap-doc-specialists">
                <div class="soap-doc-specialists-title">Consulting Specialists</div>
                <div class="soap-doc-specialists-list">${specChips}</div>
            </div>

            <!-- Footer / Signature -->
            <div class="soap-doc-footer">
                <div class="soap-doc-signature">
                    <div class="soap-doc-sig-label">Signature</div>
                    <div class="soap-doc-sig-line">${escapeHtml(data.approvingPhysician)}</div>
                    <div class="soap-doc-sig-name">${escapeHtml(data.approvingPhysician)}</div>
                    <div class="soap-doc-sig-title">${escapeHtml(data.physicianTitle)}</div>
                </div>
                <div class="soap-doc-stamp">
                    <div class="soap-doc-stamp-date">${escapeHtml(data.reportDate)}</div>
                    <div class="soap-doc-approved-badge">✅ Approved & Signed</div>
                </div>
            </div>
        </div>
    `;
}


// ══════════════════════════════════════════════════════════════
// Downloads
// ══════════════════════════════════════════════════════════════
function downloadPDF() {
    document.getElementById('print-soap-document').innerHTML = document.getElementById('soap-document').innerHTML;
    window.print();
    showToast('Use the print dialog to save as PDF.', 'info');
}

function downloadTXT() {
    const d = state.finalReport;
    if (!d) return;

    const specs = (d.selected_specialists || []).map(k => {
        const s = state.allSpecialists.find(x => x.key === k);
        return s ? s.name : k;
    }).join(', ');

    const condLines = (d.condition_codes || []).map(c => `  ${c.chunk}: ICD-10 ${c.code}`).join('\n');
    const medLines = (d.medication_codes || []).map(m => `  ${m.chunk}: RxNorm ${m.code}`).join('\n');

    const txt = `
══════════════════════════════════════════════
       HEALTHAI MEDICAL REPORT
══════════════════════════════════════════════

PATIENT INFORMATION
─────────────────────────────────────────────
Patient Name:    ${d.patientName || 'N/A'}
Patient ID:      ${d.patientId || 'N/A'}
Date of Birth:   ${d.patientDob || 'N/A'}
Date:            ${d.reportDate || 'N/A'}
Time:            ${d.reportTime || 'N/A'}

CLINICAL NOTE
─────────────────────────────────────────────
${d.final_soap_note || ''}

MEDICAL CODES — ICD-10-CM
─────────────────────────────────────────────
${condLines || '  None'}

MEDICAL CODES — RxNorm
─────────────────────────────────────────────
${medLines || '  None'}

CONSULTING SPECIALISTS
─────────────────────────────────────────────
${specs || 'None'}

APPROVAL
─────────────────────────────────────────────
Approving Physician:  ${d.approvingPhysician || 'N/A'}
Title:                ${d.physicianTitle || 'N/A'}
Date:                 ${d.reportDate || 'N/A'}
Status:               APPROVED & SIGNED

══════════════════════════════════════════════
`.trim();

    downloadFile(txt, 'Clinical_Report.txt', 'text/plain');
    showToast('TXT file downloaded.', 'success');
}

function downloadHTML() {
    const doc = document.getElementById('soap-document');
    const html = `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Clinical Report — HealthAI</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
body{font-family:'Inter',sans-serif;margin:2rem auto;max-width:800px;background:#fff;color:#1a1a2e}
.soap-document{border:1px solid #e2e8f0;border-radius:12px;overflow:hidden}
.soap-doc-header{display:flex;justify-content:space-between;padding:1.75rem 2rem 1.25rem;border-bottom:3px solid #2563eb;background:linear-gradient(135deg,#f8fafc,#eef2ff)}
.soap-doc-patient{flex:1}.soap-doc-clinic{font-size:1.1rem;font-weight:800;color:#1e3a5f;margin-bottom:.75rem}
.soap-doc-field{font-size:.85rem;color:#475569;line-height:1.6}.soap-doc-field strong{color:#1e293b;font-weight:600;display:inline-block;min-width:100px}
.soap-doc-date{text-align:right}.soap-doc-date-line{font-size:.85rem;color:#475569;line-height:1.6}.soap-doc-date-line strong{color:#1e293b;font-weight:600}
.soap-doc-body{padding:1.75rem 2rem}.soap-doc-body-text{font-size:.92rem;line-height:1.85;color:#334155;white-space:pre-wrap}
.soap-doc-codes{padding:1.25rem 2rem;border-top:1px solid #e2e8f0}
.soap-doc-codes-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.soap-doc-codes-card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden}
.soap-doc-codes-header{padding:.5rem .85rem;font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
.soap-doc-codes-header.icd{background:#ede9fe;color:#5b21b6;border-bottom:1px solid #ddd6fe}
.soap-doc-codes-header.rxn{background:#cffafe;color:#0e7490;border-bottom:1px solid #a5f3fc}
.soap-doc-codes-body{padding:.65rem .85rem;display:flex;flex-wrap:wrap;gap:.35rem}
.soap-doc-code-tag{display:inline-flex;align-items:center;gap:.25rem;padding:.2rem .55rem;border-radius:5px;font-size:.75rem;font-weight:600}
.soap-doc-code-tag.icd{background:#f5f3ff;color:#6d28d9;border:1px solid #ddd6fe}
.soap-doc-code-tag.rxn{background:#ecfeff;color:#0891b2;border:1px solid #a5f3fc}
.soap-doc-code-label{font-family:monospace;font-weight:700;padding:.1rem .3rem;border-radius:3px;font-size:.7rem}
.soap-doc-code-label.icd{background:#ede9fe}.soap-doc-code-label.rxn{background:#cffafe}
.soap-doc-specialists{padding:1rem 2rem;border-top:1px solid #e2e8f0;background:#f8fafc}
.soap-doc-specialists-title{font-size:.78rem;font-weight:700;text-transform:uppercase;color:#64748b;margin-bottom:.5rem}
.soap-doc-specialists-list{display:flex;flex-wrap:wrap;gap:.4rem}
.soap-doc-spec-chip{display:inline-flex;align-items:center;gap:.25rem;padding:.25rem .65rem;border-radius:14px;font-size:.78rem;font-weight:600;background:#e0e7ff;color:#3730a3}
.soap-doc-footer{display:flex;justify-content:space-between;align-items:flex-end;padding:1.5rem 2rem;border-top:2px solid #e2e8f0;gap:2rem}
.soap-doc-sig-label{font-size:.75rem;color:#64748b;font-weight:600;text-transform:uppercase}
.soap-doc-sig-line{width:220px;border-bottom:1px solid #94a3b8;padding-bottom:.25rem;margin-bottom:.35rem;font-style:italic;color:#1e293b;min-height:1.5rem}
.soap-doc-sig-name{font-size:.85rem;color:#1e293b;font-weight:600;margin-top:.2rem}.soap-doc-sig-title{font-size:.8rem;color:#64748b}
.soap-doc-stamp{text-align:right}.soap-doc-stamp-date{font-size:.82rem;color:#64748b}
.soap-doc-approved-badge{display:inline-flex;align-items:center;gap:.3rem;margin-top:.35rem;padding:.3rem .8rem;border-radius:6px;background:#dcfce7;color:#166534;font-size:.78rem;font-weight:700;text-transform:uppercase}
</style></head><body>${doc.innerHTML}</body></html>`;

    downloadFile(html, 'Clinical_Report.html', 'text/html');
    showToast('HTML file downloaded.', 'success');
}

function downloadFile(content, filename, mime) {
    const blob = new Blob([content], { type: mime + ';charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function printReport() {
    document.getElementById('print-soap-document').innerHTML = document.getElementById('soap-document').innerHTML;
    window.print();
}


// ── Utils ────────────────────────────────────────────────────
function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

function startOver() {
    Object.assign(state, {
        currentStep: 1, sessionId: null, patientInput: '', uploadedFiles: [],
        approvedSummary: '', recommendedSpecialists: [], selectedSpecialists: [],
        aiReasoning: '', assessments: [], aggregatedSummary: '',
        conditions: [], medications: [], conditionCodes: [], medicationCodes: [],
        soapNote: '', originalSoapNote: '', finalReport: null
    });

    document.getElementById('patient-input').value = '';
    document.getElementById('char-count').textContent = '0 characters';
    document.getElementById('top-k-slider').value = 3;
    document.getElementById('top-k-value').textContent = '3';
    document.getElementById('patient-name').value = '';
    document.getElementById('patient-id').value = '';
    document.getElementById('patient-dob').value = '';
    document.getElementById('approving-physician').value = '';
    document.getElementById('physician-title').value = '';
    document.getElementById('file-list').innerHTML = '';

    goToStep(1);
    showToast('New patient session started.', 'info');
}
