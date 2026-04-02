/* ============================================================
   app.js — Convertly (Secure Version)
   Handles: file selection, drag & drop, API call,
   progress animation, result/error display, stats counter.
   ============================================================ */


// ── CONFIGURATION ────────────────────────────────────────────
// Change this to your deployed server URL when you go live.
const API_URL = 'http://localhost:5000/convert';
const STATS_URL = 'http://localhost:5000/stats';


// ── FILE TYPE ICONS ──────────────────────────────────────────
const FILE_ICONS = {
  pdf: '📕',
  docx: '📘', doc: '📘',
  pptx: '📙', ppt: '📙',
  xlsx: '📗', xls: '📗',
  jpg: '🖼️', jpeg: '🖼️', png: '🖼️', webp: '🖼️', gif: '🖼️',
  html: '🌐', htm: '🌐',
  txt: '📝',
};


// ── STATE ────────────────────────────────────────────────────
let selectedFile = null;


// ── DOM ELEMENTS ─────────────────────────────────────────────
const dropZone      = document.getElementById('dropZone');
const fileInput     = document.getElementById('fileInput');
const fileInfo      = document.getElementById('fileInfo');
const fileIconBox   = document.getElementById('fileIconBox');
const fileNameEl    = document.getElementById('fileName');
const fileSizeEl    = document.getElementById('fileSize');
const fileRemove    = document.getElementById('fileRemove');
const fromFormat    = document.getElementById('fromFormat');
const toFormat      = document.getElementById('toFormat');
const btnConvert    = document.getElementById('btnConvert');
const progressWrap  = document.getElementById('progressWrap');
const progressFill  = document.getElementById('progressFill');
const progressLabel = document.getElementById('progressLabel');
const resultEl      = document.getElementById('result');
const resultName    = document.getElementById('resultName');
const resultMeta    = document.getElementById('resultMeta');
const btnDownload   = document.getElementById('btnDownload');
const errorMsg      = document.getElementById('errorMsg');
const convCounter   = document.getElementById('conversionCounter');


// ── UTILITIES ────────────────────────────────────────────────

function getExtension(filename) {
  return filename.includes('.') ? filename.split('.').pop().toLowerCase() : '';
}

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1024 / 1024).toFixed(1) + ' MB';
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function easeInOut(t) {
  return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
}


// ── STATS COUNTER ────────────────────────────────────────────
// Fetches total conversions from the backend and shows in footer

async function loadStats() {
  if (!convCounter) return;
  try {
    const res = await fetch(STATS_URL);
    if (!res.ok) return;
    const data = await res.json();
    const count = data.conversions || 0;
    // Only show if there are conversions to display
    if (count > 0) {
      convCounter.textContent = `⚡ ${count.toLocaleString()} files converted · `;
    }
  } catch {
    // Silently fail — stats are not critical
    convCounter.textContent = '';
  }
}

// Load stats when page opens
loadStats();


// ── FILE HANDLING ────────────────────────────────────────────

function handleFile(file) {
  selectedFile = file;

  const ext = getExtension(file.name);
  fileIconBox.textContent = FILE_ICONS[ext] || '📄';
  fileNameEl.textContent = file.name;
  fileSizeEl.textContent = formatSize(file.size);

  fileInfo.classList.add('visible');
  btnConvert.disabled = false;

  // Auto-select "From" format based on file extension
  const match = [...fromFormat.options].find(o =>
    o.value === ext || (ext === 'jpeg' && o.value === 'jpg')
  );
  if (match) fromFormat.value = match.value;

  // Clear any previous state
  hideResult();
  hideError();
  hideProgress();
}

function clearFile() {
  selectedFile = null;
  fileInput.value = '';
  fileInfo.classList.remove('visible');
  btnConvert.disabled = true;
  hideResult();
  hideError();
  hideProgress();
}


// ── DRAG AND DROP ────────────────────────────────────────────

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

fileInput.addEventListener('change', (e) => {
  if (e.target.files[0]) handleFile(e.target.files[0]);
});

fileRemove.addEventListener('click', clearFile);


// ── PROGRESS BAR ─────────────────────────────────────────────

function showProgress(pct, label) {
  progressWrap.classList.add('visible');
  progressFill.style.width = pct + '%';
  progressLabel.textContent = label;
}

function hideProgress() {
  progressWrap.classList.remove('visible');
  progressFill.style.width = '0%';
}

function animateProgress(from, to, durationMs, label) {
  progressLabel.textContent = label;
  const start = performance.now();

  function step(now) {
    const t = Math.min((now - start) / durationMs, 1);
    progressFill.style.width = (from + (to - from) * easeInOut(t)) + '%';
    if (t < 1) requestAnimationFrame(step);
  }

  requestAnimationFrame(step);
}


// ── RESULT / ERROR ───────────────────────────────────────────

function showResult(filename, size) {
  resultName.textContent = filename;
  // Confirm to the user that the file was deleted server-side
  resultMeta.textContent = formatSize(size) + ' · File deleted from server ✓';
  resultEl.classList.add('visible');
}

function hideResult() { resultEl.classList.remove('visible'); }

function showError(message) {
  errorMsg.textContent = '⚠️ ' + message;
  errorMsg.classList.add('visible');
}

function hideError() { errorMsg.classList.remove('visible'); }


// ── CONVERT ──────────────────────────────────────────────────

btnConvert.addEventListener('click', async () => {
  if (!selectedFile) return;

  const targetFormat = toFormat.value;

  // Reset UI state
  hideResult();
  hideError();
  showProgress(0, 'Preparing…');
  btnConvert.disabled = true;

  // Build the multipart request (file + target format)
  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('to', targetFormat);

  try {
    // Phase 1: Upload
    animateProgress(0, 40, 800, 'Uploading file securely…');

    const response = await fetch(API_URL, {
      method: 'POST',
      body: formData,
    });

    // Phase 2: Converting
    animateProgress(40, 85, 700, 'Converting…');

    // Check for server-side errors
    if (!response.ok) {
      const errData = await response.json().catch(() => ({
        error: `Server error (${response.status})`
      }));
      throw new Error(errData.error);
    }

    // Phase 3: Finishing
    animateProgress(85, 100, 300, 'Almost done…');

    // Read the converted file as a binary blob
    const blob = await response.blob();

    // Create a temporary browser download URL
    const downloadUrl = URL.createObjectURL(blob);
    const outputFilename = selectedFile.name.replace(/\.[^.]+$/, '') + '.' + targetFormat;

    // Wire up the download button
    btnDownload.href = downloadUrl;
    btnDownload.download = outputFilename;

    // Brief pause so user sees 100%
    await delay(350);

    hideProgress();
    showResult(outputFilename, blob.size);

    // Refresh the stats counter after a successful conversion
    loadStats();

  } catch (err) {
    hideProgress();
    showError(err.message || 'Something went wrong. Is the backend server running?');
  } finally {
    btnConvert.disabled = false;
  }
});
