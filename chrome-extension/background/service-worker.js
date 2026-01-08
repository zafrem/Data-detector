/**
 * Background Service Worker for PII Detector
 * Handles network monitoring, notifications, and message coordination
 */

// Import libraries (Manifest V3 supports importScripts in service workers)
importScripts(
  '../lib/utils.js',
  '../lib/storage-manager.js',
  '../content/patterns.js',
  '../lib/pattern-matcher.js',
  '../lib/api-client.js'
);

console.log('[PII Detector] Service worker loaded');

/**
 * Initialize extension
 */
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('[PII Detector] Extension installed');

    // Set default configuration
    resetConfig().then(() => {
      // Open options page on first install
      chrome.runtime.openOptionsPage();
    });
  } else if (details.reason === 'update') {
    console.log('[PII Detector] Extension updated');
  }
});

/**
 * Network Request Monitoring
 * Note: Manifest V3 only allows observation, not blocking
 */
chrome.webRequest.onBeforeRequest.addListener(
  async (details) => {
    try {
      // Check if network monitoring is enabled
      const enabled = await isMonitoringEnabled('network');
      if (!enabled) {
        return;
      }

      // Check if URL is whitelisted
      const whitelist = await getWhitelist();
      if (isWhitelisted(details.url, whitelist)) {
        return;
      }

      // Only monitor POST requests with body
      if (details.method !== 'POST' || !details.requestBody) {
        return;
      }

      // Extract and scan request body
      const bodyText = extractRequestBody(details.requestBody);
      if (!bodyText || bodyText.length === 0) {
        return;
      }

      // Quick check first
      if (!containsPII(bodyText)) {
        return;
      }

      const namespaces = await getEnabledNamespaces();
      const results = await detectPII(bodyText, namespaces, {
        maxMatches: 10
      });

      if (results.matches && results.matches.length > 0) {
        await handleDetection({
          source: 'network',
          url: details.url,
          matches: results.matches,
          mode: results.mode,
          method: details.method,
          requestId: details.requestId
        });
      }
    } catch (error) {
      console.error('[PII Detector] Network monitoring error:', error);
    }
  },
  { urls: ['<all_urls>'] },
  ['requestBody']
);

/**
 * Message Handler
 * Receives messages from content scripts and popup
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    try {
      switch (message.type) {
        case 'PII_DETECTED':
          await handleDetection(message);
          sendResponse({ success: true });
          break;

        case 'CHECK_API_STATUS':
          const status = await checkAPIStatus();
          sendResponse(status);
          break;

        case 'GET_STATISTICS':
          const stats = await getStatistics();
          sendResponse(stats);
          break;

        case 'CLEAR_EVENTS':
          await clearDetectionEvents();
          sendResponse({ success: true });
          break;

        default:
          sendResponse({ success: false, error: 'Unknown message type' });
      }
    } catch (error) {
      console.error('[PII Detector] Message handler error:', error);
      sendResponse({ success: false, error: error.message });
    }
  })();

  return true;  // Keep message channel open for async response
});

/**
 * Handle PII detection event
 * @param {Object} event - Detection event
 */
async function handleDetection(event) {
  // Log event to storage
  await logDetectionEvent(event);

  // Check notification threshold
  const shouldNotify = await shouldShowNotification(event.matches);

  if (shouldNotify) {
    await showNotification(event);
  }

  // Update badge
  await updateBadge();
}

/**
 * Check if notification should be shown
 * @param {Array} matches - Detected matches
 * @returns {Promise<boolean>} True if should notify
 */
async function shouldShowNotification(matches) {
  // Check if notifications are enabled
  const enabled = await areNotificationsEnabled();
  if (!enabled) {
    return false;
  }

  // Check severity threshold
  const threshold = await getNotificationThreshold();
  const severityOrder = { low: 1, medium: 2, high: 3, critical: 4 };
  const minLevel = severityOrder[threshold] || 1;

  // Check if any match meets threshold
  return matches.some(match => {
    const matchLevel = severityOrder[match.severity] || 1;
    return matchLevel >= minLevel;
  });
}

/**
 * Show browser notification
 * @param {Object} event - Detection event
 */
async function showNotification(event) {
  const categories = [...new Set(event.matches.map(m => m.category))];
  const categoryNames = categories.map(c => getCategoryDisplayName(c)).join(', ');

  const sourceLabels = {
    form: 'Form',
    'dom-initial': 'Page Content',
    'dom-mutation': 'Page Content',
    network: 'Network Request'
  };

  const sourceLabel = sourceLabels[event.source] || 'Unknown';

  chrome.notifications.create({
    type: 'basic',
    iconUrl: '../icons/icon48.png',
    title: 'PII Detected',
    message: `Found ${event.matches.length} PII instance(s) in ${sourceLabel}\nCategories: ${categoryNames}`,
    buttons: [
      { title: 'View Details' },
      { title: 'Dismiss' }
    ],
    requireInteraction: false,
    priority: 1
  });
}

/**
 * Handle notification button clicks
 */
chrome.notifications.onButtonClicked.addListener((notifId, btnIdx) => {
  if (btnIdx === 0) {
    // View Details - open popup
    chrome.action.openPopup();
  }

  // Dismiss notification
  chrome.notifications.clear(notifId);
});

/**
 * Update extension badge with detection count
 */
async function updateBadge() {
  try {
    const stats = await getStatistics();

    if (stats.today > 0) {
      chrome.action.setBadgeText({
        text: stats.today > 99 ? '99+' : stats.today.toString()
      });
      chrome.action.setBadgeBackgroundColor({ color: '#FF5722' });
    } else {
      chrome.action.setBadgeText({ text: '' });
    }
  } catch (error) {
    console.error('[PII Detector] Badge update error:', error);
  }
}

/**
 * Check API status
 * @returns {Promise<Object>} API status
 */
async function checkAPIStatus() {
  try {
    const health = await checkAPIHealth();
    return {
      online: true,
      version: health.version,
      namespaces: health.namespaces,
      patternCount: health.patterns_loaded
    };
  } catch (error) {
    return {
      online: false,
      error: error.message
    };
  }
}

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

/**
 * Helper: Extract request body
 */
function extractRequestBody(requestBody) {
  if (!requestBody) return '';

  const parts = [];

  if (requestBody.formData) {
    for (const [key, values] of Object.entries(requestBody.formData)) {
      // Skip password fields
      if (key.toLowerCase().includes('password') || key.toLowerCase().includes('passwd')) {
        continue;
      }
      parts.push(...values);
    }
  }

  if (requestBody.raw) {
    for (const item of requestBody.raw) {
      if (item.bytes) {
        try {
          const decoder = new TextDecoder();
          parts.push(decoder.decode(new Uint8Array(item.bytes)));
        } catch (e) {
          console.warn('Failed to decode request body:', e);
        }
      }
    }
  }

  return parts.join('\n');
}

/**
 * Helper: Get category display name
 */
function getCategoryDisplayName(category) {
  const names = {
    email: 'Email',
    phone: 'Phone',
    ssn: 'SSN',
    rrn: 'RRN',
    credit_card: 'Credit Card',
    ip: 'IP Address',
    bank: 'Bank Account',
    passport: 'Passport',
    address: 'Address',
    name: 'Name',
    iban: 'IBAN',
    location: 'Location',
    token: 'API Token',
    date_of_birth: 'Date of Birth',
    other: 'Other'
  };

  return names[category] || category;
}

// Update badge on startup
updateBadge();
