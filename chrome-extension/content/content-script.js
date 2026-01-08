/**
 * Content Script Entry Point for PII Detector
 * Initializes form monitoring and DOM scanning
 */

// Global instances
let formMonitor = null;
let domScanner = null;

/**
 * Initialize PII detection on the page
 */
async function initPIIDetection() {
  try {
    console.log('[PII Detector] Initializing content script');

    // Check if page is whitelisted
    const whitelist = await getWhitelist();
    if (isWhitelisted(window.location.href, whitelist)) {
      console.log('[PII Detector] Page whitelisted, skipping monitoring');
      return;
    }

    // Initialize form monitoring
    const formsEnabled = await isMonitoringEnabled('forms');
    if (formsEnabled) {
      formMonitor = new FormMonitor();
      formMonitor.init();
    }

    // Initialize DOM scanning
    const domEnabled = await isMonitoringEnabled('dom');
    if (domEnabled) {
      domScanner = new DOMScanner();
      await domScanner.init();
    }

    console.log('[PII Detector] Content script initialized successfully');
  } catch (error) {
    console.error('[PII Detector] Initialization error:', error);
  }
}

/**
 * Cleanup on page unload
 */
function cleanup() {
  if (formMonitor) {
    formMonitor.destroy();
    formMonitor = null;
  }

  if (domScanner) {
    domScanner.destroy();
    domScanner = null;
  }
}

/**
 * Handle messages from background script
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'PAUSE_MONITORING':
      if (formMonitor) formMonitor.destroy();
      if (domScanner) domScanner.pause();
      sendResponse({ success: true });
      break;

    case 'RESUME_MONITORING':
      if (formMonitor) formMonitor.init();
      if (domScanner) domScanner.resume();
      sendResponse({ success: true });
      break;

    case 'RELOAD_CONFIG':
      // Reload monitoring based on new config
      cleanup();
      initPIIDetection();
      sendResponse({ success: true });
      break;

    default:
      sendResponse({ success: false, error: 'Unknown message type' });
  }

  return true;  // Keep message channel open for async response
});

/**
 * Helper: Check if URL is whitelisted
 */
function isWhitelisted(url, whitelist) {
  if (!whitelist || whitelist.length === 0) return false;

  try {
    const urlObj = new URL(url);
    const hostname = urlObj.hostname;

    return whitelist.some(domain => {
      return hostname === domain || hostname.endsWith(`.${domain}`);
    });
  } catch (e) {
    return false;
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPIIDetection);
} else {
  // DOM already loaded
  initPIIDetection();
}

// Cleanup on page unload
window.addEventListener('beforeunload', cleanup);
