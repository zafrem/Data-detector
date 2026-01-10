"""
NLP utilities for improved PII detection in multi-language contexts.

This module provides language detection, tokenization, and stopword filtering
to improve PII detection accuracy, especially for languages like Korean where
grammatical particles are attached to PII without spaces.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml

from datadetector import regex_compat

logger = logging.getLogger(__name__)

# Optional imports with graceful degradation
try:
    import langdetect

    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    logger.debug("langdetect not available - language detection disabled")

try:
    from konlpy.tag import Okt

    KONLPY_AVAILABLE = True
except ImportError:
    KONLPY_AVAILABLE = False
    logger.debug("konlpy not available - Korean tokenization disabled")

try:
    import jieba
    import jieba.posseg as pseg

    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.debug("jieba not available - Chinese tokenization disabled")

try:
    from sudachipy import dictionary, tokenizer

    SUDACHI_AVAILABLE = True
except ImportError:
    SUDACHI_AVAILABLE = False
    logger.debug("sudachipy not available - Japanese tokenization disabled")


class NLPFeature(str, Enum):
    """NLP feature flags."""

    LANGUAGE_DETECTION = "language_detection"
    TOKENIZATION = "tokenization"
    STOPWORD_FILTERING = "stopword_filtering"
    KOREAN_PARTICLE_PROCESSING = "korean_particle_processing"
    CHINESE_SEGMENTATION = "chinese_segmentation"
    JAPANESE_SEGMENTATION = "japanese_segmentation"


@dataclass
class NLPConfig:
    """
    Configuration for NLP preprocessing features.

    All features are disabled by default for backwards compatibility.
    Enable only the features you need for your use case.
    """

    # Enable language detection (requires langdetect)
    enable_language_detection: bool = False

    # Enable tokenization (requires konlpy for Korean, jieba for Chinese)
    enable_tokenization: bool = False

    # Enable stopword filtering (removes common words like particles)
    enable_stopword_filtering: bool = False

    # Enable Korean particle processing (requires konlpy)
    # Processes particles like 은/는/이/가/을/를/와/과/도/만 etc.
    enable_korean_particles: bool = False

    # Enable Chinese word segmentation (requires jieba)
    # Chinese doesn't use spaces, so segmentation is essential
    enable_chinese_segmentation: bool = False

    # Enable Japanese word segmentation (requires sudachipy)
    # Japanese doesn't use spaces, so segmentation is essential
    enable_japanese_segmentation: bool = False

    # Custom stopwords to add (in addition to defaults)
    custom_stopwords: Set[str] = field(default_factory=set)

    # Preferred Korean tokenizer backend (okt, komoran, mecab, hannanum, kkma)
    korean_tokenizer: str = "okt"

    def is_enabled(self) -> bool:
        """Check if any NLP feature is enabled."""
        return (
            self.enable_language_detection
            or self.enable_tokenization
            or self.enable_stopword_filtering
            or self.enable_korean_particles
            or self.enable_chinese_segmentation
        )

    def validate(self) -> None:
        """Validate configuration and check dependencies."""
        if self.enable_language_detection and not LANGDETECT_AVAILABLE:
            raise ImportError(
                "Language detection requires 'langdetect' package. "
                "Install with: pip install langdetect"
            )

        if (
            self.enable_korean_particles or (self.enable_tokenization and not JIEBA_AVAILABLE)
        ) and not KONLPY_AVAILABLE:
            logger.warning(
                "Korean processing requires 'konlpy' package. "
                "Install with: pip install konlpy. "
                "Falling back to basic tokenization."
            )

        if self.enable_chinese_segmentation and not JIEBA_AVAILABLE:
            logger.warning(
                "Chinese segmentation requires 'jieba' package. "
                "Install with: pip install jieba. "
                "Falling back to basic tokenization."
            )

        if self.enable_japanese_segmentation and not SUDACHI_AVAILABLE:
            logger.warning(
                "Japanese segmentation requires 'sudachipy' and 'sudachidict_core' packages. "
                "Install with: pip install sudachipy sudachidict_core. "
                "Falling back to basic tokenization."
            )


def _load_default_stopwords() -> Dict[str, Set[str]]:
    """Load default stopwords from pattern-engine YAML file."""
    try:
        # Determine path to stopwords.yml
        # src/datadetector/nlp.py -> ... -> pattern-engine/keyword/stopwords.yml
        root = Path(__file__).parent.parent.parent
        
        # Check potential locations
        possible_paths = [
            root / "pattern-engine" / "keyword" / "stopwords.yml",
            root / "pattern-engine" / "keyword" / "stopwords.yaml",
            # Fallback for installed package if patterns are packaged differently
            Path(__file__).parent / "patterns" / "keyword" / "stopwords.yml", 
        ]
        
        yaml_path = None
        for path in possible_paths:
            if path.exists():
                yaml_path = path
                break
        
        if not yaml_path:
            logger.warning("stopwords.yml not found, using empty defaults")
            return {}

        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
        stopwords = {}
        if data and "stopwords" in data:
            for lang, content in data["stopwords"].items():
                if "words" in content:
                    stopwords[lang] = set(content["words"])
        
        return stopwords

    except Exception as e:
        logger.error(f"Failed to load stopwords: {e}")
        return {}


# Load default stopwords
_STOPWORDS_DATA = _load_default_stopwords()
KOREAN_STOPWORDS = _STOPWORDS_DATA.get("ko", set())
ENGLISH_STOPWORDS = _STOPWORDS_DATA.get("en", set())
CHINESE_STOPWORDS = _STOPWORDS_DATA.get("zh", set())
JAPANESE_STOPWORDS = _STOPWORDS_DATA.get("ja", set())



class LanguageDetector:
    """Detects the language of input text."""

    def __init__(self) -> None:
        if not LANGDETECT_AVAILABLE:
            raise ImportError("langdetect package required for language detection")

    def detect(self, text: str) -> Optional[str]:
        """
        Detect language of text.

        Returns:
            ISO 639-1 language code (e.g., 'ko', 'en', 'ja') or None if detection fails
        """
        if not text or not text.strip():
            return None

        try:
            return langdetect.detect(text)
        except Exception as e:
            logger.debug(f"Language detection failed: {e}")
            return None


class StopwordFilter:
    """Filters stopwords from text."""

    def __init__(self, custom_stopwords: Optional[Set[str]] = None):
        """
        Initialize stopword filter.

        Args:
            custom_stopwords: Additional stopwords to filter
        """
        self.stopwords = KOREAN_STOPWORDS | ENGLISH_STOPWORDS | CHINESE_STOPWORDS | JAPANESE_STOPWORDS
        if custom_stopwords:
            self.stopwords |= custom_stopwords

    def filter_tokens(self, tokens: List[str]) -> List[str]:
        """Remove stopwords from token list."""
        return [
            token
            for token in tokens
            if token.lower() not in self.stopwords and token not in self.stopwords
        ]

    def is_stopword(self, word: str) -> bool:
        """Check if a word is a stopword."""
        return word.lower() in self.stopwords or word in self.stopwords


class KoreanTokenizer:
    """Korean-aware tokenizer using konlpy."""

    def __init__(self, backend: str = "okt"):
        """
        Initialize Korean tokenizer.

        Args:
            backend: Tokenizer backend (okt, komoran, mecab, hannanum, kkma)
        """
        if not KONLPY_AVAILABLE:
            raise ImportError("konlpy package required for Korean tokenization")

        self.backend = backend
        if backend == "okt":
            self.tokenizer = Okt()
        else:
            # Support for other backends can be added here
            logger.warning(f"Backend {backend} not implemented, using Okt")
            self.tokenizer = Okt()

    def tokenize(self, text: str, include_pos: bool = False) -> List[str]:
        """
        Tokenize Korean text.

        Args:
            text: Input text
            include_pos: Include part-of-speech tags

        Returns:
            List of tokens (or token/pos tuples if include_pos=True)
        """
        if include_pos:
            return self.tokenizer.pos(text)
        return self.tokenizer.morphs(text)

    def extract_nouns(self, text: str) -> List[str]:
        """Extract only nouns from text."""
        return self.tokenizer.nouns(text)

    def remove_particles(self, text: str) -> str:
        """
        Remove Korean particles from text.

        This helps with matching PII that has particles attached.
        Example: "010-1234-5678은" -> "010-1234-5678"
        """
        # Get morphemes with POS tags
        morphs: List[Tuple[str, str]] = self.tokenizer.pos(text)

        # Filter out particles (Josa in Korean POS tagging)
        filtered: List[str] = []
        for morph, pos in morphs:
            # Keep everything except particles (Josa)
            if pos != "Josa":
                filtered.append(morph)

        return " ".join(filtered)


class ChineseTokenizer:
    """Chinese word segmentation using jieba."""

    def __init__(self) -> None:
        """Initialize Chinese tokenizer."""
        if not JIEBA_AVAILABLE:
            raise ImportError("jieba package required for Chinese tokenization")

        # Set jieba to quiet mode to avoid initialization messages
        jieba.setLogLevel(logging.INFO)

    def tokenize(self, text: str, include_pos: bool = False) -> List[str]:
        """
        Tokenize Chinese text.

        Args:
            text: Input text
            include_pos: Include part-of-speech tags

        Returns:
            List of tokens (or token/pos tuples if include_pos=True)
        """
        if include_pos:
            # Returns list of (word, pos) tuples
            return [(w.word, w.flag) for w in pseg.cut(text)]  # type: ignore[misc]
        return list(jieba.cut(text))

    def tokenize_search(self, text: str) -> List[str]:
        """
        Tokenize for search mode (finer granularity).

        This mode splits compound words for better search matching.
        """
        return list(jieba.cut_for_search(text))

    def extract_keywords(self, text: str, topk: int = 10) -> List[str]:
        """
        Extract keywords from text using TF-IDF.

        Args:
            text: Input text
            topk: Number of top keywords to return

        Returns:
            List of keywords
        """
        import jieba.analyse

        return jieba.analyse.extract_tags(text, topK=topk)

    def add_word(self, word: str, freq: Optional[int] = None, tag: Optional[str] = None) -> None:
        """
        Add custom word to dictionary.

        This is useful for domain-specific terms or PII patterns.

        Args:
            word: Word to add
            freq: Word frequency (higher = more likely to be segmented as single word)
            tag: Part-of-speech tag
        """
        jieba.add_word(word, freq, tag)


class JapaneseTokenizer:
    """Japanese word segmentation using sudachipy."""

    def __init__(self, mode: str = "C") -> None:
        """
        Initialize Japanese tokenizer.

        Args:
            mode: Splitting mode:
                - 'A': Shortest units (similar to UniDic)
                - 'B': Middle units
                - 'C': Longest units (compound words, default)
        """
        if not SUDACHI_AVAILABLE:
            raise ImportError("sudachipy and sudachidict_core required for Japanese tokenization")

        self.tokenizer_obj = dictionary.Dictionary().create()
        self.mode = mode
        if mode == "A":
            self.split_mode = tokenizer.Tokenizer.SplitMode.A
        elif mode == "B":
            self.split_mode = tokenizer.Tokenizer.SplitMode.B
        else:
            self.split_mode = tokenizer.Tokenizer.SplitMode.C

    def tokenize(self, text: str, include_pos: bool = False) -> List[str]:
        """
        Tokenize Japanese text.

        Args:
            text: Input text
            include_pos: Include part-of-speech tags

        Returns:
            List of tokens (or token/pos tuples if include_pos=True)
        """
        if not text:
            return []

        tokens = self.tokenizer_obj.tokenize(text, self.split_mode)

        if include_pos:
            # pos_info() returns list like ['名詞', '固有名詞', '*', '*', '*', '*']
            # We take the first two as a representative tag
            return [(t.surface(), "/".join(t.part_of_speech()[:2])) for t in tokens]

        return [t.surface() for t in tokens]

    def extract_nouns(self, text: str) -> List[str]:
        """Extract only nouns from text."""
        tokens = self.tokenizer_obj.tokenize(text, self.split_mode)
        return [t.surface() for t in tokens if t.part_of_speech()[0] == "名詞"]


class SmartTokenizer:
    """
    A smart tokenizer that handles script boundaries (e.g., Latin/Number <-> CJK).

    This is useful for languages like Korean, Chinese, or Japanese where PII
    (often in ASCII/Numbers) is attached directly to grammatical particles
    (in CJK scripts) without spaces.

    Example:
        "010-1234-5678을" -> "010-1234-5678 을"
    """

    # Regex to find transitions between:
    # 1. ASCII/Number (ends with \w or digit) -> CJK (starts with non-ascii/non-punct)
    # 2. CJK -> ASCII/Number

    # Simple heuristic:
    # Detect PII-like characters (Latin, Numbers, common separators like - . @)
    # vs "Other" characters (Hangul, Hanzi, Kana, etc.)

    PII_CHARS = r"[a-zA-Z0-9\-\.\@\+\_\:\/]"
    NON_PII_CHARS = r"[^a-zA-Z0-9\-\.\@\+\_\:\/\s]"

    # Pre-compiled pattern for PII character matching
    _PII_PATTERN = regex_compat.compile(PII_CHARS)

    def __init__(self) -> None:
        self._cache: Dict[str, Tuple[str, List[int]]] = {}

    def prepare_text_for_search(self, text: str) -> Tuple[str, List[int]]:
        """
        Prepares text for regex searching by inserting spaces at script boundaries.

        Returns:
            Tuple[str, List[int]]:
                - The modified text with spaces inserted.
                - A mapping list where map[i] = original_index_of_char_at_i
        """
        if not text:
            return "", []

        # We will build a new string and a mapping
        # This is an O(N) operation

        # Optimization: If text is pure ASCII, return as is
        if text.isascii():
            return text, list(range(len(text)))

        result_chars = []
        original_indices = []

        prev_type = None  # 0: PII-safe, 1: Other (CJK etc), 2: Space/Punct

        for i, char in enumerate(text):
            # Determine character type
            curr_type = 2
            if char.isspace():
                curr_type = 2
            elif self._PII_PATTERN.match(char):
                curr_type = 0
            elif ord(char) > 127:  # Rough check for CJK/Unicode
                curr_type = 1
            else:
                curr_type = 2  # Other ascii punctuation

            # Insert space if transition between 0 <-> 1
            if prev_type is not None:
                if (prev_type == 0 and curr_type == 1) or (prev_type == 1 and curr_type == 0):
                    result_chars.append(" ")
                    original_indices.append(-1)  # -1 indicates inserted char

            result_chars.append(char)
            original_indices.append(i)
            prev_type = curr_type

        return "".join(result_chars), original_indices

    def map_match_to_original(
        self, match_start: int, match_end: int, mapping: List[int]
    ) -> Tuple[int, int]:
        """
        Maps the start/end indices from the prepared text back to the original text.
        """
        if not mapping:
            return 0, 0

        # Handle edge cases where match extends slightly beyond mapped range
        safe_end = min(match_end, len(mapping))
        safe_start = min(match_start, len(mapping) - 1)

        orig_start = mapping[safe_start]

        # For end, we need to look at the character *before* the end index in the result string
        # because 'end' is exclusive.
        # But since we inserted spaces, we might land on a -1.
        # We scan backwards to find the last real character included in the match.

        orig_end_idx = safe_end - 1
        while orig_end_idx >= 0 and mapping[orig_end_idx] == -1:
            orig_end_idx -= 1

        if orig_end_idx < 0:
            return 0, 0

        # The original end is the index of that character + 1
        orig_end = mapping[orig_end_idx] + 1

        # If the start was a virtual space (unlikely for a match start), adjust
        while orig_start == -1 and safe_start < len(mapping) - 1:
            safe_start += 1
            orig_start = mapping[safe_start]

        return orig_start, orig_end


@dataclass
class PreprocessedText:
    """
    Result of NLP preprocessing.

    Contains the processed text along with mappings to restore original positions.
    """

    # Processed text (with spaces inserted, stopwords removed, etc.)
    processed_text: str

    # Original text
    original_text: str

    # Mapping from processed text indices to original text indices
    # mapping[i] = original index of character at position i in processed text
    # -1 indicates an inserted character (e.g., space at script boundary)
    index_mapping: List[int]

    # Detected language (if language detection was enabled)
    detected_language: Optional[str] = None

    # Tokens (if tokenization was enabled)
    tokens: Optional[List[str]] = None

    def map_to_original(self, start: int, end: int) -> Tuple[int, int]:
        """Map processed text positions back to original text positions."""
        if not self.index_mapping:
            return start, end

        tokenizer = SmartTokenizer()
        return tokenizer.map_match_to_original(start, end, self.index_mapping)


class NLPProcessor:
    """
    Main NLP processor that combines language detection, tokenization,
    and stopword filtering.
    """

    def __init__(self, config: Optional[NLPConfig] = None) -> None:
        """
        Initialize NLP processor.

        Args:
            config: NLP configuration. If None, all features are disabled.
        """
        self.config = config or NLPConfig()
        self.config.validate()

        # Initialize components based on config
        self.language_detector: Optional[LanguageDetector] = None
        if self.config.enable_language_detection:
            try:
                self.language_detector = LanguageDetector()
            except ImportError:
                logger.warning("Language detection disabled - langdetect not available")

        self.korean_tokenizer = None
        if self.config.enable_korean_particles or self.config.enable_tokenization:
            try:
                self.korean_tokenizer = KoreanTokenizer(self.config.korean_tokenizer)
            except ImportError:
                logger.warning("Korean tokenization disabled - konlpy not available")

        self.chinese_tokenizer = None
        if self.config.enable_chinese_segmentation or self.config.enable_tokenization:
            try:
                self.chinese_tokenizer = ChineseTokenizer()
            except ImportError:
                logger.warning("Chinese tokenization disabled - jieba not available")

        self.japanese_tokenizer = None
        if self.config.enable_japanese_segmentation or self.config.enable_tokenization:
            try:
                self.japanese_tokenizer = JapaneseTokenizer()
            except ImportError:
                logger.warning("Japanese tokenization disabled - sudachipy not available")

        self.stopword_filter = None
        if self.config.enable_stopword_filtering:
            self.stopword_filter = StopwordFilter(self.config.custom_stopwords)

        self.smart_tokenizer = SmartTokenizer()

    def preprocess(self, text: str) -> PreprocessedText:
        """
        Preprocess text with enabled NLP features.

        Args:
            text: Input text

        Returns:
            PreprocessedText with processed text and metadata
        """
        if not text:
            return PreprocessedText(processed_text="", original_text="", index_mapping=[])

        # Detect language if enabled
        detected_lang = None
        if self.config.enable_language_detection and self.language_detector:
            detected_lang = self.language_detector.detect(text)
            logger.debug(f"Detected language: {detected_lang}")

        # Process Korean particles if enabled
        processed_text = text
        if self.config.enable_korean_particles and self.korean_tokenizer:
            if detected_lang == "ko" or detected_lang is None:
                # Only process if Korean or language unknown
                processed_text = self.korean_tokenizer.remove_particles(processed_text)

        # Apply smart tokenization (script boundary detection)
        prepared_text, mapping = self.smart_tokenizer.prepare_text_for_search(processed_text)

        # Tokenize if enabled
        tokens = None
        if self.config.enable_tokenization:
            if detected_lang == "ko" and self.korean_tokenizer:
                tokens = self.korean_tokenizer.tokenize(prepared_text)
            elif detected_lang == "zh-cn" and self.chinese_tokenizer:
                # Chinese detected - use jieba for segmentation
                tokens = self.chinese_tokenizer.tokenize(prepared_text)
            elif detected_lang == "ja" and self.japanese_tokenizer:
                # Japanese detected - use sudachipy for segmentation
                tokens = self.japanese_tokenizer.tokenize(prepared_text)
            elif self.config.enable_chinese_segmentation and self.chinese_tokenizer:
                # Force Chinese segmentation even if language not detected
                tokens = self.chinese_tokenizer.tokenize(prepared_text)
            elif self.config.enable_japanese_segmentation and self.japanese_tokenizer:
                # Force Japanese segmentation even if language not detected
                tokens = self.japanese_tokenizer.tokenize(prepared_text)
            else:
                # Basic whitespace tokenization for other languages
                tokens = prepared_text.split()

            # Filter stopwords if enabled
            if self.config.enable_stopword_filtering and self.stopword_filter:
                tokens = self.stopword_filter.filter_tokens(tokens)

        return PreprocessedText(
            processed_text=prepared_text,
            original_text=text,
            index_mapping=mapping,
            detected_language=detected_lang,
            tokens=tokens,
        )
