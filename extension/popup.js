// Configuration
const DEFAULT_BACKEND_URL = 'http://127.0.0.1:8000';
const CONFIG_KEY = 'cyberguardian_backend_url';
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// State
let currentMode = 'url';
let analysisCache = {};

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
    document.getElementById('backendUrl').value = url;
  });
}

// Save configuration
function saveConfiguration() {
  const url = document.getElementById('backendUrl').value.trim();
  if (!url) {
    showStatus('Backend URL cannot be empty', 'error');
    return;
  }

  chrome.storage.local.set({ [CONFIG_KEY]: url }, () => {
    showStatus('Configuration saved', 'success');
    setTimeout(() => hideStatus(), 2000);
  });
}

// Get backend URL
function getBackendUrl() {
  return document.getElementById('backendUrl').value.trim() || DEFAULT_BACKEND_URL;
}

// Load current tab URL into URL input
function loadCurrentTabUrl() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs.length > 0 && tabs[0].url) {
      const url = tabs[0].url;
      // Only populate if it's a valid web URL
      if (url.startsWith('http://') || url.startsWith('https://')) {
        document.getElementById('urlInput').value = url;
      }
    }
  });
}

// Attach event listeners
function attachEventListeners() {
  // Mode selector
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', (e) => switchMode(e.target.closest('.mode-btn').dataset.mode));
  });

  // Analysis buttons
  document.getElementById('analyzeUrlBtn').addEventListener('click', () => analyzeUrl());
  document.getElementById('analyzeMessageBtn').addEventListener('click', () => analyzeMessage());

  // Results close
  document.getElementById('closeResults').addEventListener('click', () => hideResults());

  // Configuration
  document.getElementById('saveConfig').addEventListener('click', () => saveConfiguration());
  document.getElementById('backendUrl').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') saveConfiguration();
  });

  // Allow Enter to submit in input fields
  document.getElementById('urlInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') analyzeUrl();
  });

  document.getElementById('messageInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) analyzeMessage();
  });
}

// Switch analysis mode
function switchMode(mode) {
  currentMode = mode;

  // Update buttons
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });

  // Update panels
  document.getElementById('urlPanel').classList.toggle('active', mode === 'url');
  document.getElementById('messagePanel').classList.toggle('active', mode === 'message');
}

// Show status message
function showStatus(message, type = 'info') {
  const status = document.getElementById('status');
  status.textContent = message;
  status.className = `status show ${type}`;
}

function hideStatus() {
  const status = document.getElementById('status');
  status.classList.remove('show');
}

// Analyze URL
async function analyzeUrl() {
  const urlInput = document.getElementById('urlInput');
  const url = urlInput.value.trim();

  if (!url) {
    showStatus('Please enter a URL', 'error');
    return;
  }

  // Validate URL
  try {
    new URL(url);
  } catch {
    showStatus('Invalid URL format', 'error');
    return;
  }

  setAnalyzeButtonLoading('url', true);

  try {
    const backendUrl = getBackendUrl();
    const response = await fetch(`${backendUrl}/security/analyze-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }

    const result = await response.json();
    displayUrlResult(result, url);
    showStatus('Analysis complete', 'success');
  } catch (error) {
    console.error('Analysis error:', error);
    showStatus(`Error: ${error.message}`, 'error');
  } finally {
    setAnalyzeButtonLoading('url', false);
  }
}

// Analyze message
async function analyzeMessage() {
  const messageInput = document.getElementById('messageInput');
  const message = messageInput.value.trim();

  if (!message) {
    showStatus('Please enter text to analyze', 'error');
    return;
  }

  setAnalyzeButtonLoading('message', true);

  try {
    const backendUrl = getBackendUrl();
    const response = await fetch(`${backendUrl}/security/analyze-message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }

    const result = await response.json();
    displayMessageResult(result, message);
    showStatus('Analysis complete', 'success');
  } catch (error) {
    console.error('Analysis error:', error);
    showStatus(`Error: ${error.message}`, 'error');
  } finally {
    setAnalyzeButtonLoading('message', false);
  }
}

// Set button loading state
function setAnalyzeButtonLoading(mode, loading) {
  const btn = mode === 'url' ? document.getElementById('analyzeUrlBtn') : document.getElementById('analyzeMessageBtn');
  const spinner = mode === 'url' ? document.getElementById('urlSpinner') : document.getElementById('messageSpinner');

  btn.disabled = loading;
  spinner.classList.toggle('hidden', !loading);
}

// Display URL analysis result
function displayUrlResult(result, url) {
  const resultsPanel = document.getElementById('results');
  const resultTitle = document.getElementById('resultTitle');
  const riskScore = document.getElementById('riskScore');
  const riskCategory = document.getElementById('riskCategory');
  const scoreBar = document.getElementById('scoreBar');
  const feedbackList = document.getElementById('feedbackList');
  const featuresSection = document.getElementById('featuresSection');
  const featuresList = document.getElementById('featuresList');
  const psychologySection = document.getElementById('psychologySection');
  const psychologyList = document.getElementById('psychologyList');
  const errorMessage = document.getElementById('errorMessage');

  resultTitle.textContent = 'URL Analysis Result';

  const score = result.risk_score || 0;
  const prediction = result.prediction || 'Unknown';

  riskScore.textContent = score;
  riskCategory.textContent = prediction;
  riskCategory.className = `risk-category ${prediction.toLowerCase().replace('/', '-')}`;

  scoreBar.style.width = `${Math.min(100, score)}%`;

  // Feedback
  feedbackList.innerHTML = '';
  if (result.feedback && result.feedback.length > 0) {
    result.feedback.forEach(item => {
      const li = document.createElement('li');
      li.textContent = item;
      feedbackList.appendChild(li);
    });
  } else {
    const li = document.createElement('li');
    li.textContent = 'No risk signals detected.';
    feedbackList.appendChild(li);
  }

  // Features
  if (result.features && Object.keys(result.features).length > 0) {
    featuresSection.classList.remove('hidden');
    featuresList.innerHTML = '';
    Object.entries(result.features).forEach(([name, value]) => {
      const statusClass = value === -1 ? 'threat' : value === 0 ? 'suspicious' : 'safe';
      const div = document.createElement('div');
      div.className = `feature-badge ${statusClass}`;
      div.textContent = name.replace(/_/g, ' ');
      featuresList.appendChild(div);
    });
  } else {
    featuresSection.classList.add('hidden');
  }

  // Scam Psychology
  if (result.scam_psychology && result.scam_psychology.scores) {
    const scores = result.scam_psychology.scores;
    const hasSignals = Object.values(scores).some(v => v > 0);

    if (hasSignals) {
      psychologySection.classList.remove('hidden');
      psychologyList.innerHTML = '';
      Object.entries(scores).forEach(([trigger, score]) => {
        if (score > 0) {
          const div = document.createElement('div');
          div.className = 'psychology-item';
          const label = trigger.charAt(0).toUpperCase() + trigger.slice(1);
          div.innerHTML = `
            <span>${label} Bait</span>
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
    } else {
      psychologySection.classList.add('hidden');
    }
  } else {
    psychologySection.classList.add('hidden');
  }

  errorMessage.classList.remove('show');
  resultsPanel.classList.add('active');
}

// Display message analysis result
function displayMessageResult(result, message) {
  const resultsPanel = document.getElementById('results');
  const resultTitle = document.getElementById('resultTitle');
  const riskScore = document.getElementById('riskScore');
  const riskCategory = document.getElementById('riskCategory');
  const scoreBar = document.getElementById('scoreBar');
  const feedbackList = document.getElementById('feedbackList');
  const featuresSection = document.getElementById('featuresSection');
  const psychologySection = document.getElementById('psychologySection');
  const errorMessage = document.getElementById('errorMessage');

  resultTitle.textContent = 'Message Analysis Result';

  const score = result.risk_score || 0;
  const prediction = result.prediction || 'Unknown';

  riskScore.textContent = score;
  riskCategory.textContent = prediction;
  riskCategory.className = `risk-category ${prediction.toLowerCase().replace('/', '-')}`;

  scoreBar.style.width = `${Math.min(100, score)}%`;

  // Feedback
  feedbackList.innerHTML = '';
  if (result.feedback && result.feedback.length > 0) {
    result.feedback.forEach(item => {
      const li = document.createElement('li');
      li.textContent = item;
      feedbackList.appendChild(li);
    });
  } else {
    const li = document.createElement('li');
    li.textContent = 'No risk signals detected.';
    feedbackList.appendChild(li);
  }

  // Hide features for messages
  featuresSection.classList.add('hidden');

  // Scam Psychology
  if (result.scam_psychology && result.scam_psychology.scores) {
    const scores = result.scam_psychology.scores;
    const hasSignals = Object.values(scores).some(v => v > 0);

    if (hasSignals) {
      psychologySection.classList.remove('hidden');
      const psychologyList = document.getElementById('psychologyList');
      psychologyList.innerHTML = '';
      Object.entries(scores).forEach(([trigger, score]) => {
        if (score > 0) {
          const div = document.createElement('div');
          div.className = 'psychology-item';
          const label = trigger.charAt(0).toUpperCase() + trigger.slice(1);
          div.innerHTML = `
            <span>${label} Pressure</span>
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
    } else {
      psychologySection.classList.add('hidden');
    }
  } else {
    psychologySection.classList.add('hidden');
  }

  errorMessage.classList.remove('show');
  resultsPanel.classList.add('active');
}

// Hide results panel
function hideResults() {
  document.getElementById('results').classList.remove('active');
}
