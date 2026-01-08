<p align="center">
  <img src="images/Data%20Detector.jpg" alt="Data Detector Logo" width="200">
</p>

# Data Detector

**Data Detector** is a high-performance engine for detecting, redacting, and generating sensitive data (PII).

## Installation

```bash
pip install data-detector
```

For more options, see the [Installation Guide](docs/installation.md).

## Quick Start

### Library Usage

```python
from datadetector import Engine, load_registry

# Load patterns and initialize engine
registry = load_registry()
engine = Engine(registry)

# Find PII
results = engine.find("My phone: 010-1234-5678")

# Redact text
redacted = engine.redact("Contact me at test@example.com")
print(redacted.redacted_text)
```

### NLP-Enhanced Detection (Korean, Chinese, Japanese)

For improved CJK PII detection with particle handling and word segmentation:

```python
from datadetector import Engine, load_registry, NLPConfig

# Configure NLP for CJK processing
nlp_config = NLPConfig(
    enable_language_detection=True,
    enable_korean_particles=True,
    enable_chinese_segmentation=True,
    enable_japanese_segmentation=True
)

registry = load_registry()
engine = Engine(registry, nlp_config=nlp_config)

# Detects PII even with particles or without spaces
text = "私の電話번호는 090-1234-5678입니다"
results = engine.find(text, namespaces=["jp", "kr"])
```

### Detection Process Steps

Here is how the engine processes text, illustrated with a Korean example:

1.  **Original Text**: `제 이름은 마크이고 전화번호는 010-1234-5678입니다.`
2.  **Tokenization**: `['제', '이름', '은', '마크', '이고', '전화번호', '는', '010-1234-5678', '입니다']`
    *   *The text is split into meaningful units (morphemes/words).*
3.  **No-word (Stopword Filtering)**: `이름 마크 전화번호 010-1234-5678`
    *   *Particles (은, 는, 이고, 입니다) are removed to isolate the data.*
4.  **Regex Matching**: `010-1234-5678`
    *   *The pattern is now clearly visible and matched.*
5.  **Verification**: `Data Check (Valid)`
    *   *The extracted number is verified against format rules.*

Install NLP dependencies:
```bash
pip install data-detector[nlp]
```

See [NLP Features Documentation](docs/nlp-features.md) for more details.

### CLI Usage

```bash
# Find PII in text
data-detector find --text "010-1234-5678" --ns kr

# Redact a file
data-detector redact --in input.log --out redacted.log

# Start a REST API server
data-detector serve --port 8080
```

## CLI Commands & Options

| Command | Description | Key Options |
| :--- | :--- | :--- |
| `find` | Search for PII in text or files. | `--text`, `--in`, `--ns` (namespace) |
| `redact` | Mask or tokenize sensitive data. | `--in`, `--out`, `--format` |
| `validate` | Validate text against a pattern. | `--text`, `--pattern-id` |
| `list-patterns`| Show all available PII patterns. | `--ns`, `--category` |
| `serve` | Run as an HTTP/gRPC server. | `--port`, `--host`, `--workers` |

Use `data-detector --help` for a full list of options.

## Chrome Extension

Monitor PII in real-time as you browse with the **PII Detector Chrome Extension**. It uses a hybrid approach combining fast client-side pattern matching with the Data-Detector API for accurate verification.

### Features

- **Multi-Source Monitoring**: Detect PII in form inputs, page content, and network requests
- **Real-Time Alerts**: Visual highlights and notifications when PII is detected
- **Privacy-Preserving**: Never stores actual PII values, only metadata
- **Hybrid Detection**: Fast client-side matching with API verification for accuracy
- **Offline Fallback**: Continues working even when API is unavailable

### Quick Setup

1. **Start the API Server**:
   ```bash
   data-detector serve --port 8080
   ```

2. **Load the Extension**:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked" and select the `chrome-extension` directory

3. **Configure Settings**:
   - Click the extension icon
   - Go to Settings
   - Verify API endpoint is `http://localhost:8080`
   - Select namespaces (e.g., `comm`, `us`, `kr`)

For detailed instructions, architecture, and troubleshooting, see the [Chrome Extension README](chrome-extension/README.md).

## Documentation

For detailed guides and references, please see the following:

- **Guides**: [Quick Start](docs/quickstart.md) | [Architecture](docs/ARCHITECTURE.md) | [Configuration](docs/configuration.md)
- **Patterns**: [Supported Patterns](docs/supported-patterns.md) | [Custom Patterns](docs/custom-patterns.md) | [Pattern Structure](docs/patterns.md)
- **Features**: [NLP Processing](docs/nlp-features.md) | [Fake Data Generation](docs/yaml_utilities.md) | [RAG Security](docs/rag-integration.md) | [Verification Functions](docs/verification.md)
- **API**: [API Reference](docs/api-reference.md)

## CI/CD Integration

Data Detector can be integrated into your CI/CD pipeline to automatically block PII leaks.

- **Guide**: [CI/CD Integration Guide](docs/guides/cicd-integration.md)
- **Example Script**: [examples/cicd_scan.sh](examples/cicd_scan.sh)

```bash
# Example: Fail build if PII is found in changed files
data-detector find --file "changed_file.py" --on-match exit
```

## License

MIT License - see [LICENSE](LICENSE) file for details.