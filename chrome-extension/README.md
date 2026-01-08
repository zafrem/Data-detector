# PII Detector Chrome Extension

A Chrome extension that monitors browser activity for personal information (PII) using a hybrid detection approach: fast client-side pattern matching combined with the Data-Detector REST API for verification.

## Features

- **Multi-Source Monitoring**:
  - Form inputs before submission
  - Page content (DOM scanning)
  - Network requests (experimental)

- **Hybrid Detection**:
  - Fast client-side regex matching for immediate feedback
  - API verification for accurate detection with low false-positives
  - Offline fallback mode when API is unavailable

- **Privacy-Preserving**:
  - Never stores actual PII values
  - Only logs metadata (category, count, timestamp)
  - URL hashing for privacy

- **User-Friendly**:
  - Real-time notifications
  - Dashboard with statistics
  - Configurable sensitivity and namespaces

## Installation

### Prerequisites

1. **Data-Detector API Server**

   The extension requires a running Data-Detector API server:

   ```bash
   cd /Users/milkiss/github-public/Data-detector
   python -m datadetector.server
   ```

   Or using the CLI:
   ```bash
   data-detector serve --port 8080
   ```

   The API should be accessible at `http://localhost:8080`

### Load Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `chrome-extension` directory
5. The extension icon should appear in your toolbar

## Configuration

### First Time Setup

1. Click the extension icon in the toolbar
2. Click "Settings" in the popup
3. Configure the following:

   - **API Endpoint**: URL of your Data-Detector server (default: `http://localhost:8080`)
   - **Namespaces**: Select which pattern sets to use (e.g., `comm` for common patterns, `us` for US-specific)
   - **Monitoring**: Enable/disable form, DOM, or network monitoring
   - **Notifications**: Set threshold and enable/disable notifications
   - **Whitelist**: Add domains to skip scanning (one per line)

4. Click "Save Settings"

### Testing the Connection

In the Settings page:
1. Click "Test Connection" to verify API connectivity
2. You should see connection status with API version and pattern count

## Usage

### Monitoring Forms

1. Navigate to any web page with forms (or open `tests/test-form.html`)
2. Enter PII data (email, phone, SSN, etc.) into form fields
3. Watch for:
   - Input fields highlighted in orange when PII detected
   - Tooltip showing detected categories
   - Warning dialog on form submission

### Monitoring Page Content

1. Navigate to pages with visible PII (or open `tests/test-dom.html`)
2. The extension automatically scans:
   - Initial page content on load
   - Dynamically added content (mutations)
3. Check the extension popup for detection logs

### Viewing Detection History

1. Click the extension icon to open the popup
2. View:
   - Statistics (today, this week, total)
   - Top detected categories
   - Recent events with filtering

3. Filter events by:
   - Search term (category names)
   - Source (form, page, network)

## Architecture

```
chrome-extension/
├── manifest.json              # Extension manifest (Manifest V3)
├── background/
│   └── service-worker.js     # Network monitoring, notifications
├── content/
│   ├── content-script.js     # Entry point
│   ├── dom-scanner.js        # DOM mutation observer
│   ├── form-monitor.js       # Form event listeners
│   └── patterns.js           # Bundled regex patterns
├── lib/
│   ├── api-client.js         # Data-Detector API client
│   ├── pattern-matcher.js    # Local quick scan
│   ├── storage-manager.js    # Chrome storage wrapper
│   └── utils.js              # Shared utilities
├── popup/
│   ├── popup.html            # Dashboard UI
│   ├── popup.js              # Statistics & events
│   └── popup.css             # Styling
├── options/
│   ├── options.html          # Settings page
│   ├── options.js            # Configuration
│   └── options.css           # Styling
└── tests/
    ├── test-form.html        # Form testing page
    └── test-dom.html         # DOM scanning test page
```

## Detection Flow

1. **Client-Side Quick Scan** (`patterns.js` + `pattern-matcher.js`)
   - Fast regex matching for common PII patterns
   - Returns candidates in < 10ms
   - Categories: email, SSN, phone, credit card, IP, tokens, etc.

2. **API Verification** (`api-client.js`)
   - Sends candidates to Data-Detector `/find` endpoint
   - Full pattern matching with verification functions
   - Returns confirmed matches with severity levels

3. **Offline Fallback**
   - If API unavailable, uses client-side results
   - Marks detections as "unverified"
   - Lower accuracy but remains functional

## Supported PII Categories

- **Email addresses**
- **Phone numbers** (US, Korea, etc.)
- **SSN** (US Social Security Numbers)
- **RRN** (Korean Resident Registration Numbers)
- **Credit card numbers**
- **IP addresses** (IPv4, IPv6)
- **API tokens** (AWS, GitHub, generic)
- **IBAN** (International Bank Account Numbers)
- **Passport numbers**
- **Date of birth**
- **Addresses**

## Testing

### Test Files

Two test HTML files are provided in the `tests/` directory:

1. **test-form.html** - Tests form monitoring
   - Enter sample PII in form fields
   - Submit to trigger detection
   - Verify warnings and logs

2. **test-dom.html** - Tests DOM scanning
   - Static content with PII
   - Dynamic content injection
   - Mutation detection

### Manual Testing Steps

1. **Start the API**:
   ```bash
   cd /Users/milkiss/github-public/Data-detector
   python -m datadetector.server
   ```

2. **Load Test Pages**:
   - Open `chrome-extension/tests/test-form.html` in Chrome
   - Open `chrome-extension/tests/test-dom.html` in Chrome

3. **Verify Detection**:
   - Enter test data from the pages
   - Check extension popup for logs
   - Verify API status shows "Connected"

4. **Test Offline Mode**:
   - Stop the API server
   - Refresh test page
   - Verify extension still detects (client-only mode)
   - API status should show "Offline"

## Performance

- **Client-side scan**: < 10ms for typical text (10KB)
- **API verification**: < 100ms for typical request
- **DOM scan**: < 500ms for average page
- **Memory footprint**: < 50MB per tab

### Optimization Features

- Throttling: DOM scans limited to 1 every 3 seconds
- Debouncing: Form inputs debounced at 500ms
- Caching: API responses cached for 1 hour
- Sampling: Large pages (>50KB) sampled at 10%
- Background processing: Uses `requestIdleCallback`

## Privacy & Security

### Privacy Protections

- **No PII Storage**: Extension never stores actual PII values
- **Hashed URLs**: URLs are hashed before logging
- **API Privacy**: `include_matched_text: false` in API requests
- **Local Processing**: Client-side patterns don't leave the browser

### Security Considerations

- Whitelist trusted domains in settings
- Review detection logs regularly
- API communication over localhost (or HTTPS in production)
- Extension only observes, never modifies requests

## Troubleshooting

### API Not Connecting

1. Verify API is running:
   ```bash
   curl http://localhost:8080/health
   ```

2. Check API endpoint in settings
3. Look for CORS issues in browser console
4. Ensure firewall allows localhost:8080

### No Detections Showing

1. Check monitoring is enabled in settings
2. Verify page is not whitelisted
3. Check browser console for errors
4. Ensure test data contains actual PII patterns

### Extension Not Loading

1. Check for errors in `chrome://extensions/`
2. Verify all files are present
3. Check manifest.json syntax
4. Reload extension after changes

### Performance Issues

1. Disable DOM scanning for heavy pages
2. Increase throttle delay in dom-scanner.js
3. Add problematic domains to whitelist
4. Check Chrome Task Manager for memory usage

## Development

### Making Changes

1. Edit source files in the extension directory
2. Go to `chrome://extensions/`
3. Click reload icon on the PII Detector extension
4. Test changes

### Debugging

- **Background Script**: `chrome://extensions/` → Inspect service worker
- **Content Script**: Right-click page → Inspect → Console tab
- **Popup**: Right-click extension icon → Inspect popup

### Adding Patterns

Edit `content/patterns.js`:
```javascript
FAST_PATTERNS.my_pattern = {
  pattern: /regex-here/g,
  category: 'category_name',
  severity: 'high'
};
```

## Limitations

### Manifest V3 Restrictions

- Cannot block network requests (observation only)
- Response bodies not directly accessible via webRequest
- Service worker has 5-minute inactivity timeout

### Detection Limitations

- Client-side patterns have lower accuracy than API
- Cannot detect PII in:
  - Images or PDFs
  - Encrypted traffic
  - WebSocket messages (not yet implemented)
  - Password fields (skipped for privacy)

## Future Enhancements

- [ ] Machine learning-based detection
- [ ] Advanced redaction capabilities
- [ ] Compliance reporting (GDPR, CCPA)
- [ ] Multi-language UI
- [ ] Firefox/Edge ports
- [ ] Enterprise policy management
- [ ] WebSocket monitoring

## License

This extension integrates with the Data-Detector project. Refer to the main project license.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review browser console for errors
3. Test with the provided test HTML files
4. Verify API server is running and accessible
