/**
 * Options Page for PII Detector
 * Handles configuration and settings management
 */

let currentConfig = null;

/**
 * Initialize options page
 */
async function init() {
  await loadSettings();
  attachEventListeners();
}

/**
 * Load current settings
 */
async function loadSettings() {
  try {
    currentConfig = await getConfig();

    // API Endpoint
    document.getElementById('api-endpoint').value = currentConfig.apiEndpoint || 'http://localhost:8080';

    // Namespaces
    const namespaces = currentConfig.namespaces || ['comm', 'us'];
    document.querySelectorAll('.checkbox-group input[type="checkbox"][value]').forEach(checkbox => {
      checkbox.checked = namespaces.includes(checkbox.value);
    });

    // Monitoring Options
    document.getElementById('monitor-forms').checked = currentConfig.monitorForms !== false;
    document.getElementById('monitor-dom').checked = currentConfig.monitorDOM !== false;
    document.getElementById('monitor-network').checked = currentConfig.monitorNetwork === true;

    // Notifications
    document.getElementById('threshold').value = currentConfig.notificationThreshold || 'high';
    document.getElementById('show-notifications').checked = currentConfig.showNotifications !== false;

    // Whitelist
    const whitelist = currentConfig.whitelist || [];
    document.getElementById('whitelist').value = whitelist.join('\n');
  } catch (error) {
    console.error('Failed to load settings:', error);
    showStatus('Failed to load settings', 'error');
  }
}

/**
 * Save settings
 */
async function saveSettings() {
  try {
    // Get namespace checkboxes
    const namespaces = Array.from(
      document.querySelectorAll('.checkbox-group input[type="checkbox"][value]:checked')
    ).map(cb => cb.value);

    // Get whitelist
    const whitelistText = document.getElementById('whitelist').value;
    const whitelist = whitelistText
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0);

    const config = {
      apiEndpoint: document.getElementById('api-endpoint').value || 'http://localhost:8080',
      namespaces: namespaces,
      monitorForms: document.getElementById('monitor-forms').checked,
      monitorDOM: document.getElementById('monitor-dom').checked,
      monitorNetwork: document.getElementById('monitor-network').checked,
      notificationThreshold: document.getElementById('threshold').value,
      showNotifications: document.getElementById('show-notifications').checked,
      whitelist: whitelist
    };

    await saveConfig(config);
    currentConfig = config;

    showStatus('Settings saved successfully!', 'success');

    // Notify content scripts to reload config
    const tabs = await chrome.tabs.query({});
    for (const tab of tabs) {
      chrome.tabs.sendMessage(tab.id, { type: 'RELOAD_CONFIG' }).catch(() => {
        // Ignore errors for tabs that don't have content script
      });
    }
  } catch (error) {
    console.error('Failed to save settings:', error);
    showStatus('Failed to save settings: ' + error.message, 'error');
  }
}

/**
 * Reset to default settings
 */
async function resetSettings() {
  if (!confirm('Reset all settings to defaults? This cannot be undone.')) {
    return;
  }

  try {
    await resetConfig();
    await loadSettings();
    showStatus('Settings reset to defaults', 'success');
  } catch (error) {
    console.error('Failed to reset settings:', error);
    showStatus('Failed to reset settings', 'error');
  }
}

/**
 * Test API connection
 */
async function testConnection() {
  const statusEl = document.getElementById('connection-status');
  statusEl.textContent = 'Testing...';
  statusEl.className = 'status-message info';

  try {
    const apiEndpoint = document.getElementById('api-endpoint').value;

    // Temporarily use this endpoint for testing
    const response = await fetch(`${apiEndpoint}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const health = await response.json();

    statusEl.innerHTML = `
      <strong>Connected!</strong><br>
      Version: ${health.version || 'unknown'}<br>
      Patterns: ${health.patterns_loaded || 0}<br>
      Namespaces: ${health.namespaces?.join(', ') || 'none'}
    `;
    statusEl.className = 'status-message success';
  } catch (error) {
    statusEl.textContent = `Connection failed: ${error.message}`;
    statusEl.className = 'status-message error';
  }
}

/**
 * Show status message
 * @param {string} message - Message to show
 * @param {string} type - Type: 'success', 'error', 'info'
 */
function showStatus(message, type = 'info') {
  const statusEl = document.getElementById('save-status');
  statusEl.textContent = message;
  statusEl.className = `status-message ${type}`;

  // Clear after 3 seconds
  setTimeout(() => {
    statusEl.textContent = '';
    statusEl.className = 'status-message';
  }, 3000);
}

/**
 * Attach event listeners
 */
function attachEventListeners() {
  // Save button
  document.getElementById('save-btn').addEventListener('click', saveSettings);

  // Reset button
  document.getElementById('reset-btn').addEventListener('click', resetSettings);

  // Test connection
  document.getElementById('test-connection').addEventListener('click', testConnection);

  // Auto-save indicators
  document.querySelectorAll('input, select, textarea').forEach(element => {
    element.addEventListener('change', () => {
      const statusEl = document.getElementById('save-status');
      statusEl.textContent = 'Unsaved changes';
      statusEl.className = 'status-message info';
    });
  });
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', init);
