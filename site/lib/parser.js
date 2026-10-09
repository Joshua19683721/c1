// Tolerant answer parsing for ReadExpress-CoT — browser build.
//
// A port of src/parser.py. The two implementations are deliberately NOT kept
// bit-identical: Python's difflib.SequenceMatcher is not reproducible in
// JavaScript, and float-equal string similarity is not a meaningful contract.
// What IS contractual is the behaviour, and tests/site/run_contract.mjs
// asserts the same guarantees on this file that tests/test_parser.py asserts
// on the Python one:
//
//   1. every option, read aloud, maps back to itself (200/200)
//   2. no confidently-wrong picks
//   3. unrelated answers are rejected
//   4. numbers inside a quoted answer are never read as a choice

const NUMBER_CHARS = {
  '1': 1, '2': 2, '3': 3, '4': 4,
  '\uff11': 1, '\uff12': 2, '\uff13': 3, '\uff14': 4,
  '\u4e00': 1, '\u4e8c': 2, '\u4e09': 3, '\u56db': 4, '\u4e24': 2,
};

const CN_DIGIT = '[1234\uff11-\uff14\u4e00\u4e8c\u4e09\u56db\u4e24]';

const MIN_CONFIDENCE = 0.55;
const AMBIGUITY_MARGIN = 0.08;
const DEFAULT_OPTION_COUNT = 4;

const NOISE_RE =
  /[\s,\u3002\uFF0C\u3001\uFF1B;\uFF1A:\uFF01!\uFF1F?\uFF0E.\u00b7\u2026\u2014\-\u2013_()\uFF08\uFF09\u300c\u300d\u300e\u300f\u300a\u300b\u3008\u3009\u201c\u201d\u2018\u2019~]+/g;

const VARIANT_FOLD = {
  '\u81fa': '\u53f0', // \u81fa -> \u53f0
  '\u98a8': '\u53f0', // \u98a8 -> \u53f0
  '\u88cf': '\u91cc', // \u88cf -> \u91cc
  '\u88e1': '\u91cc', // \u88e1 -> \u91cc
};

const HOMOPHONE_GROUPS = [
  '\u7684\u5f97\u5730', '\u662f\u4e8b\u5e02\u5f0f\u8a66', '\u5728\u518d\u8f09',
  '\u6709\u53cb\u53c8\u53f3', '\u5c31\u6551\u820a', '\u500b\u5404\u54e5',
  '\u807d\u5385\u505c\u4ead', '\u8072\u751f\u5347', '\u770b\u520a\u780d',
  '\u6703\u56de\u7070', '\u4e0d\u5e03\u6b65\u90e8\u88dc', '\u5df1\u5df2\u4ee5\u6905',
  '\u9053\u5fb7\u5f88', '\u611f\u51cf',
];

const SYNONYM_GROUPS = [
  '\u7236\u8ab0', '\u6bcd\u8a71', '\u756a\u8304', '\u51b0\u68d2', '\u5938\u5f35',
];

function buildFold(groups) {
  const table = {};
  for (const group of groups) {
    const canonical = group[0];
    for (const ch of group) {
      if (!(ch in table)) table[ch] = canonical;
    }
  }
  return table;
}

const HOMOPHONE_FOLD = buildFold(HOMOPHONE_GROUPS);
const SYNONYM_FOLD = buildFold(SYNONYM_GROUPS);

// Grammar characters that carry no content, stripped before the character-level
// comparison so wrappers like "\u56e0\u70ba...\u7684" cannot mask a real match.
const STOP_CHARS = new Set(
  '\u7684\u4e86\u662f\u6211\u4f60\u4ed6\u5979\u5b83\u5728\u548c\u8ddf\u8207\u628a\u88ab\u5c31\u90fd\u4e5f\u5f88\u9084\u6709\u6c92\u4e0d\u90a3\u8fd9\u500b\u5011\u4eec'.split(''),
);

const CUED_PATTERNS = [
  new RegExp('\u7b2c\\s*(' + CN_DIGIT + ')'),
  new RegExp('(' + CN_DIGIT + ')\\s*(?:\u500b|\u9805|\u6b3e|\u689d|\u9078|\u7684)'),
  new RegExp(
    '(?:\u9078|\u9078\u7684\u662f|\u7b54\u6848\u662f|\u7b54|\u6211\u9078|\u6211\u8aaa|\u6211\u731c|\u6b63\u78ba|\u5c0d)\\s*(?:\u662f)?\\s*(' + CN_DIGIT + ')'
  ),
];

const AR_DIGIT_RE = new RegExp('(?<![0-9])([1234\uff11-\uff14])(?![0-9])');
const DIGIT_RUN_RE = /[0-9]{2,}/;
const BARE_RE = new RegExp('^(' + CN_DIGIT + ')$');

export function normalize(text) {
  if (!text) return '';
  let out = String(text).trim().toLowerCase();
  out = out.replace(/[\uff10-\uff19]/g, (ch) =>
    String.fromCharCode(ch.charCodeAt(0) - 0xff10 + 0x30)
  );
  return out.replace(NOISE_RE, '');
}

export function foldTable(text, table) {
  let out = '';
  for (const ch of String(text)) out += table[ch] !== undefined ? table[ch] : ch;
  return out;
}

export function foldVariants(text) {
  return foldTable(text, VARIANT_FOLD);
}

export function foldHomophones(text) {
  return foldTable(text, HOMOPHONE_FOLD);
}

export function foldRelaxed(text) {
  return foldTable(foldHomophones(text), SYNONYM_FOLD);
}

// --- stage 1: explicit numbers --------------------------------------------

export function extractOptionIndex(raw, optionCount = DEFAULT_OPTION_COUNT) {
  const normalized = normalize(raw);
  if (!normalized) return { index: null, how: '' };

  for (const pattern of CUED_PATTERNS) {
    const match = pattern.exec(normalized);
    if (match) {
      const value = NUMBER_CHARS[match[1]];
      if (value !== undefined && value >= 1 && value <= optionCount) {
        return { index: value - 1, how: 'cued' };
      }
    }
  }

  if (normalized.length <= 2) {
    const match = BARE_RE.exec(normalized);
    if (match) {
      const value = NUMBER_CHARS[match[1]];
      if (value !== undefined && value >= 1 && value <= optionCount) {
        return { index: value - 1, how: 'bare' };
      }
    }
  }

  if (!DIGIT_RUN_RE.test(normalized)) {
    const match = AR_DIGIT_RE.exec(normalized);
    if (match) {
      const value = NUMBER_CHARS[match[1]];
      if (value !== undefined && value >= 1 && value <= optionCount) {
        return { index: value - 1, how: 'isolated' };
      }
    }
  }

  return { index: null, how: '' };
}

// --- similarity ------------------------------------------------------------

// Longest common substring, normalised by length.
//
// This replaces a Ratcliff/Obershelp port of difflib.SequenceMatcher. That port
// was correct on simple inputs but looped forever on real corpus text (e.g. the
// 背影 Q4 option), because difflib de-duplicates overlapping matches through an
// i2j/j2i table that a naive queue-based port drops.
//
// Substring similarity is not the same number difflib returns, so the two
// implementations are intentionally not bit-identical — see the contract test.
// Nothing is lost in practice: for two identical strings the bigram dice below
// already scores a perfect 1.0, so this signal only has to break ties.
export function substringSimilarity(left, right) {
  if (!left || !right) return 0;
  if (left === right) return 1;
  // DP over one rolling row: O(n*m) time, O(min(n,m)) memory, always terminates.
  const shorter = left.length <= right.length ? left : right;
  const longer = left.length <= right.length ? right : left;
  let prev = new Array(shorter.length + 1).fill(0);
  let best = 0;
  for (let i = 1; i <= longer.length; i += 1) {
    const row = new Array(shorter.length + 1).fill(0);
    const lc = longer[i - 1];
    for (let j = 1; j <= shorter.length; j += 1) {
      if (lc === shorter[j - 1]) {
        row[j] = prev[j - 1] + 1;
        if (row[j] > best) best = row[j];
      }
    }
    prev = row;
  }
  return (2 * best) / (left.length + right.length);
}

function bigrams(text) {
  if (text.length < 2) return new Set(text ? [text] : []);
  const out = new Set();
  for (let i = 0; i < text.length - 1; i += 1) out.add(text.slice(i, i + 2));
  return out;
}

// Four distinct matching characters is roughly where a CJK overlap starts to
// mean something. Below that, overlaps are discounted so two shared characters
// out of three cannot masquerade as a confident match.
const SMALL_OVERLAP = 4;

function overlapDiscount(a, b) {
  return Math.min(1, Math.min(a.size, b.size) / SMALL_OVERLAP);
}

function dice(a, b) {
  if (!a.size || !b.size) return 0;
  let shared = 0;
  for (const value of a) if (b.has(value)) shared += 1;
  return ((2 * shared) / (a.size + b.size)) * overlapDiscount(a, b);
}

// Discounted when the overlap is tiny: two or three shared characters out of
// three looks like a 1.0 match but is weak evidence. Without the discount,
// "今天天氣很好" scored 0.67 against the three-character option "天氣變了" and
// was accepted. Four distinct matching characters is where a CJK overlap
// starts to mean something.
function containment(needle, haystack) {
  if (!needle.size || !haystack.size) return 0;
  let shared = 0;
  for (const value of needle) if (haystack.has(value)) shared += 1;
  const smallest = Math.min(needle.size, haystack.size);
  return (shared / smallest) * overlapDiscount(needle, haystack);
}

function contentChars(text) {
  const out = new Set();
  for (const ch of text) if (!STOP_CHARS.has(ch)) out.add(ch);
  return out;
}

function baseSimilarity(inputNorm, optionNorm) {
  if (!inputNorm || !optionNorm) return 0;
  return Math.max(
    substringSimilarity(inputNorm, optionNorm),
    dice(bigrams(inputNorm), bigrams(optionNorm)),
    containment(bigrams(inputNorm), bigrams(optionNorm)) * 0.92,
    dice(contentChars(inputNorm), contentChars(optionNorm)),
  );
}

function pairSimilarity(inputNorm, optionNorm) {
  let direct = baseSimilarity(inputNorm, optionNorm);
  const foldedInput = foldRelaxed(inputNorm);
  const foldedOption = foldRelaxed(optionNorm);
  if (foldedInput !== inputNorm || foldedOption !== optionNorm) {
    const folded = baseSimilarity(foldedInput, foldedOption);
    direct = Math.min(1, direct + 0.18 * (folded - direct));
  }
  return direct;
}

// --- stage 2: semantic matching -------------------------------------------

export function fuzzyMatchOption(
  raw,
  options,
  threshold = MIN_CONFIDENCE,
  ambiguityMargin = AMBIGUITY_MARGIN,
) {
  const normalizedInput = foldVariants(normalize(raw));
  if (!normalizedInput || !options || !options.length) {
    return { index: null, score: 0, how: 'no-input', ranking: [], suggestion: null, margin: 0 };
  }

  const scores = options.map((option) =>
    pairSimilarity(normalizedInput, foldVariants(normalize(option))),
  );
  const ranking = [...scores].sort((a, b) => b - a);
  let bestIndex = 0;
  for (let i = 1; i < scores.length; i += 1) {
    if (scores[i] > scores[bestIndex]) bestIndex = i;
  }
  const bestScore = scores[bestIndex];
  const margin = ranking.length > 1 ? ranking[0] - ranking[1] : 1;

  const deny = (how) => ({
    index: null, score: bestScore, how, ranking, suggestion: bestIndex, margin,
  });
  if (bestScore < threshold) return deny('below-threshold');
  if (margin < ambiguityMargin) return deny('ambiguous');
  return { index: bestIndex, score: bestScore, how: 'fuzzy', ranking, suggestion: bestIndex, margin };
}

// --- combined cascade ------------------------------------------------------

export function combineSignals(raw, options, threshold = MIN_CONFIDENCE) {
  const { index, how } = extractOptionIndex(raw, options.length);
  if (index !== null) return { index, how, score: 1 };
  const match = fuzzyMatchOption(raw, options, threshold);
  return { index: match.index, how: match.how, score: match.score, suggestion: match.suggestion };
}
