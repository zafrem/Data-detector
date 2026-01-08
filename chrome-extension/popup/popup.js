/**
 * Popup Dashboard for PII Detector
 * Displays statistics and event history
 */

let currentEvents = [];
let filteredEvents = [];

/**
 * Initialize popup
 */
async function init() {
  await loadStatistics();
  await checkAPIStatus();
  await loadEvents();
  attachEventListeners();
}

/**
 * Load and display statistics
 */
async function loadStatistics() {
  try {
    const stats = await getStatistics();

    document.getElementById('today-count').textContent = stats.today;
    document.getElementById('week-count').textContent = stats.week;
    document.getElementById('total-count').textContent = stats.total;

    displayCategoryBreakdown(stats.byCategory);
  } catch (error) {
    console.error('Failed to load statistics:', error);
  }
}

/**
 * Display category breakdown
 * @param {Object} categories - Category counts
 */
function displayCategoryBreakdown(categories) {
  const container = document.getElementById('category-list');

  if (!categories || Object.keys(categories).length === 0) {
    container.innerHTML = '<p class="empty-message">No detections yet</p>';
    return;
  }

  // Sort by count (descending)
  const sorted = Object.entries(categories)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);  // Top 5

  const html = sorted.map(([category, count]) => {
    const displayName = getCategoryDisplayName(category);
    return `
      <div class="category-item">
        <span class="category-name">${displayName}</span>
        <span class="category-count">${count}</span>
      </div>
    `;
  }).join('');

  container.innerHTML = html;
}

/**
 * Check API status
 */
async function checkAPIStatus() {
  const statusIndicator = document.getElementById('api-status');
  const statusText = document.getElementById('api-status-text');

  try {
    const response = await chrome.runtime.sendMessage({ type: 'CHECK_API_STATUS' });

    if (response.online) {
      statusIndicator.className = 'status-indicator online';
      statusText.textContent = `API Connected (v${response.version || 'unknown'})`;
    } else {
      statusIndicator.className = 'status-indicator offline';
      statusText.textContent = 'API Offline';
    }
  } catch (error) {
    statusIndicator.className = 'status-indicator offline';
    statusText.textContent = 'API Unavailable';
  }
}

/**
 * Load and display events
 */
async function loadEvents() {
  try {
    currentEvents = await getDetectionEvents();
    filteredEvents = currentEvents;

    displayEvents(filteredEvents);
  } catch (error) {
    console.error('Failed to load events:', error);
  }
}

/**
 * Display events in the list
 * @param {Array} events - Events to display
 */
function displayEvents(events) {
  const container = document.getElementById('event-list');

  if (!events || events.length === 0) {
    container.innerHTML = '<p class="empty-message">No events to display</p>';
    return;
  }

  // Sort by timestamp (newest first)
  const sorted = events.slice().sort((a, b) => b.timestamp - a.timestamp);

  // Show only last 20
  const recent = sorted.slice(0, 20);

  const html = recent.map(event => {
    const sourceLabels = {
      form: 'Form',
      'dom-initial': 'Page',
      'dom-mutation': 'Page',
      network: 'Network'
    };

    const sourceLabel = sourceLabels[event.source] || event.source;
    const timeStr = formatTimestamp(event.timestamp);
    const categoryNames = event.categories.map(c => getCategoryDisplayName(c)).join(', ');

    return `
      <div class="event-item">
        <div class="event-header">
          <span class="event-source">${sourceLabel}</span>
          <span class="event-time">${timeStr}</span>
        </div>
        <div class="event-details">
          <span class="event-count">${event.matchCount} match${event.matchCount !== 1 ? 'es' : ''}</span>
          <span class="event-categories">${categoryNames}</span>
        </div>
        <div class="event-mode">${getModeLabel(event.mode)}</div>
      </div>
    `;
  }).join('');

  container.innerHTML = html;
}

/**
 * Get mode label
 * @param {string} mode - Detection mode
 * @returns {string} Label
 */
function getModeLabel(mode) {
  const labels = {
    'api-verified': 'Verified',
    'client-only': 'Unverified',
    'client': 'Client-side'
  };

  return labels[mode] || mode;
}

/**
 * Filter events based on search and source
 */
function filterEvents() {
  const searchTerm = document.getElementById('search').value.toLowerCase();
  const sourceFilter = document.getElementById('source-filter').value;

  filteredEvents = currentEvents.filter(event => {
    // Source filter
    if (sourceFilter && event.source !== sourceFilter) {
      return false;
    }

    // Search filter (categories)
    if (searchTerm) {
      const categoryMatch = event.categories.some(cat =>
        getCategoryDisplayName(cat).toLowerCase().includes(searchTerm)
      );

      if (!categoryMatch) {
        return false;
      }
    }

    return true;
  });

  displayEvents(filteredEvents);
}

/**
 * Attach event listeners
 */
function attachEventListeners() {
  // Settings button
  document.getElementById('settings-btn').addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  // Clear history button
  document.getElementById('clear-btn').addEventListener('click', async () => {
    if (confirm('Clear all detection history? This cannot be undone.')) {
      try {
        await chrome.runtime.sendMessage({ type: 'CLEAR_EVENTS' });
        await loadStatistics();
        await loadEvents();
      } catch (error) {
        console.error('Failed to clear events:', error);
      }
    }
  });

  // Search and filter
  document.getElementById('search').addEventListener('input', filterEvents);
  document.getElementById('source-filter').addEventListener('change', filterEvents);
}

/**
 * Get category display name
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

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', init);
