// Behavioural contract for site/lib/parser.js, run under Node.
//
// The browser build is a second implementation of src/parser.py. Rather than
// pretending the two are bit-identical (they are not: difflib's SequenceMatcher
// has no exact JavaScript twin), this asserts the guarantees that actually
// matter to a student sitting in front of the app.
//
//   node tests/site/run_contract.mjs
//
// Prints a JSON summary on stdout so the Python test suite can assert on it.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import {
  normalize,
  extractOptionIndex,
  fuzzyMatchOption,
  foldRelaxed,
} from '../../site/lib/parser.js';

const here = dirname(fileURLToPath(import.meta.url));
const data = JSON.parse(
  readFileSync(join(here, '..', '..', 'site', 'data', 'articles.json'), 'utf8'),
);

const failures = [];
const fail = (message) => failures.push(message);

function lessonFor(article, { shuffle = true } = {}) {
  return article.questions.map((q) => {
    if (!shuffle) {
      return { ...q, options: q.options, correctIndex: q.sourceCorrectIndex };
    }
    const options = q.shuffleOrder.map((i) => q.options[i]);
    return {
      ...q,
      options,
      correctIndex: q.shuffleOrder.indexOf(q.sourceCorrectIndex),
    };
  });
}

let verbatimChecked = 0;
let verbatimWrong = 0;

for (const article of data.articles) {
  for (const q of lessonFor(article)) {
    q.options.forEach((text, position) => {
      verbatimChecked += 1;
      const result = fuzzyMatchOption(text, q.options);
      if (result.index !== position) {
        verbatimWrong += 1;
        fail(
          `${article.id} Q${q.number}: option ${position + 1} mapped to ` +
            `${result.index === null ? 'null' : result.index + 1} (${result.how})`,
        );
      }
    });
  }
}

// Options must stay distinguishable after folding.
let collapsed = 0;
for (const article of data.articles) {
  for (const q of lessonFor(article)) {
    const folded = q.options.map((o) => foldRelaxed(normalize(o)));
    if (new Set(folded).size !== 4) {
      collapsed += 1;
      fail(`${article.id} Q${q.number}: folding collapsed options: ${JSON.stringify(folded)}`);
    }
  }
}

// Numbers inside a quoted answer must not be read as a choice.
const numberCases = [
  ['3', 2, 'bare'],
  ['\u7b2c\u56db\u500b', 3, 'cued'],
  ['\u6211\u9078\u7b2c\u4e8c\u500b', 1, 'cued'],
  ['2.', 1, 'bare'],
];
for (const [raw, expected, how] of numberCases) {
  const got = extractOptionIndex(raw);
  if (got.index !== expected || got.how !== how) {
    fail(`extractOptionIndex(${raw}) -> ${JSON.stringify(got)}, expected ${expected}/${how}`);
  }
}

const mustNotChoose = [
  '\u5341\u4e94\u842c\u5927\u8ecd', // \u5341\u4e94\u842c\u5927\u8ecd
  '\u4e8c\u5343\u4e94\u767e\u540d\u58f3\u58eb', // \u4e8c\u5343\u4e94\u767e\u540d\u58f3\u58eb
  '15\u842c', // 15\u842c
  '50\u5143', // 50\u5143
];
for (const raw of mustNotChoose) {
  if (extractOptionIndex(raw).index !== null) {
    fail(`extractOptionIndex(${raw}) should abstain, got ${JSON.stringify(extractOptionIndex(raw))}`);
  }
}

// Unrelated answers must be rejected everywhere.
const negatives = [
  '\u4eca\u5929\u5929\u6c23\u5f88\u597d', // \u4eca\u5929\u5929\u6c23\u5f88\u597d
  '\u6211\u4e0d\u77e5\u9053', // \u6211\u4e0d\u77e5\u9053
  '\u6211\u5fd8\u8a18\u4e86', // \u6211\u5fd8\u8a18\u4e86
  '\u9999\u8549\u5f88\u597d\u5403', // \u9999\u8549\u5f88\u597d\u5403
];
// A distractor must never contain one of the negative phrases: an option that
// says "不知道" makes "我不知道" a *correct* match, which is not a bug in the
// matcher but a badly-written option. Catch it at authoring time.
let optionTrap = 0;
for (const article of data.articles) {
  for (const q of lessonFor(article)) {
    for (const option of q.options) {
      for (const raw of negatives) {
        if (normalize(option).includes(normalize(raw))) {
          optionTrap += 1;
          fail(`${article.id} Q${q.number}: option contains the test phrase ${raw}: ${option}`);
        }
      }
    }
  }
}

let negativeAccepted = 0;
for (const article of data.articles) {
  for (const q of lessonFor(article)) {
    for (const raw of negatives) {
      if (fuzzyMatchOption(raw, q.options).index !== null) {
        negativeAccepted += 1;
        fail(`${article.id} Q${q.number}: accepted unrelated answer ${raw}`);
      }
    }
  }
}

const summary = {
  articles: data.articles.length,
  questions: data.articles.reduce((n, a) => n + a.questions.length, 0),
  verbatimChecked,
  verbatimWrong,
  collapsed,
  negativeAccepted,
  optionTrap,
  failures,
};

console.log(JSON.stringify(summary, null, 2));
process.exit(failures.length ? 1 : 0);
