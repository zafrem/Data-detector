/**
 * Bundled regex patterns for fast client-side PII detection
 * These are lightweight, high-confidence patterns extracted from Data-Detector
 */

const FAST_PATTERNS = {
  // Email addresses
  email: {
    pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    category: 'email',
    severity: 'medium'
  },

  // US Social Security Number
  us_ssn: {
    pattern: /\b\d{3}-\d{2}-\d{4}\b/g,
    category: 'ssn',
    severity: 'critical'
  },

  // US Phone numbers (various formats)
  us_phone: {
    pattern: /\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/g,
    category: 'phone',
    severity: 'medium'
  },

  // Credit card numbers (16 digits with optional separators)
  credit_card: {
    pattern: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g,
    category: 'credit_card',
    severity: 'critical'
  },

  // IPv4 addresses
  ipv4: {
    pattern: /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/g,
    category: 'ip',
    severity: 'low'
  },

  // IPv6 addresses (simplified)
  ipv6: {
    pattern: /\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b/g,
    category: 'ip',
    severity: 'low'
  },

  // Korean mobile phone numbers
  kr_mobile: {
    pattern: /\b01[0-9]-?\d{3,4}-?\d{4}\b/g,
    category: 'phone',
    severity: 'medium'
  },

  // Korean Resident Registration Number (RRN)
  kr_rrn: {
    pattern: /\b\d{6}-?[1-4]\d{6}\b/g,
    category: 'rrn',
    severity: 'critical'
  },

  // API keys and tokens (generic patterns)
  api_key_generic: {
    pattern: /\b[A-Za-z0-9_-]{32,}\b/g,
    category: 'token',
    severity: 'high',
    // Only flag if it looks like a key (has mix of chars/numbers)
    validate: (match) => {
      return /[A-Za-z]/.test(match) && /[0-9]/.test(match);
    }
  },

  // AWS Access Key
  aws_access_key: {
    pattern: /\bAKIA[0-9A-Z]{16}\b/g,
    category: 'token',
    severity: 'critical'
  },

  // GitHub Personal Access Token
  github_token: {
    pattern: /\bghp_[A-Za-z0-9]{36}\b/g,
    category: 'token',
    severity: 'critical'
  },

  // Generic bearer tokens
  bearer_token: {
    pattern: /\bBearer\s+[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/gi,
    category: 'token',
    severity: 'high'
  },

  // US Zip codes (for address detection)
  us_zipcode: {
    pattern: /\b\d{5}(?:-\d{4})?\b/g,
    category: 'address',
    severity: 'low'
  },

  // IBAN (simplified - basic structure)
  iban: {
    pattern: /\b[A-Z]{2}\d{2}[A-Z0-9]{4,}\b/g,
    category: 'iban',
    severity: 'high'
  },

  // Dates that might be DOB (various formats)
  date_of_birth: {
    pattern: /\b(?:0[1-9]|1[0-2])\/(?:0[1-9]|[12][0-9]|3[01])\/(?:19|20)\d{2}\b/g,
    category: 'date_of_birth',
    severity: 'medium'
  },

  // Passport numbers (generic pattern)
  passport: {
    pattern: /\b[A-Z]{1,2}\d{6,9}\b/g,
    category: 'passport',
    severity: 'high'
  }
};

/**
 * Get all patterns as array
 * @returns {Array} Array of pattern objects
 */
function getAllPatterns() {
  return Object.entries(FAST_PATTERNS).map(([id, config]) => ({
    id,
    ...config
  }));
}

/**
 * Get patterns by category
 * @param {string} category - Category name
 * @returns {Array} Array of matching patterns
 */
function getPatternsByCategory(category) {
  return Object.entries(FAST_PATTERNS)
    .filter(([_, config]) => config.category === category)
    .map(([id, config]) => ({ id, ...config }));
}

/**
 * Get patterns by severity
 * @param {string} minSeverity - Minimum severity level
 * @returns {Array} Array of matching patterns
 */
function getPatternsBySeverity(minSeverity) {
  const severityLevels = { low: 0, medium: 1, high: 2, critical: 3 };
  const minLevel = severityLevels[minSeverity] || 0;

  return Object.entries(FAST_PATTERNS)
    .filter(([_, config]) => severityLevels[config.severity] >= minLevel)
    .map(([id, config]) => ({ id, ...config }));
}
