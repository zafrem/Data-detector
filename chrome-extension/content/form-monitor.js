/**
 * Form Monitor for PII Detector
 * Monitors form inputs and submissions for PII
 */

class FormMonitor {
  constructor() {
    this.debounceTimers = new Map();
    this.formData = new Map();
    this.highlightedInputs = new Set();
  }

  /**
   * Initialize form monitoring
   */
  init() {
    // Monitor existing forms
    this.scanExistingForms();

    // Monitor dynamically added forms
    this.observeFormAdditions();

    console.log('[PII Detector] Form monitoring initialized');
  }

  /**
   * Scan and attach listeners to existing forms
   */
  scanExistingForms() {
    const forms = document.querySelectorAll('form');
    console.log(`[PII Detector] Found ${forms.length} forms`);

    forms.forEach(form => {
      this.attachFormListener(form);
    });
  }

  /**
   * Observe DOM for dynamically added forms
   */
  observeFormAdditions() {
    const observer = new MutationObserver(mutations => {
      mutations.forEach(mutation => {
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.tagName === 'FORM') {
              this.attachFormListener(node);
            }

            // Check for forms within added nodes
            const forms = node.querySelectorAll?.('form');
            forms?.forEach(form => this.attachFormListener(form));
          }
        });
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  /**
   * Attach event listeners to a form
   * @param {HTMLFormElement} form - Form element
   */
  attachFormListener(form) {
    // Prevent duplicate listeners
    if (form.dataset.piiMonitored) {
      return;
    }

    form.dataset.piiMonitored = 'true';

    // Monitor form submission
    form.addEventListener('submit', async (e) => {
      await this.handleFormSubmit(e, form);
    });

    // Monitor individual inputs
    const inputs = form.querySelectorAll('input, textarea');
    inputs.forEach(input => {
      this.attachInputListener(input);
    });
  }

  /**
   * Attach event listener to an input field
   * @param {HTMLInputElement} input - Input element
   */
  attachInputListener(input) {
    // Skip password fields for privacy
    if (input.type === 'password') {
      return;
    }

    input.addEventListener('input', (e) => {
      this.debouncedScanInput(input);
    });

    input.addEventListener('blur', () => {
      this.removeHighlight(input);
    });
  }

  /**
   * Debounced scan of input field
   * @param {HTMLInputElement} input - Input element
   */
  debouncedScanInput(input) {
    clearTimeout(this.debounceTimers.get(input));

    this.debounceTimers.set(input, setTimeout(async () => {
      await this.scanInput(input);
    }, 500));
  }

  /**
   * Scan a single input field for PII
   * @param {HTMLInputElement} input - Input element
   */
  async scanInput(input) {
    const value = input.value;

    if (!value || value.length < 3) {
      this.removeHighlight(input);
      return;
    }

    // Quick check first
    if (!containsPII(value)) {
      this.removeHighlight(input);
      return;
    }

    try {
      const namespaces = await getEnabledNamespaces();
      const results = await detectPII(value, namespaces, {
        maxMatches: 5
      });

      if (results.matches && results.matches.length > 0) {
        this.highlightInput(input, results.matches);
      } else {
        this.removeHighlight(input);
      }
    } catch (error) {
      console.error('[PII Detector] Input scan error:', error);
    }
  }

  /**
   * Highlight input field containing PII
   * @param {HTMLInputElement} input - Input element
   * @param {Array} matches - Detected matches
   */
  highlightInput(input, matches) {
    input.style.borderColor = '#FF9800';
    input.style.borderWidth = '2px';
    input.style.boxShadow = '0 0 5px rgba(255, 152, 0, 0.5)';

    this.highlightedInputs.add(input);

    // Add tooltip
    const categories = [...new Set(matches.map(m => m.category))];
    input.title = `PII Detected: ${categories.map(c => getCategoryDisplayName(c)).join(', ')}`;
  }

  /**
   * Remove highlight from input field
   * @param {HTMLInputElement} input - Input element
   */
  removeHighlight(input) {
    input.style.borderColor = '';
    input.style.borderWidth = '';
    input.style.boxShadow = '';
    input.title = '';

    this.highlightedInputs.delete(input);
  }

  /**
   * Handle form submission
   * @param {Event} e - Submit event
   * @param {HTMLFormElement} form - Form element
   */
  async handleFormSubmit(e, form) {
    try {
      const formData = new FormData(form);
      const data = Object.fromEntries(formData);

      // Filter out password fields
      const values = Object.entries(data)
        .filter(([key, _]) => {
          const input = form.querySelector(`[name="${key}"]`);
          return input?.type !== 'password';
        })
        .map(([_, value]) => value);

      const text = values.join('\n');

      if (!text || text.length === 0) {
        return;
      }

      const namespaces = await getEnabledNamespaces();
      const results = await detectPII(text, namespaces);

      if (results.matches && results.matches.length > 0) {
        // Send message to background script
        chrome.runtime.sendMessage({
          type: 'PII_DETECTED',
          source: 'form',
          url: window.location.href,
          matches: results.matches,
          mode: results.mode,
          formAction: form.action || window.location.href
        });

        // Show warning to user
        const shouldContinue = await this.showSubmitWarning(results);

        if (!shouldContinue) {
          e.preventDefault();
          console.log('[PII Detector] Form submission prevented by user');
        }
      }
    } catch (error) {
      console.error('[PII Detector] Form submit scan error:', error);
    }
  }

  /**
   * Show warning before form submission
   * @param {Object} results - Detection results
   * @returns {Promise<boolean>} True if user wants to continue
   */
  async showSubmitWarning(results) {
    const categories = [...new Set(results.matches.map(m => m.category))];
    const categoryNames = categories.map(c => getCategoryDisplayName(c)).join(', ');

    const message = `This form contains potential personal information (${categoryNames}).\n\nDo you want to submit it anyway?`;

    return confirm(message);
  }

  /**
   * Cleanup resources
   */
  destroy() {
    // Clear all debounce timers
    for (const timer of this.debounceTimers.values()) {
      clearTimeout(timer);
    }

    this.debounceTimers.clear();

    // Remove highlights
    for (const input of this.highlightedInputs) {
      this.removeHighlight(input);
    }
  }
}

/**
 * Get category display name helper
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
