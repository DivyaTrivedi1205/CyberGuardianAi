// CyberGuardian AI Background Service Worker

// Listen for messages from popup or content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'checkBackend') {
    checkBackendHealth(request.backendUrl).then(sendResponse);
    return true; // Will respond asynchronously
  }
});

// Check if backend is healthy
async function checkBackendHealth(backendUrl) {
  try {
    const response = await fetch(`${backendUrl}/`, {
      method: 'GET',
      mode: 'cors'
    });
    return {
      healthy: response.ok,
      status: response.status
    };
  } catch (error) {
    return {
      healthy: false,
      error: error.message
    };
  }
}

// Initialize extension on install
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    chrome.storage.local.set({
      'cyberguardian_backend_url': 'http://127.0.0.1:8000'
    });
  }
});
