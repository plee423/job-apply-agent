// Side panel UI logic

const $ = id => document.getElementById(id);
const show = id => $$(id).classList.remove('hidden');
const hide = id => $$(id).classList.add('hidden');

function $$(id) {
  const el = typeof id === 'string' ? document.getElementById(id) : id;
  if (!el) console.warn('Element not found:', id);
  return el;
}

// State
let streamBuffer = '';
let isGenerating = false;

// ── Init ──────────────────────────────────────────────────────────────────

async function init() {
  const storage = await chrome.storage.local.get(['apiKey']);
  if (!storage.apiKey) {
    showState('setup');
    return;
  }

  showState('input');
  checkForJobData();
  setupEventListeners();
}

function showState(state) {
  ['input', 'loading', 'results', 'error', 'setup'].forEach(s => {
    $(`${s}-section`)?.classList.toggle('hidden', s !== state);
  });
}

// ── Event Listeners ───────────────────────────────────────────────────────

function setupEventListeners() {
  $('btn-generate').addEventListener('click', generate);
  $('btn-regenerate').addEventListener('click', () => { showState('input'); });
  $('btn-retry').addEventListener('click', generate);
  $('btn-settings').addEventListener('click', () => chrome.runtime.openOptionsPage());
  $('btn-open-settings').addEventListener('click', () => chrome.runtime.openOptionsPage());
  $('btn-select-all').addEventListener('click', () => setAllChecked(true));
  $('btn-select-none').addEventListener('click', () => setAllChecked(false));
  $('btn-use-detected').addEventListener('click', useDetectedJob);

  // Listen for messages from background (streamed chunks)
  chrome.runtime.onMessage.addListener(handleBackgroundMessage);
}

function setAllChecked(checked) {
  document.querySelectorAll('.content-types input[type="checkbox"]')
    .forEach(cb => cb.checked = checked);
}

// ── Job Detection ─────────────────────────────────────────────────────────

async function checkForJobData() {
  const response = await chrome.runtime.sendMessage({ type: 'GET_LATEST_JOB' });
  if (response?.payload?.description) {
    showJobBanner(response.payload);
  }
}

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === 'JOB_DATA_READY' && message.payload?.description) {
    showJobBanner(message.payload);
  }
});

function showJobBanner(job) {
  $('job-title').textContent = job.title || 'Job detected';
  $('job-company').textContent = job.company || '';
  $('job-banner').classList.remove('hidden');
  $('job-banner').dataset.job = JSON.stringify(job);
}

function useDetectedJob() {
  const job = JSON.parse($('job-banner').dataset.job || '{}');
  const parts = [];
  if (job.title) parts.push(`Role: ${job.title}`);
  if (job.company) parts.push(`Company: ${job.company}`);
  if (job.url) parts.push(`URL: ${job.url}`);
  if (job.description) parts.push(`\n${job.description}`);
  $('job-input').value = parts.join('\n');
  $('job-banner').classList.add('hidden');
}

// ── Generate ──────────────────────────────────────────────────────────────

function getSelectedTypes() {
  return Array.from(document.querySelectorAll('.content-types input[type="checkbox"]:checked'))
    .map(cb => cb.value);
}

async function generate() {
  if (isGenerating) return;

  const jobText = $('job-input').value.trim();
  if (!jobText) {
    $('job-input').focus();
    return;
  }

  const contentTypes = getSelectedTypes();
  if (contentTypes.length === 0) {
    alert('Select at least one content type.');
    return;
  }

  const storage = await chrome.storage.local.get(['model']);
  const model = storage.model || 'claude-sonnet-4-6';

  isGenerating = true;
  streamBuffer = '';
  showState('loading');
  $('stream-preview').textContent = '';

  chrome.runtime.sendMessage({
    type: 'GENERATE',
    payload: { jobText, contentTypes, model },
  });
}

function handleBackgroundMessage(message) {
  if (message.type === 'STREAM_CHUNK') {
    streamBuffer += message.text;
    // Show last 500 chars of stream in preview
    $('stream-preview').textContent = streamBuffer.slice(-500);
    $('stream-preview').scrollTop = $('stream-preview').scrollHeight;
  }

  if (message.type === 'STREAM_DONE') {
    isGenerating = false;
    renderResults(streamBuffer);
  }

  if (message.type === 'ERROR') {
    isGenerating = false;
    $('error-message').textContent = message.message;
    showState('error');
  }
}

// ── Results Rendering ─────────────────────────────────────────────────────

function renderResults(rawText) {
  const sections = parseOutputSections(rawText);
  const container = $('results-container');
  container.innerHTML = '';

  if (sections.length === 0) {
    // Fallback: show raw output in one card
    container.appendChild(createResultCard('Full Output', rawText, false));
  } else {
    sections.forEach(({ title, content }) => {
      container.appendChild(createResultCard(title, content));
    });
  }

  showState('results');
}

function parseOutputSections(text) {
  const sections = [];
  const lines = text.split('\n');
  let currentTitle = null;
  let currentLines = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('═══') && !trimmed.includes('END')) {
      if (currentTitle !== null) {
        sections.push({ title: currentTitle, content: currentLines.join('\n').trim() });
      }
      currentTitle = trimmed.replace(/═══/g, '').trim();
      currentLines = [];
    } else if (trimmed.startsWith('═══') && trimmed.includes('END')) {
      if (currentTitle !== null) {
        sections.push({ title: currentTitle, content: currentLines.join('\n').trim() });
        currentTitle = null;
        currentLines = [];
      }
    } else if (currentTitle !== null) {
      currentLines.push(line);
    }
  }

  // Catch any open section
  if (currentTitle !== null && currentLines.length) {
    sections.push({ title: currentTitle, content: currentLines.join('\n').trim() });
  }

  return sections;
}

function createResultCard(title, content, collapsed = false) {
  const card = document.createElement('div');
  card.className = `result-card${collapsed ? ' collapsed' : ''}`;

  card.innerHTML = `
    <div class="result-card-header">
      <span class="result-card-title">${escapeHtml(title)}</span>
      <div class="result-card-actions">
        <button class="btn-copy">Copy</button>
      </div>
      <span class="result-card-chevron">▾</span>
    </div>
    <div class="result-card-body">
      <div class="result-text">${escapeHtml(content)}</div>
    </div>
  `;

  // Toggle collapse
  card.querySelector('.result-card-header').addEventListener('click', (e) => {
    if (e.target.closest('.btn-copy')) return;
    card.classList.toggle('collapsed');
  });

  // Copy button
  const copyBtn = card.querySelector('.btn-copy');
  copyBtn.addEventListener('click', async (e) => {
    e.stopPropagation();
    await navigator.clipboard.writeText(content);
    copyBtn.textContent = 'Copied ✓';
    copyBtn.classList.add('copied');
    setTimeout(() => {
      copyBtn.textContent = 'Copy';
      copyBtn.classList.remove('copied');
    }, 2000);
  });

  return card;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Boot ──────────────────────────────────────────────────────────────────
init();
