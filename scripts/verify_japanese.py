import logging
import sys

# Configure logging to show what's happening
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("datadetector")

try:
    from datadetector import Engine, load_registry, NLPConfig
    from datadetector.nlp import JapaneseTokenizer
except ImportError:
    print("Error: data-detector not installed or path incorrect.")
    sys.exit(1)

def verify_japanese_support():
    print("=== 1. Verifying Sentence Separation (Tokenization) ===")
    
    text = "私の電話番号は090-1234-5678です"
    print(f"Original Text: '{text}'")

    # Initialize Tokenizer directly to show separation
    try:
        tokenizer = JapaneseTokenizer()
        tokens = tokenizer.tokenize(text)
        print(f"Separated/Tokenized: {tokens}")
        print("✅ JapaneseTokenizer loaded and working.")
    except ImportError:
        print("❌ sudachipy not installed. Skipping direct tokenization check.")
    except Exception as e:
        print(f"❌ Tokenization failed: {e}")

    print("\n=== 2. Verifying Regex Detection with NLP Engine ===")
    
    # Configure NLP as described in README
    nlp_config = NLPConfig(
        enable_language_detection=True,
        enable_japanese_segmentation=True
    )

    try:
        registry = load_registry()
        engine = Engine(registry, nlp_config=nlp_config)
        
        # Run detection
        results = engine.find(text, namespaces=["jp"])
        
        if results.matches:
            print(f"✅ Detection Successful! Found {len(results.matches)} match(es).")
            for i, match in enumerate(results.matches):
                print(f"   Match #{i+1}:")
                print(f"     - Type: {match.pattern_id}")
                # Use matched_text if available, otherwise extract from original text
                val = match.matched_text if match.matched_text else text[match.start:match.end]
                print(f"     - Value: '{val}'")
                print(f"     - Score: {match.score}")
                
                # Verify exact PII extraction
                if val == "090-1234-5678":
                    print("     - Verified: Extracted text matches expected PII exactly.")
                else:
                    print(f"     - Warning: Extracted text '{val}' != '090-1234-5678'")
        else:
            print("❌ No matches found. Regex or NLP failed.")
            
    except Exception as e:
        print(f"❌ Engine execution failed: {e}")

if __name__ == "__main__":
    verify_japanese_support()
