"""
data-detector: A general-purpose engine for detecting and masking personal information.

This package provides tools for PII detection, validation, and redaction using
pattern-based matching organized by country and information type.
"""

__version__ = "0.0.2"

from datadetector import context_presets
from datadetector.async_engine import AsyncEngine
from datadetector.bulk_generator import BulkDataGenerator
from datadetector.context import (
    ContextFilter,
    ContextHint,
    KeywordRegistry,
    create_context_from_field_name,
)
from datadetector.engine import Engine
from datadetector.fake_file_generators import (
    ImageGenerator,
    OfficeFileGenerator,
    PDFGenerator,
    XMLGenerator,
)
from datadetector.fake_generator import FakeDataGenerator
from datadetector.models import FindResult, RedactionResult, ValidationResult
from datadetector.nlp import (
    ChineseTokenizer,
    KoreanTokenizer,
    LanguageDetector,
    NLPConfig,
    NLPProcessor,
    PreprocessedText,
    SmartTokenizer,
    StopwordFilter,
)
from datadetector.rag_config import RAGPolicyConfig, load_rag_policy
from datadetector.rag_middleware import RAGSecurityMiddleware
from datadetector.rag_models import (
    SecurityAction,
    SecurityLayer,
    SecurityPolicy,
    SeverityLevel,
)
from datadetector.regex_compat import RegexEngine, get_engine, set_engine
from datadetector.registry import PatternRegistry, load_registry
from datadetector.stream_engine import StreamEngine
from datadetector.tokenization import SecureTokenizer
from datadetector.utils.yaml_utils import (
    PatternFileHandler,
    YAMLHandler,
    read_yaml,
    update_yaml,
    write_yaml,
)

__all__ = [
    "Engine",
    "AsyncEngine",
    "load_registry",
    "PatternRegistry",
    "FindResult",
    "ValidationResult",
    "RedactionResult",
    "FakeDataGenerator",
    "BulkDataGenerator",
    "OfficeFileGenerator",
    "ImageGenerator",
    "PDFGenerator",
    "XMLGenerator",
    "YAMLHandler",
    "PatternFileHandler",
    "read_yaml",
    "write_yaml",
    "update_yaml",
    # Context-aware filtering
    "ContextHint",
    "ContextFilter",
    "KeywordRegistry",
    "create_context_from_field_name",
    "context_presets",
    # NLP Processing
    "NLPConfig",
    "NLPProcessor",
    "LanguageDetector",
    "StopwordFilter",
    "KoreanTokenizer",
    "ChineseTokenizer",
    "SmartTokenizer",
    "PreprocessedText",
    # RAG Security
    "RAGSecurityMiddleware",
    "StreamEngine",
    "SecureTokenizer",
    "SecurityAction",
    "SecurityLayer",
    "SecurityPolicy",
    "SeverityLevel",
    "RAGPolicyConfig",
    "load_rag_policy",
    # Regex engine configuration
    "RegexEngine",
    "set_engine",
    "get_engine",
]
