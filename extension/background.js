// CyberGuardian AI Background Service Worker

// Listen for messages from popup or content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'checkBackend') {
    checkBackendHealth(request.backendUrl).then(sendResponse);
    return true; // Will respond asynchronously
  }
  if (request.action === 'analyzeUrl') {
    handleAnalyzeUrl(request.url, request.backendUrl).then(sendResponse);
    return true;
  }
  if (request.action === 'analyzeMessage') {
    handleAnalyzeMessage(request.message, request.backendUrl).then(sendResponse);
    return true;
  }
  if (request.action === 'analyzePassword') {
    handleAnalyzePassword(request.password, request.backendUrl).then(sendResponse);
    return true;
  }
});

// Resolve effective backend URL with fallback to storage and default
function getEffectiveBackendUrl(requestedUrl) {
  if (requestedUrl && typeof requestedUrl === 'string' && requestedUrl.trim()) {
    return Promise.resolve(requestedUrl.trim());
  }
  return new Promise((resolve) => {
    chrome.storage.local.get(['cyberguardian_backend_url'], (result) => {
      resolve(result.cyberguardian_backend_url || 'http://127.0.0.1:8000');
    });
  });
}

// Handle URL analysis
async function handleAnalyzeUrl(url, requestedBackendUrl) {
  try {
    const backendUrl = await getEffectiveBackendUrl(requestedBackendUrl);
    const response = await fetch(`${backendUrl}/security/analyze-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        success: false,
        error: errorData.detail || `HTTP ${response.status}`,
      };
    }

    const data = await response.json();
    return {
      success: true,
      data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message || 'Failed to connect to backend',
    };
  }
}

// Handle message analysis
async function handleAnalyzeMessage(message, requestedBackendUrl) {
  try {
    const backendUrl = await getEffectiveBackendUrl(requestedBackendUrl);
    const response = await fetch(`${backendUrl}/security/analyze-message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        success: false,
        error: errorData.detail || `HTTP ${response.status}`,
      };
    }

    const data = await response.json();
    return {
      success: true,
      data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message || 'Failed to connect to backend',
    };
  }
}

// Handle password analysis
async function handleAnalyzePassword(password, requestedBackendUrl) {
  try {
    const backendUrl = await getEffectiveBackendUrl(requestedBackendUrl);
    const response = await fetch(`${backendUrl}/security/analyze-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        success: false,
        error: errorData.detail || `HTTP ${response.status}`,
      };
    }

    const data = await response.json();
    return {
      success: true,
      data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message || 'Failed to connect to backend',
    };
  }
}

// Check if backend is healthy
async function checkBackendHealth(requestedBackendUrl) {
  try {
    const backendUrl = await getEffectiveBackendUrl(requestedBackendUrl);
    const response = await fetch(`${backendUrl}/`, {
      method: 'GET',
    });
    return {
      healthy: response.ok,
      status: response.status,
    };
  } catch (error) {
    return {
      healthy: false,
      error: error.message,
    };
  }
}

// Initialize extension on install
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    chrome.storage.local.set({
      cyberguardian_backend_url: 'http://127.0.0.1:8000',
    });
  }
});

