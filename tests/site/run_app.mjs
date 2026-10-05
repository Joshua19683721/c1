// End-to-end check of the shipped site/app.js under a minimal DOM stub.
//
// There is no headless browser here, so this stubs just enough of the DOM for
// app.js to run: element registry, classList, children, and the speech APIs.
// It catches the bug class that would otherwise ship silently — an element id
// typo, a wrong property name, a handler wired to nothing.
//
//   node tests/site/run_app.mjs

import { readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const siteRoot = join(here, '..', '..', 'site');
const payload = JSON.parse(readFileSync(join(siteRoot, 'data', 'articles.json'), 'utf8'));

class StubClassList {
  constructor() { this.set = new Set(); }
  add(...names) { for (const n of names) this.set.add(n); }
  remove(...names) { for (const n of names) this.set.delete(n); }
  contains(name) { return this.set.has(name); }
}

class StubElement {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.classList = new StubClassList();
    this.style = {};
    this._text = '';
    this._html = '';
    this.listeners = {};
    this.attributes = {};
    this.value = '';
    this.disabled = false;
  }
  // Assigning className updates classList in a real DOM; the stub must do the
  // same or class-based queries silently match nothing.
  get className() { return [...this.classList.set].join(' '); }
  set className(value) {
    this.classList.set = new Set(String(value).split(/\s+/).filter(Boolean));
  }

  get textContent() { return this._text; }
  set textContent(v) { this._text = String(v); this.children = []; }
  get innerHTML() { return this._html; }
  set innerHTML(v) { this._html = String(v); this.children = []; }
  appendChild(child) { this.children.push(child); return child; }
  append(...nodes) { this.children.push(...nodes); }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name]; }

  addEventListener(type, handler) {
    (this.listeners[type] ||= []).push(handler);
  }
  dispatch(type) { for (const h of this.listeners[type] || []) h({ preventDefault() {} }); }
  click() { this.dispatch('click'); }
  // What a user would see: own text, any innerHTML, plus every descendant.
  // A real DOM exposes this through textContent; the stub has to walk children
  // itself, because renderFinished() builds the reflection by appending nodes.
  get text() {
    return [
      this._text,
      this._html,
      ...this.children.map((c) => c.text),
    ].join('\n');
  }
}

const registry = new Map();
const byId = (id) => {
  if (!registry.has(id)) registry.set(id, new StubElement());
  return registry.get(id);
};

const inputsBlock = new StubElement();

globalThis.document = {
  getElementById: byId,
  createElement: (tag) => new StubElement(tag),
  querySelector: (sel) => (sel === '.inputs' ? inputsBlock : new StubElement()),
};

globalThis.window = {
  speechSynthesis: {
    getVoices: () => [],
    speak: () => {},
    cancel: () => {},
    pause: () => {},
  },
};
globalThis.SpeechSynthesisUtterance = class { constructor(t) { this.text = t; } };
// SpeechRecognition deliberately absent: exercises the unsupported-browser path.
globalThis.fetch = async (url) => {
  if (url !== 'data/articles.json') throw new Error(`unexpected fetch: ${url}`);
  return { ok: true, status: 200, json: async () => payload };
};

const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

// pathToFileURL: on Windows a bare drive path is not a valid ESM URL.
await import(pathToFileURL(join(siteRoot, 'app.js')).href);
await new Promise((resolve) => setTimeout(resolve, 50));

const optionButtons = () => byId('options').children.filter((c) => c.tagName === 'BUTTON');
const explanationButtons = () => byId('explain').children
  .flatMap((card) => card.children)
  .flatMap((row) => row.children || [])
  .filter((c) => c.tagName === 'BUTTON');

check(optionButtons().length === 4, `expected 4 option buttons, got ${optionButtons().length}`);
check(byId('progressText').textContent === '\u7b2c 1 \u984c / \u5171 10 \u984c',
  `progress text is ${JSON.stringify(byId('progressText').textContent)}`);
check(byId('readText').textContent.length > 50, 'article text not rendered');

// --- category browser ---
check(byId('categories').children.length === payload.categories.length,
  `expected ${payload.categories.length} category chips, got ${byId('categories').children.length}`);
check(byId('articleGrid').children.length > 0, 'article grid is empty on load');

const emptyCategory = payload.categories.find((c) => c.count === 0);
if (emptyCategory) {
  const chips = byId('categories').children;
  chips[payload.categories.indexOf(emptyCategory)].click();
  check(byId('articleGrid').text.includes('\u9019\u500b\u985e\u5225\u9084\u5728\u88dc\u5145'),
    'an empty category did not show the placeholder note');
}

const selectArticle = (article) => {
  const index = payload.categories.findIndex((c) => c.slug === article.category);
  byId('categories').children[index].click();
  const siblings = payload.articles.filter((a) => a.category === article.category);
  byId('articleGrid').children[siblings.findIndex((a) => a.id === article.id)].click();
};

// Click through every question using the answer key.
for (const article of payload.articles) {
  selectArticle(article);

  for (const q of article.questions) {
    const buttons = optionButtons();
    check(buttons.length === 4, `${article.id} Q${q.number}: ${buttons.length} buttons`);
    const correctPosition = q.shuffleOrder.indexOf(q.sourceCorrectIndex);
    buttons[correctPosition].click();
    check(byId('explain').text.includes(q.explanation),
      `${article.id} Q${q.number}: correct answer showed no explanation`);
    explanationButtons()[0].click();   // 下一題
  }

  check(byId('progressText').textContent === '\u5b8c\u6210 10 \u984c',
    `${article.id}: progress is ${JSON.stringify(byId('progressText').textContent)}`);
  check(byId('reflection').text.includes(article.title),
    `${article.id}: puzzle does not mention the title`);
  const stepCount = byId('reflection').children.filter((c) => c.tagName === 'DIV' && c.classList.contains('step')).length;
  check(stepCount === 3, `${article.id}: expected 3 CoT steps, got ${stepCount}`);

  byId('restart').click();
  check(byId('progressText').textContent === '\u7b2c 1 \u984c / \u5171 10 \u984c',
    `${article.id}: restart did not reset the progress bar`);
  check(optionButtons().length === 4, `${article.id}: options not restored after restart`);
}

// An answer that cannot be resolved must not advance the lesson.
byId('typed').value = '\u4eca\u5929\u5929\u6c23\u5f88\u597d';
byId('send').click();
check(byId('progressText').textContent === '\u7b2c 1 \u984c / \u5171 10 \u984c',
  'an unresolved answer advanced the lesson');
check(byId('feedback').text.length > 0, 'no feedback shown for an unresolved answer');

// --- explanation + retry: the feature that turns a wrong answer into learning ---
// Pin the article first: the loop above ends on the last one, so measuring
// against articles[0] would silently test a question that is not on screen.
selectArticle(payload.articles[0]);
const firstQuestion = payload.articles[0].questions[0];
const wrongPosition = (firstQuestion.shuffleOrder.indexOf(firstQuestion.sourceCorrectIndex) + 1) % 4;
optionButtons()[wrongPosition].click();

check(byId('progressText').textContent === '\u7b2c 1 \u984c / \u5171 10 \u984c',
  'a wrong answer advanced the lesson instead of offering a retry');

const explainText = byId('explain').text;
check(explainText.includes('\u6b63\u78ba\u7b54\u6848\u8207\u89e3\u6790'),
  'wrong answer did not show the correct-answer explanation');
check(explainText.includes(firstQuestion.explanation),
  'explanation text does not match the question explanation');
check(explainText.includes('\u518d\u8a66\u4e00\u6b21'), 'no retry button');
check(explainText.includes('\u61c2\u4e86'), 'no skip button');

const explainButtons = explanationButtons();
check(explainButtons.length === 2, `expected retry + skip, got ${explainButtons.length} buttons`);

explainButtons[0].click();
check(byId('explain').text.trim().length === 0, 'retry did not clear the explanation');
check(byId('progressText').textContent === '\u7b2c 1 \u984c / \u5171 10 \u984c',
  'retry moved the lesson on');

optionButtons()[wrongPosition].click();
const skipButtons = explanationButtons();
check(skipButtons.length === 2, 'retry button vanished on the second attempt');
skipButtons[1].click();
check(byId('progressText').textContent === '\u7b2c 2 \u984c / \u5171 10 \u984c',
  'skip did not advance past the question');

// A correct answer shows its explanation too, and still waits for 下一題 rather
// than moving on by itself — that is what keeps the explanation attached to the
// question it belongs to.
const q2 = payload.articles[0].questions[1];
optionButtons()[q2.shuffleOrder.indexOf(q2.sourceCorrectIndex)].click();
check(byId('explain').text.includes(q2.explanation),
  'a correct answer did not show the explanation');
check(byId('progressText').textContent === '\u7b2c 2 \u984c / \u5171 10 \u984c',
  'a correct answer advanced without asking');
check(explanationButtons().length === 1, 'correct answer should offer only 下一題');
explanationButtons()[0].click();
check(byId('progressText').textContent === '\u7b2c 3 \u984c / \u5171 10 \u984c',
  '下一題 did not advance');

// A number typed into the box must be accepted.
const q3 = payload.articles[0].questions[2];
byId('typed').value = String(q3.shuffleOrder.indexOf(q3.sourceCorrectIndex) + 1);
byId('send').click();
check(byId('explain').text.includes(q3.explanation),
  'typed number did not show the explanation');

console.log(JSON.stringify({ failures }, null, 2));
process.exit(failures.length ? 1 : 0);
