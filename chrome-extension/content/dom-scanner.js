/**
 * DOM Scanner for PII Detector
 * Monitors DOM content for exposed PII using MutationObserver
 */

class DOMScanner {
  constructor() {
    this.lastScan = 0;
    this.throttleDelay = 3000; // 3 seconds
    this.observer = null;
    this.scannedNodes = new WeakSet();
    this.scanning = false;
  }

  /**
   * Initialize DOM scanning
   */
  async init() {
    // Perform initial scan of page content
    await this.scanInitialContent();

    // Start observing DOM changes
    this.startObserving();

    console.log('[PII Detector] DOM scanning initialized');
  }

  /**
   * Scan initial page content
   */
  async scanInitialContent() {
    try {
      const text = this.getVisibleText(document.body);

      if (!text || text.length === 0) {
        return;
      }

      // For large pages, sample the content
      const textToScan = text.length > 50000 ? sampleText(text, 0.1) : text;

      const namespaces = await getEnabledNamespaces();
      const results = await detectPII(textToScan, namespaces, {
        maxMatches: 20
      });

      if (results.matches && results.matches.length > 0) {
        this.reportDetection(results, 'dom-initial');
      }
    } catch (error) {
      console.error('[PII Detector] Initial DOM scan error:', error);
    }
  }

  /**
   * Start observing DOM mutations
   */
  startObserving() {
    this.observer = new MutationObserver(mutations => {
      this.queueScan(mutations);
    });

    this.observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true
    });
  }

  /**
   * Queue a scan with throttling
   * @param {Array} mutations - Array of mutations
   */
  queueScan(mutations) {
    const now = Date.now();

    // Throttle: don't scan too frequently
    if (now - this.lastScan < this.throttleDelay) {
      return;
    }

    if (this.scanning) {
      return;
    }

    this.lastScan = now;

    // Use requestIdleCallback for background processing
    if (window.requestIdleCallback) {
      requestIdleCallback(() => {
        this.scanMutations(mutations);
      }, { timeout: 2000 });
    } else {
      // Fallback for browsers without requestIdleCallback
      setTimeout(() => {
        this.scanMutations(mutations);
      }, 100);
    }
  }

  /**
   * Scan mutations for new text content
   * @param {Array} mutations - Array of mutations
   */
  async scanMutations(mutations) {
    if (this.scanning) {
      return;
    }

    this.scanning = true;

    try {
      const addedText = this.extractAddedText(mutations);

      if (!addedText || addedText.length === 0) {
        return;
      }

      // Quick check first
      if (!containsPII(addedText)) {
        return;
      }

      const namespaces = await getEnabledNamespaces();
      const results = await detectPII(addedText, namespaces, {
        maxMatches: 10
      });

      if (results.matches && results.matches.length > 0) {
        this.reportDetection(results, 'dom-mutation');
      }
    } catch (error) {
      console.error('[PII Detector] Mutation scan error:', error);
    } finally {
      this.scanning = false;
    }
  }

  /**
   * Extract text from added nodes in mutations
   * @param {Array} mutations - Array of mutations
   * @returns {string} Extracted text
   */
  extractAddedText(mutations) {
    const textParts = [];

    for (const mutation of mutations) {
      // Handle character data changes
      if (mutation.type === 'characterData') {
        const text = mutation.target.textContent?.trim();
        if (text) {
          textParts.push(text);
        }
      }

      // Handle added nodes
      if (mutation.type === 'childList') {
        for (const node of mutation.addedNodes) {
          if (this.scannedNodes.has(node)) {
            continue;
          }

          if (node.nodeType === Node.TEXT_NODE) {
            const text = node.textContent?.trim();
            if (text) {
              textParts.push(text);
              this.scannedNodes.add(node);
            }
          } else if (node.nodeType === Node.ELEMENT_NODE) {
            const text = this.getVisibleText(node);
            if (text) {
              textParts.push(text);
              this.scannedNodes.add(node);
            }
          }
        }
      }
    }

    return textParts.join(' ');
  }

  /**
   * Get visible text from an element
   * @param {Element} element - DOM element
   * @returns {string} Visible text
   */
  getVisibleText(element) {
    if (!element) return '';

    const walker = document.createTreeWalker(
      element,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: (node) => {
          const parent = node.parentElement;
          if (!parent) return NodeFilter.FILTER_REJECT;

          // Skip script and style elements
          const tagName = parent.tagName?.toLowerCase();
          if (tagName === 'script' || tagName === 'style' || tagName === 'noscript') {
            return NodeFilter.FILTER_REJECT;
          }

          // Check if element is visible
          const style = window.getComputedStyle(parent);
          if (style.display === 'none' || style.visibility === 'hidden') {
            return NodeFilter.FILTER_REJECT;
          }

          return NodeFilter.FILTER_ACCEPT;
        }
      }
    );

    const textNodes = [];
    let node;

    while (node = walker.nextNode()) {
      const text = node.textContent?.trim();
      if (text && text.length > 0) {
        textNodes.push(text);
      }

      // Limit text collection to prevent memory issues
      if (textNodes.length > 1000) {
        break;
      }
    }

    return textNodes.join(' ');
  }

  /**
   * Sample text at given percentage (for large pages)
   * @param {string} text - Text to sample
   * @param {number} percentage - Percentage to sample (0.0-1.0)
   * @returns {string} Sampled text
   */
  sampleText(text, percentage = 0.1) {
    const words = text.split(/\s+/);
    const sampleSize = Math.floor(words.length * percentage);
    const step = Math.floor(words.length / sampleSize);

    const sampled = [];
    for (let i = 0; i < words.length; i += step) {
      sampled.push(words[i]);
    }

    return sampled.join(' ');
  }

  /**
   * Report PII detection to background script
   * @param {Object} results - Detection results
   * @param {string} source - Source identifier
   */
  reportDetection(results, source) {
    chrome.runtime.sendMessage({
      type: 'PII_DETECTED',
      source: source,
      url: window.location.href,
      matches: results.matches,
      mode: results.mode
    });

    console.log(`[PII Detector] Detected ${results.matches.length} PII instances in ${source}`);
  }

  /**
   * Pause scanning
   */
  pause() {
    if (this.observer) {
      this.observer.disconnect();
    }
  }

  /**
   * Resume scanning
   */
  resume() {
    if (this.observer) {
      this.startObserving();
    }
  }

  /**
   * Cleanup resources
   */
  destroy() {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }

    this.scannedNodes = new WeakSet();
  }
}

/**
 * Sample text helper (standalone function)
 */
function sampleText(text, percentage = 0.1) {
  const words = text.split(/\s+/);
  const sampleSize = Math.floor(words.length * percentage);
  const step = Math.floor(words.length / sampleSize) || 1;

  const sampled = [];
  for (let i = 0; i < words.length; i += step) {
    sampled.push(words[i]);
  }

  return sampled.join(' ');
}
