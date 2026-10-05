# -*- coding: utf-8 -*-
"""Pipeline 1 core — 寬容數字解析 (Tolerant Number Parsing) + 語意模糊比對.

Two stages, deliberately ordered by reliability:

1. extract_option_index — pull an explicit choice number out of the student
   input ("3", "第三個", "我選二", "答案是4" ...).
2. fuzzy_match_option — when no number is present, compare the input against
   the four option texts with a folding-aware similarity, so that
   speech-recognition slips (臺/台, 裡/裏, homophones, dropped particles) still
   land on the intended option.

Everything here is pure and deterministic — no network, no LLM, no state. That
is what makes the offline fallback in src.evaluator trustworthy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Sequence

__all__ = [
    'MatchResult',
    'normalize',
    'fold_variants',
    'fold_homophones',
    'extract_option_index',
    'fuzzy_match_option',
    'combine_signals',
    'format_options',
    'MIN_CONFIDENCE',
    'AMBIGUITY_MARGIN',
    'fold_relaxed',
]

DEFAULT_OPTION_COUNT = 4

#: Below this score a fuzzy match is treated as "no idea", not a guess.
MIN_CONFIDENCE = 0.55

#: An earlier revision auto-accepted a lower tier when the leader was far
#: ahead. Measured on the benchmark it converted honest abstentions into
#: *confidently wrong* picks on 背影 Q6, so it was removed: below MIN_CONFIDENCE
#: the parser abstains and offers the runner-up as a confirmation instead.

#: If the top two options score within this gap the match is ambiguous; we ask
#: the student again instead of silently picking one for them.
AMBIGUITY_MARGIN = 0.08


# --- number tables ----------------------------------------------------------

#: Digits plus the Chinese numerals a 國小六年級 student actually uses.
NUMBER_CHARS: dict[str, int] = {
    '1': 1, '2': 2, '3': 3, '4': 4,
    '１': 1, '２': 2, '３': 3, '４': 4,
    '一': 1, '二': 2, '三': 3, '四': 4, '兩': 2,
}

_CN_DIGIT = '[1234１-４一二三四兩]'

# Punctuation / whitespace that carries no meaning for a choice.
_NOISE_RE = re.compile(
    r'[\s,，。、；;：:！!？?．.·…—\-–_()（）「」『』《》〈〉“”‘’~]+'
)

#: Orthographic variants folded to one canonical character. Applied to BOTH the
#: student input and the option text, so 臺/台 become interchangeable without
#: changing which option wins. Article 2 legitimately says 「台糖」and article 4
#: legitimately says 「臺灣」 — folding makes that difference irrelevant.
VARIANT_FOLD: dict[int, str] = {
    ord('臺'): '台',
    ord('颱'): '台',
    ord('裏'): '里',
    ord('裡'): '里',
}

#: Small, deliberately conservative homophone groups. Used only to nudge scores
#: (see _pair_similarity), never as a hard text replacement, so folding can never
#: manufacture a confident match out of nothing.
HOMOPHONE_GROUPS: tuple[str, ...] = (
    '的得地',
    '是事市式試',
    '在再載',
    '有友又右',
    '就救舊',
    '個各哥',
    '聽厅停亭',
    '聲生升',
    '看刊砍',
    '會回灰',
    '不布步部補',
    '己已以椅',
    '道德很',
    '感減',
)

#: Semantic near-synonyms a sixth grader substitutes freely. A student says
#: 「爸爸」, the option says 「父親」 — without this, a correct paraphrase scores
#: near zero because the two words share no characters at all.
SYNONYM_GROUPS: tuple[str, ...] = (
    '父親',      # 爸爸 / 父親
    '母親',      # 媽媽 / 母親
    '番茄',      # 西紅柿 / 番茄
    '冰棒',      # 冰棍 / 冰棒
    '誇張',      # 夸張 / 誇張
)

_SYNONYM_FOLD: dict[int, str] = {}
for _group in SYNONYM_GROUPS:
    _canonical = _group[0]
    for _ch in _group:
        _SYNONYM_FOLD.setdefault(ord(_ch), _canonical)


_HOMOPHONE_FOLD: dict[int, str] = {}
for _group in HOMOPHONE_GROUPS:
    _canonical = _group[0]
    for _ch in _group:
        _HOMOPHONE_FOLD.setdefault(ord(_ch), _canonical)


def normalize(text: str) -> str:
    """Lowercase, unify full-width digits, drop punctuation and whitespace.

    Every CJK character survives — only noise is removed.
    """
    if not text:
        return ''
    lowered = text.strip().lower()
    unified = lowered.translate({0xFF10 + i: ord(str(i)) for i in range(10)})
    return _NOISE_RE.sub('', unified)


def fold_variants(text: str) -> str:
    """Apply 臺/台・裡/裏 style orthographic folding."""
    return text.translate(VARIANT_FOLD)


def fold_homophones(text: str) -> str:
    """Apply conservative homophone folding, used only for scoring nudges."""
    return text.translate(_HOMOPHONE_FOLD)


def fold_relaxed(text: str) -> str:
    """Fold homophones *and* near-synonyms — used only inside the scoring nudge."""
    return fold_homophones(text).translate(_SYNONYM_FOLD)


# --- stage 1: explicit number extraction ------------------------------------

# A cued form ("第3個", "我選二", "答案是4") is unambiguous.
_CUED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(rf'第\s*({_CN_DIGIT})'),
    re.compile(rf'({_CN_DIGIT})\s*(?:個|項|款|條|選|的)'),
    re.compile(
        rf'(?:選|選的是|答案是|答|我選|我說|我猜|正確|對)\s*(?:是)?\s*({_CN_DIGIT})'
    ),
)

# A bare Arabic digit must be *isolated*, otherwise 「十五萬」recognised as "15萬"
# would silently look like option 1.
_AR_DIGIT_RE = re.compile(r'(?<![0-9])([1234１-４])(?![0-9])')
_DIGIT_RUN_RE = re.compile(r'[0-9]{2,}')

# The whole answer being a single token, e.g. "3" / "三" / "３." — here a Chinese
# numeral IS the choice, so this regex deliberately accepts 一二三四兩.
_BARE_RE = re.compile(rf'^({_CN_DIGIT})$')


def extract_option_index(
    raw: str, option_count: int = DEFAULT_OPTION_COUNT
) -> tuple[int | None, str]:
    """Return (zero_based_index, how) for an explicit choice, else (None, "").

    'how' records which strategy fired, so the UI can explain why an option was
    chosen — a small transparency win in a classroom tool.
    """
    normalized = normalize(raw)
    if not normalized:
        return None, ''

    for pattern in _CUED_PATTERNS:
        match = pattern.search(normalized)
        if match:
            index = NUMBER_CHARS.get(match.group(1))
            if index is not None and 1 <= index <= option_count:
                return index - 1, 'cued'

    # The entire answer is just the token, e.g. "3" / "3." / "三".
    if len(normalized) <= 2:  # short enough to be nothing but a choice
        match = _BARE_RE.match(normalized)
        if match:
            index = NUMBER_CHARS.get(match.group(1))
            if index is not None and 1 <= index <= option_count:
                return index - 1, 'bare'

    # An isolated Arabic digit, but only when no multi-digit run exists
    # anywhere in the answer ("15萬" must never be read as option 1).
    if not _DIGIT_RUN_RE.search(normalized):
        match = _AR_DIGIT_RE.search(normalized)
        if match:
            index = NUMBER_CHARS.get(match.group(1))
            if index is not None and 1 <= index <= option_count:
                return index - 1, 'isolated'

    return None, ''


# --- stage 2: fuzzy semantic matching ---------------------------------------


#: Function characters that carry grammar, not meaning. Stripped for the
#: character-level comparison only, so 「因為…的…」 wrappers cannot mask a match.
_STOP_CHARS = frozenset('的了是我你他她它在和跟與把被就都也很還有沒不那這個們'.replace(' ', ''))


def _content_chars(text: str) -> set[str]:
    return {ch for ch in text if ch not in _STOP_CHARS}


def _bigrams(text: str) -> set[str]:
    if len(text) < 2:
        return {text} if text else set()
    return {text[i: i + 2] for i in range(len(text) - 1)}


def _dice(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return (2.0 * len(left & right)) / (len(left) + len(right))


def _containment(needle: set[str], haystack: set[str]) -> float:
    """How much of the smaller set is covered by the larger one."""
    if not needle or not haystack:
        return 0.0
    return len(needle & haystack) / min(len(needle), len(haystack))


def _ratio(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _pair_similarity(input_norm: str, option_norm: str) -> float:
    """Similarity of one (input, option) pair, in [0, 1].

    A sixth grader rarely reads an option verbatim — they paraphrase ("父親很
    累卻還是愛我" for 「被父親雖然動作吃力卻依然愛自己的心意所感動」). So the
    score blends four signals rather than leaning on any single one:

      * edit ratio              — catches near-verbatim answers
      * bigram dice             — catches shared word-like units
      * bigram containment      — catches a short answer naming a long option
      * content-character dice  — catches CJK paraphrase, where several
                                   characters are shared but no bigram is
    """
    if not input_norm or not option_norm:
        return 0.0

    in_bigrams = _bigrams(input_norm)
    opt_bigrams = _bigrams(option_norm)
    in_chars = _content_chars(input_norm)
    opt_chars = _content_chars(option_norm)

    direct = max(
        _ratio(input_norm, option_norm),
        _dice(in_bigrams, opt_bigrams),
        _containment(in_bigrams, opt_bigrams) * 0.92,
        _dice(in_chars, opt_chars),
    )

    folded_input = fold_relaxed(input_norm)
    folded_option = fold_relaxed(option_norm)
    if folded_input != input_norm or folded_option != option_norm:
        folded = _pair_similarity_base(folded_input, folded_option)
        # Relaxed folding may only raise the score, and only a little — an
        # aggressive fold must never manufacture a confident match.
        direct = min(1.0, direct + 0.18 * (folded - direct))

    return direct


def _pair_similarity_base(input_norm: str, option_norm: str) -> float:
    """_pair_similarity without the homophone nudge (used to avoid recursion)."""
    in_bigrams = _bigrams(input_norm)
    opt_bigrams = _bigrams(option_norm)
    return max(
        _ratio(input_norm, option_norm),
        _dice(in_bigrams, opt_bigrams),
        _containment(in_bigrams, opt_bigrams) * 0.92,
        _dice(_content_chars(input_norm), _content_chars(option_norm)),
    )



@dataclass(frozen=True)
class MatchResult:
    """Outcome of stage-2 fuzzy matching."""

    #: Option we are willing to act on, or None when unsure.
    index: int | None
    score: float
    how: str
    ranking: tuple[float, ...]
    #: Best candidate even when we abstained. The UI offers it as a
    #: "你是指這個答案嗎？" confirmation rather than silently accepting it —
    #: a quiet wrong answer is far worse for a student than a re-ask.
    suggestion: int | None = None

    @property
    def confident(self) -> bool:
        """True when an option was actually selected."""
        return self.index is not None

    @property
    def is_strong(self) -> bool:
        """True only for the high-confidence tier — drives the 'are you sure?' UI."""
        return self.index is not None and self.how == 'fuzzy'

    @property
    def margin(self) -> float:
        """Gap between the best and the runner-up."""
        if len(self.ranking) < 2:
            return 0.0
        return self.ranking[0] - self.ranking[1]


def fuzzy_match_option(
    raw: str,
    options: Sequence[str],
    threshold: float = MIN_CONFIDENCE,
    ambiguity_margin: float = AMBIGUITY_MARGIN,
) -> MatchResult:
    """Match free-form (possibly STT-corrupted) text to one option.

    When the top two options score within 'ambiguity_margin' the result is
    demoted to index=None so the student is asked again rather than handed a
    silent guess.
    """
    normalized_input = fold_variants(normalize(raw))
    if not normalized_input or not options:
        return MatchResult(None, 0.0, 'no-input', ())

    scores = [
        _pair_similarity(normalized_input, fold_variants(normalize(option)))
        for option in options
    ]
    ranking = tuple(sorted(scores, reverse=True))
    best_index = max(range(len(scores)), key=lambda i: scores[i])
    best_score = scores[best_index]
    margin = ranking[0] - ranking[1] if len(ranking) > 1 else 1.0

    if best_score < max(threshold, MIN_CONFIDENCE):
        return MatchResult(None, best_score, 'below-threshold', ranking, best_index)
    if margin < ambiguity_margin:
        return MatchResult(None, best_score, 'ambiguous', ranking, best_index)
    return MatchResult(best_index, best_score, 'fuzzy', ranking, best_index)


def combine_signals(
    raw: str,
    options: Sequence[str],
    threshold: float = MIN_CONFIDENCE,
) -> tuple[int | None, str, float]:
    """Run both stages in the documented order.

    Returns (index_or_None, how, score). Numbers win over text matching — that
    ordering is the whole point of 寬容數字解析.
    """
    index, how = extract_option_index(raw, len(options))
    if index is not None:
        return index, how, 1.0

    result = fuzzy_match_option(raw, options, threshold=threshold)
    return result.index, result.how, result.score


def format_options(options: Sequence[str]) -> str:
    """Render options the way the classroom card does: '1. ...  2. ...'."""
    return '　'.join(f'{i + 1}. {text}' for i, text in enumerate(options))
