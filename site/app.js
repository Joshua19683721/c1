// ReadExpress-CoT — static browser build.
//
// Same flow as app.py: 10 questions, instant feedback, then the reading puzzle
// and the 3-step chain of thought. Two deliberate differences from the
// Streamlit build:
//
//   * No LLM. A browser page cannot hold an API key, and shipping one to a
//     public URL would leak it to every visitor. Everything here runs locally.
//   * Speech uses the Web Speech API instead of sounddevice + Whisper, which
//     removes the 2 GB local dependency and works entirely on-device.

import { fuzzyMatchOption, extractOptionIndex } from './lib/parser.js';
import { buildLocalReflection } from './lib/reflection.js';

const PRAISE = [
  '\u7b54\u5c0d\u5566\uff01\u4f60\u8b80\u5f97\u5f88\u4ed4\u7d30\u55ae\uff01',
  '\u592a\u68d2\u4e86\uff01\u5c31\u662f\u9019\u500b\u610f\u601d\uff01',
  '\u771f\u5389\u5bb3\uff0c\u9019\u4e00\u984c\u4f60\u5b8c\u5168\u638c\u63e1\u4e86\uff01',
  '\u6b63\u78ba\uff01\u4f60\u7684\u60f3\u6cd5\u548c\u6587\u7ae0\u4e00\u6a23\u5462\uff01',
  '\u5f88\u597d\uff01\u7e7c\u7e8c\u4fdd\u6301\u9019\u500b\u8b80\u6cd5\uff01',
];

const WRONG_OPENER = '\u518d\u60f3\u60f3\u770b\u55ae\uff01';
const NUMBER_HOWS = ['cued', 'bare', 'isolated'];

const $ = (id) => document.getElementById(id);

const state = {
  articles: [],
  articleId: null,
  index: 0,
  answers: [],
  correct: [],
  last: null,
  suggestion: null,
  shuffle: true,
};

function article() {
  return state.articles.find((a) => a.id === state.articleId);
}

// Mirror of build_lesson(): apply the exported permutation and work out where
// the answer ended up.
function questions() {
  const art = article();
  return art.questions.map((q) => {
    if (!state.shuffle) {
      return { ...q, options: q.options, correctIndex: q.sourceCorrectIndex };
    }
    return {
      ...q,
      options: q.shuffleOrder.map((i) => q.options[i]),
      correctIndex: q.shuffleOrder.indexOf(q.sourceCorrectIndex),
    };
  });
}

function feedbackFor(question, isCorrect) {
  if (isCorrect) return PRAISE[(question.number - 1) % PRAISE.length];
  const hint = question.hint || '\u518d\u8b80\u4e00\u6b21\u6587\u7ae0\uff0c\u7b54\u6848\u5c31\u85cf\u5728\u88e1\u9762\u55ae\u3002';
  return `${WRONG_OPENER} \u63d0\u793a\uff1a${hint}`;
}

function submitAnswer(raw) {
  const list = questions();
  if (state.index >= list.length) return;
  const question = list[state.index];
  const text = String(raw || '').trim();

  if (!text) {
    state.last = {
      index: null,
      isCorrect: null,
      how: 'empty',
      feedback: '\u5148\u9078\u4e00\u500b\u7b54\u6848\uff0c\u6216\u8aaa\u51fa\u4f60\u7684\u60f3\u6cd5\u5427\uff01',
      note: '',
    };
    state.suggestion = null;
    render();
    return;
  }

  // Numbers first, exactly like Pipeline 1.
  const { index, how } = extractOptionIndex(text, question.options.length);
  let resolvedIndex = index;
  let resolvedHow = how;
  let suggestion = index;

  if (resolvedIndex === null) {
    const match = fuzzyMatchOption(text, question.options);
    resolvedIndex = match.index;
    resolvedHow = match.how;
    suggestion = match.suggestion;
  }

  if (resolvedIndex === null) {
    state.last = {
      index: null,
      isCorrect: null,
      how: resolvedHow,
      feedback: '\u6211\u9084\u807d\u4e0d\u592a\u61c2\u8036\uff0c\u4f60\u53ef\u4ee5\u76f4\u63a5\u6309\u4e00\u500b\u9078\u9805\uff0c\u6216\u628a\u7b54\u6848\u7684\u95dc\u9375\u5b57\u8aaa\u4e00\u6b21\u5427\uff1f',
      note: '\u7cfb\u7d71\u7121\u6cd5\u78ba\u5b9a\uff0c\u8acb\u5b78\u751f\u78ba\u8a8d',
    };
    state.suggestion = suggestion;
    render();
    return;
  }

  const isCorrect = resolvedIndex === question.correctIndex;
  state.last = {
    index: resolvedIndex,
    isCorrect,
    how: NUMBER_HOWS.includes(resolvedHow) ? 'number' : resolvedHow,
    feedback: feedbackFor(question, isCorrect),
    note: NUMBER_HOWS.includes(resolvedHow) ? '\u5bec\u5bb9\u6578\u5b57\u89e3\u6790' : '\u672c\u5730\u5bec\u5bb9\u6bd4\u5c0d',
  };
  state.answers.push(question.options[resolvedIndex]);
  state.correct.push(isCorrect);
  state.suggestion = null;
  state.index += 1;
  $('typed').value = '';
  render();
}

// --- speech ----------------------------------------------------------------

function pickVoice() {
  const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
  if (!voices.length) return null;
  const zhTW = voices.filter(
    (v) => /^zh(-|_)?(TW|Hant|KG|MO)/i.test(v.lang) || /Taiwan|Mandarin|Chinese/i.test(v.name),
  );
  return zhTW[0] || voices.find((v) => /^zh/i.test(v.lang)) || voices[0];
}

function speakArticle() {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const art = article();
  const utterance = new SpeechSynthesisUtterance(art.text);
  utterance.lang = 'zh-TW';
  utterance.rate = 0.92;
  const voice = pickVoice();
  if (voice) utterance.voice = voice;
  window.speechSynthesis.speak(utterance);
}

function setupMic() {
  const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
  const button = $('mic');
  if (!Ctor) {
    button.disabled = true;
    button.textContent = '🎤 此瀏覽器不支援';
    $('micHint').textContent =
      '這個瀏覽器沒有語音辨識（Chrome、Edge、Safari 可用）。請改用打字輸入。';
    return;
  }
  const recognition = new Ctor();
  recognition.lang = 'zh-TW';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.continuous = false;

  let busy = false;
  recognition.onstart = () => {
    busy = true;
    button.classList.add('recording');
    button.textContent = '🔴 正在聆聽…';
    $('micHint').textContent = '請在麥克風前說出答案（例如「第 3 個」）。';
  };
  recognition.onresult = (event) => {
    const text = Array.from(event.results).map((r) => r[0].transcript).join('');
    $('typed').value = text.trim();
    $('micHint').textContent = `我聽到的是：「${text.trim()}」，按「送出答案」確認。`;
  };
  recognition.onerror = (event) => {
    $('micHint').textContent = event.error === 'not-allowed'
      ? '麥克風權限被拒絕，請改用打字輸入。'
      : `語音辨識失敗（${event.error}），請再試一次或改用打字輸入。`;
  };
  recognition.onend = () => {
    busy = false;
    button.classList.remove('recording');
    button.textContent = '🎤 按住說話';
  };
  button.addEventListener('click', () => {
    if (busy) { recognition.stop(); return; }
    try {
      recognition.start();
    } catch (err) {
      $('micHint').textContent = '無法啟動語音辨識，請改用打字輸入。';
    }
  });
}

// --- rendering --------------------------------------------------------------

function render() {
  const art = article();
  const list = questions();
  const total = list.length;
  const finished = state.index >= total;

  $('subtitle').textContent = `${art.displayTitle}\u3000${art.author}\u3000\uff5c\u3000${art.genre}`;
  $('readTitle').textContent = art.displayTitle;
  $('readMeta').textContent = `${art.author}\u3000\u00b7\u3000${art.genre}`;
  $('readText').textContent = art.text;

  const shown = Math.min(state.index + 1, total);
  $('barFill').style.width = `${(state.index / total) * 100}%`;
  $('progressText').textContent = finished
    ? `\u5b8c\u6210 ${total} \u984c`
    : `\u7b2c ${shown} \u984c / \u5171 ${total} \u984c`;

  if (finished) {
    renderFinished(art, list);
    return;
  }

  const question = list[state.index];
  $('quizCard').classList.remove('hidden');
  $('doneCard').classList.add('hidden');
  $('reflection').innerHTML = '';
  $('skill').textContent = question.skill;
  $('question').innerHTML = `<b>${question.number}.</b> ${escapeHtml(question.stem)}`;

  const box = $('options');
  box.innerHTML = '';
  question.options.forEach((text, i) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'option';
    if (state.last && state.last.index === i) {
      button.classList.add(state.last.isCorrect ? 'correct' : 'wrong');
    }
    button.textContent = `${i + 1}. ${text}`;
    button.addEventListener('click', () => submitAnswer(String(i + 1)));
    box.appendChild(button);
  });

  renderFeedback(question);
  document.querySelector('.inputs').classList.remove('hidden');
}

function renderFeedback(question) {
  const host = $('feedback');
  const last = state.last;
  if (!last) { host.innerHTML = ''; return; }

  if (last.index !== null) {
    const ok = last.isCorrect;
    host.innerHTML = '<div class="feedback ' + (ok ? 'ok' : 'no') + '">'
      + (ok ? '✅ \u592a\u68d2\u4e86\uff01\u7b54\u5c0d\u4e86' : '💡 \u518d\u8a66\u8a66\u770b\u55ae\uff01')
      + '<small>' + escapeHtml(last.feedback) + '</small></div>';
    return;
  }

  host.innerHTML = '<div class="feedback no">🤔 ' + escapeHtml(last.feedback)
    + '<small>（系統判斷方式：' + escapeHtml(last.note) + '）</small></div>';

  if (state.suggestion !== null && state.suggestion !== undefined) {
    const wrap = document.createElement('div');
    wrap.style.marginTop = '12px';
    const label = document.createElement('p');
    label.className = 'meta';
    label.textContent = '你是不是想選這個？';
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'option';
    button.textContent = `${state.suggestion + 1}. ${question.options[state.suggestion]}`;
    button.addEventListener('click', () => submitAnswer(String(state.suggestion + 1)));
    const note = document.createElement('p');
    note.className = 'hint';
    note.textContent = '不對的話，請再說一次，或直接按上面的選項。';
    wrap.append(label, button, note);
    host.appendChild(wrap);
  }
}

function renderFinished(art, list) {
  const total = list.length;
  const score = state.correct.filter(Boolean).length;

  $('quizCard').classList.add('hidden');
  $('doneCard').classList.remove('hidden');
  $('doneTitle').textContent = `🎉 \u5b8c\u6210\u5566\uff01\u7b54\u5c0d ${score} / ${total} \u984c`;
  $('doneMeta').textContent = state.correct.every(Boolean)
    ? '全對！你的閱讀理解很紮實。'
    : '看看下面的拼圖，理解會更清楚。';
  document.querySelector('.inputs').classList.add('hidden');
  $('feedback').innerHTML = '';

  const gists = list.map((q) => q.gist);
  const reflection = buildLocalReflection(art, state.answers, gists);
  const host = $('reflection');
  host.innerHTML = '';

  const h2 = document.createElement('h2');
  h2.className = 'section';
  h2.textContent = '🧩 你的閱讀思考拼圖';
  const puzzle = document.createElement('div');
  puzzle.className = 'puzzle';
  puzzle.textContent = reflection.puzzle;

  const h3 = document.createElement('h2');
  h3.className = 'section';
  h3.textContent = '🧠 AI 老師的 CoT 思維鏈解析';

  host.append(h2, puzzle, h3);
  for (const step of reflection.steps) {
    const box = document.createElement('div');
    box.className = 'step';
    const title = document.createElement('h3');
    title.textContent = `第 ${step.number} 步\u3000${step.title}`;
    const body = document.createElement('p');
    body.textContent = step.body;
    box.append(title, body);
    host.appendChild(box);
  }

  const again = document.createElement('button');
  again.type = 'button';
  again.className = 'btn primary';
  again.textContent = '🔄 再讀一次這篇文章';
  again.style.marginTop = '14px';
  again.addEventListener('click', restart);
  host.appendChild(again);
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function restart() {
  state.index = 0;
  state.answers = [];
  state.correct = [];
  state.last = null;
  state.suggestion = null;
  $('typed').value = '';
  render();
}

// --- boot ------------------------------------------------------------------

async function boot() {
  try {
    const response = await fetch('data/articles.json', { cache: 'no-cache' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.articles = (await response.json()).articles;
    state.articleId = state.articles[0].id;
  } catch (err) {
    $('subtitle').textContent =
      `載入文章失敗：${err.message}。請確認 data/articles.json 存在。`;
    return;
  }

  const select = $('article');
  for (const art of state.articles) {
    const option = document.createElement('option');
    option.value = art.id;
    option.textContent = `${art.displayTitle}${art.author}\u30fb${art.genre}`;
    select.appendChild(option);
  }
  select.value = state.articleId;
  select.addEventListener('change', () => {
    state.articleId = select.value;
    restart();
  });

  $('shuffle').addEventListener('change', (e) => {
    state.shuffle = e.target.checked;
    restart();
  });
  $('restart').addEventListener('click', restart);
  $('send').addEventListener('click', () => submitAnswer($('typed').value));
  $('typed').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitAnswer($('typed').value);
  });
  $('ttsPlay').addEventListener('click', speakArticle);
  $('ttsPause').addEventListener('click', () => window.speechSynthesis.pause());
  $('ttsStop').addEventListener('click', () => window.speechSynthesis.cancel());

  if (window.speechSynthesis) {
    const show = () => {
      const voice = pickVoice();
      $('ttsVoice').textContent = voice
        ? `語音：${voice.name}`
        : '系統語音（未安裝中文語音）';
    };
    window.speechSynthesis.onvoiceschanged = show;
    show();
  } else {
    $('ttsVoice').textContent = '此瀏覽器不支援語音朗讀';
  }

  setupMic();
  render();
}

boot();
