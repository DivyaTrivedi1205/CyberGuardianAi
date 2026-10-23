// Content script for automatic URL checking
// This runs on every page and can intercept navigation

let backendUrl = 'http://127.0.0.1:8000';
let checkUrlsEnabled = true;
let urlCheckCache = {};
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// Load configuration
chrome.storage.local.get(['cyberguardian_backend_url', 'cyberguardian_auto_check'], (result) => {
  backendUrl = result.cyberguardian_backend_url || 'http://127.0.0.1:8000';
  checkUrlsEnabled = result.cyberguardian_auto_check !== false; // Default true
});

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'updateConfig') {
    backendUrl = request.backendUrl;
    checkUrlsEnabled = request.autoCheck !== false;
  }
});

// Check all links on page load and periodically
function checkPageLinks() {
  if (!checkUrlsEnabled) return;

  const links = document.querySelectorAll('a[href]');
  links.forEach(link => {
    const url = link.href;

    // Skip certain URLs
    if (shouldSkipUrl(url)) return;

    // Check if already cached
    if (urlCheckCache[url] && Date.now() - urlCheckCache[url].timestamp < CACHE_DURATION) {
      decorateLink(link, urlCheckCache[url].result);
      return;
    }

    // Async check
    analyzeUrlQuietly(url).then(result => {
      urlCheckCache[url] = { result, timestamp: Date.now() };
      decorateLink(link, result);
    }).catch(err => {
      // Silent fail - don't break page
      console.debug('URL check failed:', err);
    });
  });
}

// Determine if URL should be checked
function shouldSkipUrl(url) {
  try {
    const u = new URL(url);

    // Skip internal links
    if (u.hostname === window.location.hostname) return true;

    // Skip browser extensions and special protocols
    if (['chrome:', 'edge:', 'about:', 'data:', 'javascript:'].some(proto => url.startsWith(proto))) {
      return true;
    }

    // Skip common safe domains
    const safeDomains = ['google.com', 'github.com', 'stackoverflow.com', 'mozilla.org', 'w3.org'];
    if (safeDomains.some(domain => u.hostname.includes(domain))) {
      return true;
    }

    return false;
  } catch {
    return true;
  }
}

// Analyze URL silently via background service worker (bypasses webpage CORS restrictions)
function analyzeUrlQuietly(url) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(
      { action: 'analyzeUrl', url, backendUrl },
      (response) => {
        if (chrome.runtime.lastError) {
          return reject(new Error(chrome.runtime.lastError.message));
        }
        if (!response || !response.success) {
          return reject(new Error(response?.error || 'Analysis failed'));
        }
        resolve(response.data);
      }
    );
  });
}

// Decorate link based on risk
function decorateLink(linkElement, result) {
  if (!result || typeof result.risk_score !== 'number') return;

  const score = result.risk_score;
  const prediction = result.prediction || 'Unknown';

  // Add data attributes
  linkElement.dataset.cgRisk = score;
  linkElement.dataset.cgPrediction = prediction;

  // Don't visually block - add subtle indicator
  if (score >= 70) {
    // High risk - add warning tooltip and red dotted underline
    linkElement.title = `⚠️ CyberGuardian: ${prediction} (Risk: ${score}/100)`;
    linkElement.style.borderBottom = '2px dotted #ef4444';
  } else if (score >= 35) {
    // Moderate risk - subtle indicator
    linkElement.title = `⚠️ CyberGuardian: ${prediction} (Risk: ${score}/100)`;
    linkElement.style.borderBottom = '1px dotted #f59e0b';
  }
  // Low risk - no visual change
}

// Check page on load (robust against document.readyState)
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(checkPageLinks, 500);
  });
} else {
  setTimeout(checkPageLinks, 500);
}

// Re-check when new content is added (AJAX)
const observer = new MutationObserver((mutations) => {
  let hasNewLinks = false;
  mutations.forEach(mutation => {
    if (mutation.addedNodes.length > 0) {
      hasNewLinks = true;
    }
  });

  if (hasNewLinks) {
    setTimeout(checkPageLinks, 300);
  }
});

observer.observe(document.body, {
  childList: true,
  subtree: true
});

// Intercept link clicks to warn about suspicious URLs
document.addEventListener('click', (e) => {
  const link = e.target.closest && e.target.closest('a[href]');
  if (link && link.href) {
    const url = link.href;
    const risk = Number(link.dataset.cgRisk);

    if (risk >= 70) {
      e.preventDefault();
      e.stopPropagation();
      const prediction = link.dataset.cgPrediction || 'Threat Detected';
      showWarningPopup(url, risk, prediction);
    }
  }
}, true);

// Show warning popup
function showWarningPopup(url, risk, prediction) {
  const popup = document.createElement('div');
  popup.id = 'cyberguardian-warning-popup';
  popup.style.cssText = `
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: #0f172a;
    border: 2px solid #ef4444;
    border-radius: 8px;
    padding: 24px;
    max-width: 400px;
    z-index: 999999;
    font-family: Arial, sans-serif;
    color: #cbd5e1;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  `;

  popup.innerHTML = `
    <div style="display: grid; gap: 16px;">
      <div>
        <h2 style="color: #ef4444; font-size: 18px; margin: 0 0 8px 0;">⚠️ Security Warning</h2>
        <p style="margin: 0; font-size: 14px; line-height: 1.5;">
          CyberGuardian detected this link as <strong>${prediction}</strong> (Risk: ${risk}/100)
        </p>
      </div>
      <div style="background: #1e293b; padding: 8px; border-radius: 4px; font-family: monospace; font-size: 12px; word-break: break-all;">
        ${escapeHtml(url)}
      </div>
      <div style="display: flex; gap: 8px;">
        <button id="cg-cancel-btn" style="
          flex: 1;
          padding: 8px;
          background: #334155;
          border: 1px solid #475569;
          color: #cbd5e1;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
        ">Cancel</button>
        <button id="cg-proceed-btn" style="
          flex: 1;
          padding: 8px;
          background: #ef4444;
          border: none;
          color: white;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
        ">Proceed at Risk</button>
      </div>
    </div>
  `;

  document.body.appendChild(popup);

  document.getElementById('cg-cancel-btn').addEventListener('click', () => {
    popup.remove();
  });

  document.getElementById('cg-proceed-btn').addEventListener('click', () => {
    popup.remove();
    window.location.href = url;
  });
}

function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}
