// Configuration
const DEFAULT_BACKEND_URL = 'http://127.0.0.1:8000';
const CONFIG_KEY = 'cyberguardian_backend_url';

// State
let currentMode = 'url';

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
  loadConfiguration();
  attachEventListeners();
  loadCurrentTabUrl();
});

// Load backend configuration from storage
function loadConfiguration() {
  chrome.storage.local.get([CONFIG_KEY], (result) => {
    const url = result[CONFIG_KEY] || DEFAULT_BACKEND_URL;
    const backendInput = document.getElementById('backendUrl');
    if (backendInput) backendInput.value = url;
  });
}

// Save configuration with validation
function saveConfiguration() {
  const urlInput = document.getElementById('backendUrl');
  const statusEl = document.getElementById('configStatus');
  const url = urlInput.value.trim();

  if (!url) {
    showConfigStatus('Backend URL cannot be empty.', 'error');
    return;
  }

  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    showConfigStatus('URL must start with http:// or https://', 'error');
    return;
  }

  chrome.storage.local.set({ [CONFIG_KEY]: url }, () => {
    showConfigStatus('Settings saved successfully.', 'success');
    showStatus('Backend configuration updated', 'success');
    setTimeout(() => {
      hideConfigStatus();
      hideStatus();
    }, 2500);
  });
}

// Test backend connectivity
async function testBackendConnection() {
  const url = getBackendUrl();
  showConfigStatus('Pinging backend...', 'info');

  try {
    const response = await fetch(`${url}/`, { method: 'GET' });
    if (response.ok) {
      showConfigStatus('Connection successful! CyberGuardian backend is online.', 'success');
    } else {
      showConfigStatus(`Backend responded with HTTP ${response.status}`, 'error');
    }
  } catch (error) {
    showConfigStatus(`Cannot connect: ${error.message}. Ensure backend is running.`, 'error');
  }
}

function showConfigStatus(message, type) {
  const statusEl = document.getElementById('configStatus');
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.className = `config-status show ${type}`;
}

function hideConfigStatus() {
  const statusEl = document.getElementById('configStatus');
  if (!statusEl) return;
  statusEl.className = 'config-status';
}

// Get backend URL
function getBackendUrl() {
  const el = document.getElementById('backendUrl');
  return (el && el.value.trim()) || DEFAULT_BACKEND_URL;
}

// Load current tab URL into URL input
function loadCurrentTabUrl() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs.length > 0 && tabs[0].url) {
      const url = tabs[0].url;
      if (url.startsWith('http://') || url.startsWith('https://')) {
        const urlInput = document.getElementById('urlInput');
        if (urlInput) urlInput.value = url;
      }
    }
  });
}

// Switch between Main Scanners and Settings views
function setView(viewName) {
  const mainScanners = document.getElementById('mainScanners');
  const settingsView = document.getElementById('settingsView');

  if (viewName === 'settings') {
    mainScanners.classList.add('hidden');
    settingsView.classList.remove('hidden');
    const backendInput = document.getElementById('backendUrl');
    if (backendInput) {
      backendInput.focus();
      backendInput.select();
    }
  } else {
    settingsView.classList.add('hidden');
    mainScanners.classList.remove('hidden');
    hideConfigStatus();
  }
}

// Attach event listeners
function attachEventListeners() {
  // Mode selector buttons (URL, Message, Password, Media)
  document.querySelectorAll('.mode-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const targetBtn = e.target.closest('.mode-btn');
      if (targetBtn && targetBtn.dataset.mode) {
        switchMode(targetBtn.dataset.mode);
      }
    });
  });

  // Action buttons
  document.getElementById('analyzeUrlBtn').addEventListener('click', analyzeUrl);
  document.getElementById('analyzeMessageBtn').addEventListener('click', analyzeMessage);
  document.getElementById('analyzePasswordBtn').addEventListener('click', analyzePassword);
  document.getElementById('analyzeDeepfakeBtn').addEventListener('click', analyzeDeepfake);

  // Password visibility toggle
  const togglePassBtn = document.getElementById('togglePasswordBtn');
  if (togglePassBtn) {
    togglePassBtn.addEventListener('click', () => {
      const passInput = document.getElementById('passwordInput');
      if (passInput) {
        const isPassword = passInput.type === 'password';
        passInput.type = isPassword ? 'text' : 'password';
        togglePassBtn.textContent = isPassword ? '🙈' : '👁️';
      }
    });
  }

  // File selected info for deepfake
  const deepfakeInput = document.getElementById('deepfakeInput');
  if (deepfakeInput) {
    deepfakeInput.addEventListener('change', () => {
      const infoEl = document.getElementById('fileSelectedInfo');
      if (deepfakeInput.files && deepfakeInput.files.length > 0) {
        const file = deepfakeInput.files[0];
        const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
        infoEl.textContent = `Selected: ${file.name} (${sizeMb} MB)`;
        infoEl.style.color = '#86efac';
      } else {
        infoEl.textContent = 'Supports JPG, PNG, WEBP, MP4, WEBM (Max 10MB)';
        infoEl.style.color = '';
      }
    });
  }

  // Results close button
  document.getElementById('closeResults').addEventListener('click', hideResults);

  // Settings view navigation
  const settingsLink = document.getElementById('settingsLink');
  if (settingsLink) {
    settingsLink.addEventListener('click', (e) => {
      e.preventDefault();
      setView('settings');
    });
  }

  const backBtn = document.getElementById('backFromSettingsBtn');
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      setView('scanners');
    });
  }

  // Settings save & test connection
  document.getElementById('saveConfig').addEventListener('click', saveConfiguration);
  const testConnBtn = document.getElementById('testConnectionBtn');
  if (testConnBtn) {
    testConnBtn.addEventListener('click', testBackendConnection);
  }

  document.getElementById('backendUrl').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') saveConfiguration();
  });

  // Keyboard Enter handlers for inputs
  document.getElementById('urlInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') analyzeUrl();
  });

  document.getElementById('messageInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) analyzeMessage();
  });

  document.getElementById('passwordInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') analyzePassword();
  });
}

// Switch analysis mode tab
function switchMode(mode) {
  currentMode = mode;

  // Update tab buttons
  document.querySelectorAll('.mode-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });

  // Update panels
  const panels = {
    url: document.getElementById('urlPanel'),
    message: document.getElementById('messagePanel'),
    password: document.getElementById('passwordPanel'),
    deepfake: document.getElementById('deepfakePanel'),
  };

  Object.entries(panels).forEach(([name, panel]) => {
    if (panel) {
      panel.classList.toggle('active', name === mode);
    }
  });

  hideStatus();
}

// Status message bar in header
function showStatus(message, type = 'info') {
  const status = document.getElementById('status');
  status.textContent = message;
  status.className = `status show ${type}`;
}

function hideStatus() {
  const status = document.getElementById('status');
  status.className = 'status';
}

// Set button loading state
function setAnalyzeButtonLoading(mode, loading) {
  const config = {
    url: { btn: 'analyzeUrlBtn', spinner: 'urlSpinner' },
    message: { btn: 'analyzeMessageBtn', spinner: 'messageSpinner' },
    password: { btn: 'analyzePasswordBtn', spinner: 'passwordSpinner' },
    deepfake: { btn: 'analyzeDeepfakeBtn', spinner: 'deepfakeSpinner' },
  };

  const item = config[mode];
  if (!item) return;

  const btn = document.getElementById(item.btn);
  const spinner = document.getElementById(item.spinner);

  if (btn) btn.disabled = loading;
  if (spinner) spinner.classList.toggle('hidden', !loading);
}

// ── Background & Direct API Execution Helpers ─────────────────────────────────

function executeAnalyzeUrl(url, backendUrl) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ action: 'analyzeUrl', url, backendUrl }, (response) => {
      if (chrome.runtime.lastError) {
        fetch(`${backendUrl}/security/analyze-url`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url }),
        })
          .then(async (resp) => {
            if (!resp.ok) {
              const err = await resp.json().catch(() => ({}));
              reject(new Error(err.detail || `HTTP ${resp.status}`));
            } else {
              resolve(await resp.json());
            }
          })
          .catch(reject);
      } else if (!response || !response.success) {
        reject(new Error(response?.error || 'Analysis failed'));
      } else {
        resolve(response.data);
      }
    });
  });
}

function executeAnalyzeMessage(message, backendUrl) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ action: 'analyzeMessage', message, backendUrl }, (response) => {
      if (chrome.runtime.lastError) {
        fetch(`${backendUrl}/security/analyze-message`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message }),
        })
          .then(async (resp) => {
            if (!resp.ok) {
              const err = await resp.json().catch(() => ({}));
              reject(new Error(err.detail || `HTTP ${resp.status}`));
            } else {
              resolve(await resp.json());
            }
          })
          .catch(reject);
      } else if (!response || !response.success) {
        reject(new Error(response?.error || 'Analysis failed'));
      } else {
        resolve(response.data);
      }
    });
  });
}

function executeAnalyzePassword(password, backendUrl) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ action: 'analyzePassword', password, backendUrl }, (response) => {
      if (chrome.runtime.lastError) {
        fetch(`${backendUrl}/security/analyze-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password }),
        })
          .then(async (resp) => {
            if (!resp.ok) {
              const err = await resp.json().catch(() => ({}));
              reject(new Error(err.detail || `HTTP ${resp.status}`));
            } else {
              resolve(await resp.json());
            }
          })
          .catch(reject);
      } else if (!response || !response.success) {
        reject(new Error(response?.error || 'Analysis failed'));
      } else {
        resolve(response.data);
      }
    });
  });
}

async function executeAnalyzeDeepfake(file, backendUrl) {
  // Sanitize filename for backend requirements (^[a-zA-Z0-9._-]+$)
  const safeName = file.name.replace(/\s+/g, '_').replace(/[^a-zA-Z0-9._\-]/g, '');
  const cleanFile = new File([file], safeName || 'upload.png', { type: file.type });

  const formData = new FormData();
  formData.append('file', cleanFile);

  const response = await fetch(`${backendUrl}/security/analyze-deepfake`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return await response.json();
}

// ── Handlers ──────────────────────────────────────────────────────────────────

async function analyzeUrl() {
  const urlInput = document.getElementById('urlInput');
  const url = urlInput.value.trim();

  if (!url) {
    showStatus('Please enter a URL to analyze.', 'error');
    return;
  }

  try {
    new URL(url);
  } catch {
    showStatus('Invalid URL format. Please include http:// or https://', 'error');
    return;
  }

  setAnalyzeButtonLoading('url', true);
  hideResults();

  try {
    const backendUrl = getBackendUrl();
    const result = await executeAnalyzeUrl(url, backendUrl);
    displayUrlResult(result, url);
    showStatus('URL analysis complete', 'success');
  } catch (error) {
    console.error('URL analysis error:', error);
    showStatus(`Scan failed: ${error.message}`, 'error');
  } finally {
    setAnalyzeButtonLoading('url', false);
  }
}

async function analyzeMessage() {
  const messageInput = document.getElementById('messageInput');
  const message = messageInput.value.trim();

  if (!message) {
    showStatus('Please enter message text to inspect.', 'error');
    return;
  }

  setAnalyzeButtonLoading('message', true);
  hideResults();

  try {
    const backendUrl = getBackendUrl();
    const result = await executeAnalyzeMessage(message, backendUrl);
    displayMessageResult(result, message);
    showStatus('Message analysis complete', 'success');
  } catch (error) {
    console.error('Message analysis error:', error);
    showStatus(`Scan failed: ${error.message}`, 'error');
  } finally {
    setAnalyzeButtonLoading('message', false);
  }
}

async function analyzePassword() {
  const passwordInput = document.getElementById('passwordInput');
  const password = passwordInput.value;

  if (!password) {
    showStatus('Please enter a password to evaluate.', 'error');
    return;
  }

  // Clear immediately from DOM to ensure safety
  passwordInput.value = '';

  setAnalyzeButtonLoading('password', true);
  hideResults();

  try {
    const backendUrl = getBackendUrl();
    const result = await executeAnalyzePassword(password, backendUrl);
    displayPasswordResult(result);
    showStatus('Password evaluation complete', 'success');
  } catch (error) {
    console.error('Password analysis error:', error);
    showStatus(`Scan failed: ${error.message}`, 'error');
  } finally {
    setAnalyzeButtonLoading('password', false);
  }
}

async function analyzeDeepfake() {
  const fileInput = document.getElementById('deepfakeInput');
  if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
    showStatus('Please select an image or video file.', 'error');
    return;
  }

  const file = fileInput.files[0];
  const maxBytes = 10 * 1024 * 1024;
  if (file.size > maxBytes) {
    showStatus(`File too large (${(file.size / (1024 * 1024)).toFixed(1)} MB). Limit is 10 MB.`, 'error');
    return;
  }

  setAnalyzeButtonLoading('deepfake', true);
  hideResults();

  try {
    const backendUrl = getBackendUrl();
    const result = await executeAnalyzeDeepfake(file, backendUrl);
    displayDeepfakeResult(result);
    showStatus('Media forensic scan complete', 'success');
  } catch (error) {
    console.error('Media analysis error:', error);
    showStatus(`Media scan failed: ${error.message}`, 'error');
  } finally {
    setAnalyzeButtonLoading('deepfake', false);
  }
}

// ── Results Renderers ─────────────────────────────────────────────────────────

function resetResultsUI() {
  const resultsPanel = document.getElementById('results');
  resultsPanel.classList.remove('hidden');
  resultsPanel.classList.add('active');

  // Hide sub-sections by default
  document.getElementById('detailsSection').classList.add('hidden');
  document.getElementById('recommendationsSection').classList.add('hidden');
  document.getElementById('featuresSection').classList.add('hidden');
  document.getElementById('psychologySection').classList.add('hidden');
  document.getElementById('errorMessage').classList.add('hidden');

  // Clear lists
  document.getElementById('feedbackList').innerHTML = '';
  document.getElementById('recommendationsList').innerHTML = '';
  document.getElementById('featuresList').innerHTML = '';
  document.getElementById('psychologyList').innerHTML = '';
  document.getElementById('detailsContent').innerHTML = '';
}

function displayUrlResult(result, url) {
  resetResultsUI();

  document.getElementById('resultTitle').textContent = 'URL Threat Assessment';
  document.getElementById('feedbackHeading').textContent = 'Risk Signals & Findings';

  const score = typeof result.risk_score === 'number' ? result.risk_score : 0;
  const prediction = result.prediction || 'Unknown';

  document.getElementById('riskScore').textContent = score;
  document.getElementById('scoreUnit').textContent = '/100';

  const riskCatEl = document.getElementById('riskCategory');
  riskCatEl.textContent = prediction;
  const catSlug = prediction.toLowerCase().replace(/[^a-z0-9]/g, '-');
  riskCatEl.className = `risk-category ${catSlug}`;

  const scoreBar = document.getElementById('scoreBar');
  scoreBar.style.width = `${Math.min(100, score)}%`;

  // Feedback list
  const feedbackList = document.getElementById('feedbackList');
  if (result.feedback && result.feedback.length > 0) {
    result.feedback.forEach((item) => {
      const li = document.createElement('li');
      li.textContent = item;
      feedbackList.appendChild(li);
    });
  } else {
    const li = document.createElement('li');
    li.textContent = 'No obvious threat indicators detected.';
    feedbackList.appendChild(li);
  }

  // Features list
  if (result.features && Object.keys(result.features).length > 0) {
    const featuresSection = document.getElementById('featuresSection');
    featuresSection.classList.remove('hidden');
    const featuresList = document.getElementById('featuresList');
    Object.entries(result.features).forEach(([name, value]) => {
      const statusClass = value === -1 ? 'threat' : value === 0 ? 'suspicious' : 'safe';
      const div = document.createElement('div');
      div.className = `feature-badge ${statusClass}`;
      div.textContent = name.replace(/_/g, ' ');
      featuresList.appendChild(div);
    });
  }

  // Scam psychology triggers
  renderPsychologySection(result.scam_psychology);

  scrollToResults();
}

function displayMessageResult(result, message) {
  resetResultsUI();

  document.getElementById('resultTitle').textContent = 'Message Threat Assessment';
  document.getElementById('feedbackHeading').textContent = 'Detected Deception Signals';

  const score = typeof result.risk_score === 'number' ? result.risk_score : 0;
  const prediction = result.prediction || 'Unknown';

  document.getElementById('riskScore').textContent = score;
  document.getElementById('scoreUnit').textContent = '/100';

  const riskCatEl = document.getElementById('riskCategory');
  riskCatEl.textContent = prediction;
  const catSlug = prediction.toLowerCase().replace(/[^a-z0-9]/g, '-');
  riskCatEl.className = `risk-category ${catSlug}`;

  const scoreBar = document.getElementById('scoreBar');
  scoreBar.style.width = `${Math.min(100, score)}%`;

  // Feedback
  const feedbackList = document.getElementById('feedbackList');
  if (result.feedback && result.feedback.length > 0) {
    result.feedback.forEach((item) => {
      const li = document.createElement('li');
      li.textContent = item;
      feedbackList.appendChild(li);
    });
  } else {
    const li = document.createElement('li');
    li.textContent = 'No deceptive patterns or threats identified in this message.';
    feedbackList.appendChild(li);
  }

  // Psychology triggers
  renderPsychologySection(result.scam_psychology);

  scrollToResults();
}

function displayPasswordResult(result) {
  resetResultsUI();

  document.getElementById('resultTitle').textContent = 'Password Strength Assessment';
  document.getElementById('feedbackHeading').textContent = 'Entropy & Security Findings';

  const score = typeof result.score === 'number' ? result.score : 0;
  const strength = result.strength || 'Unknown';

  document.getElementById('riskScore').textContent = score;
  document.getElementById('scoreUnit').textContent = '/100';

  const riskCatEl = document.getElementById('riskCategory');
  riskCatEl.textContent = strength;
  const strengthSlug = strength.toLowerCase().replace(/[^a-z0-9]/g, '-');
  riskCatEl.className = `risk-category ${strengthSlug}`;

  const scoreBar = document.getElementById('scoreBar');
  scoreBar.style.width = `${Math.min(100, score)}%`;

  // Details section: crack time, entropy, length
  const detailsSection = document.getElementById('detailsSection');
  detailsSection.classList.remove('hidden');
  const detailsContent = document.getElementById('detailsContent');

  const crackTime = result.crack_time_estimate?.text || 'Standard brute-force resistant';
  const entropy = result.entropy_estimate ? `${Math.round(result.entropy_estimate)} bits` : 'Standard';
  const length = result.length ? `${result.length} chars` : 'Analyzed';

  detailsContent.innerHTML = `
    <div class="details-item">
      <span class="details-label">Crack Time</span>
      <span class="details-val">${escapeHtml(crackTime)}</span>
    </div>
    <div class="details-item">
      <span class="details-label">Entropy</span>
      <span class="details-val">${escapeHtml(entropy)}</span>
    </div>
    <div class="details-item">
      <span class="details-label">Length</span>
      <span class="details-val">${escapeHtml(length)}</span>
    </div>
    <div class="details-item">
      <span class="details-label">Common Pwd</span>
      <span class="details-val">${result.common_password ? '⚠️ Yes (Known)' : '✅ No'}</span>
    </div>
  `;

  // Feedback
  const feedbackList = document.getElementById('feedbackList');
  if (result.feedback && result.feedback.length > 0) {
    result.feedback.forEach((item) => {
      const li = document.createElement('li');
      li.textContent = item;
      feedbackList.appendChild(li);
    });
  }

  // Recommendations
  if (result.recommendations && result.recommendations.length > 0) {
    const recSection = document.getElementById('recommendationsSection');
    recSection.classList.remove('hidden');
    const recList = document.getElementById('recommendationsList');
    result.recommendations.forEach((rec) => {
      const li = document.createElement('li');
      li.textContent = `💡 ${rec}`;
      recList.appendChild(li);
    });
  }

  scrollToResults();
}

function displayDeepfakeResult(result) {
  resetResultsUI();

  document.getElementById('resultTitle').textContent = 'Forensic Media Assessment';
  document.getElementById('feedbackHeading').textContent = 'Forensic Indicators';

  const score = typeof result.risk_score === 'number' ? result.risk_score : 0;
  const prediction = result.prediction || 'Unknown';

  document.getElementById('riskScore').textContent = score;
  document.getElementById('scoreUnit').textContent = '/100';

  const riskCatEl = document.getElementById('riskCategory');
  riskCatEl.textContent = prediction;
  const catSlug = prediction.toLowerCase().replace(/[^a-z0-9]/g, '-');
  riskCatEl.className = `risk-category ${catSlug}`;

  const scoreBar = document.getElementById('scoreBar');
  scoreBar.style.width = `${Math.min(100, score)}%`;

  // Media details
  const detailsSection = document.getElementById('detailsSection');
  detailsSection.classList.remove('hidden');
  const detailsContent = document.getElementById('detailsContent');

  const fileName = result.file_name || 'Uploaded Media';
  const fileType = result.file_type || 'image';
  const fileSize = result.metadata?.file_size_bytes
    ? `${Math.round(result.metadata.file_size_bytes / 1024)} KB`
    : 'Analyzed';

  detailsContent.innerHTML = `
    <div class="details-item">
      <span class="details-label">File</span>
      <span class="details-val">${escapeHtml(fileName)}</span>
    </div>
    <div class="details-item">
      <span class="details-label">Format</span>
      <span class="details-val">${escapeHtml(fileType.toUpperCase())}</span>
    </div>
    <div class="details-item">
      <span class="details-label">Size</span>
      <span class="details-val">${escapeHtml(fileSize)}</span>
    </div>
    <div class="details-item">
      <span class="details-label">Verdict</span>
      <span class="details-val">${escapeHtml(prediction)}</span>
    </div>
  `;

  // Feedback list
  const feedbackList = document.getElementById('feedbackList');
  if (result.feedback && result.feedback.length > 0) {
    result.feedback.forEach((item) => {
      const li = document.createElement('li');
      li.textContent = item;
      feedbackList.appendChild(li);
    });
  } else {
    const li = document.createElement('li');
    li.textContent = 'No synthetic manipulation or deepfake anomalies identified.';
    feedbackList.appendChild(li);
  }

  scrollToResults();
}

function renderPsychologySection(psychology) {
  if (psychology && psychology.scores) {
    const scores = psychology.scores;
    const hasSignals = Object.values(scores).some((v) => v > 0);

    if (hasSignals) {
      const psychologySection = document.getElementById('psychologySection');
      psychologySection.classList.remove('hidden');
      const psychologyList = document.getElementById('psychologyList');
      psychologyList.innerHTML = '';

      Object.entries(scores).forEach(([trigger, score]) => {
        if (score > 0) {
          const div = document.createElement('div');
          div.className = 'psychology-item';
          const label = trigger.charAt(0).toUpperCase() + trigger.slice(1);
          div.innerHTML = `
            <span>${escapeHtml(label)} Pressure</span>
            <div style="display: flex; gap: 6px; align-items: center;">
              <strong>${score}%</strong>
              <div class="psychology-bar">
                <div class="psychology-bar-fill" style="width: ${score}%"></div>
              </div>
            </div>
          `;
          psychologyList.appendChild(div);
        }
      });
    }
  }
}

function scrollToResults() {
  const resultsPanel = document.getElementById('results');
  setTimeout(() => {
    resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, 100);
}

function hideResults() {
  const resultsPanel = document.getElementById('results');
  resultsPanel.classList.remove('active');
  resultsPanel.classList.add('hidden');
}

function escapeHtml(text) {
  if (typeof text !== 'string') return String(text ?? '');
  return text.replace(/[&<>"']/g, (m) => {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
  });
}
