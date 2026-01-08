# Extension Icons

The Chrome extension requires three icon sizes:
- `icons/icon16.png` (16x16 pixels) - Toolbar icon
- `icons/icon48.png` (48x48 pixels) - Extension management page
- `icons/icon128.png` (128x128 pixels) - Chrome Web Store

## Creating Icons

You can create icons using any image editor. Here are some suggestions:

### Design Recommendations

- Use a simple, recognizable symbol (e.g., shield, eye, lock)
- Use the extension's brand colors: `#667eea` (purple-blue)
- Ensure good contrast for visibility
- Keep design simple for small sizes

### Tools

1. **Figma** (free online):
   - Create a 128x128 canvas
   - Design your icon
   - Export as PNG at 16x16, 48x48, and 128x128

2. **Canva** (free online):
   - Use icon template
   - Export in required sizes

3. **GIMP** (free desktop):
   - Create new image (128x128)
   - Design icon
   - Scale and export to different sizes

### Quick Placeholder Icons

For testing purposes, you can create simple colored squares:

```bash
# Using ImageMagick (if installed)
convert -size 16x16 xc:#667eea icons/icon16.png
convert -size 48x48 xc:#667eea icons/icon48.png
convert -size 128x128 xc:#667eea icons/icon128.png
```

### Online Icon Generators

- https://icon.kitchen/ - Chrome Extension icon generator
- https://www.favicon-generator.org/ - Multi-size icon generator
- https://www.flaticon.com/ - Free icon library

## Icon Ideas

- 🔍 Magnifying glass over document
- 🛡️ Shield with lock
- 👁️ Eye symbol (watching/monitoring)
- 🔐 Lock with key
- 📋 Clipboard with checkmark

## Installation

1. Create your icons in the required sizes
2. Save them in the `chrome-extension/icons/` directory:
   - `icon16.png`
   - `icon48.png`
   - `icon128.png`
3. Reload the extension in Chrome

The icons are referenced in `manifest.json` and will appear:
- In the browser toolbar
- On the extensions management page
- In the Chrome Web Store (if published)
