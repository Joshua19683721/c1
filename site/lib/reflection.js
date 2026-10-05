// End-of-session reflection for the static browser build.
// A port of build_local_reflection() in src/cot.py.

export const COT_STAGES = [
  ['\u5b78\u627e\u7dda\u7d22\uff08\u7d30\u8282\u7406\u89e3\uff09', 1, 3],
  ['\u4e32\u806f\u60c5\u610f\uff08\u63a8\u6cd5\u5206\u6790\uff09', 4, 7],
  ['\u5927\u8166\u6607\u83ef\uff08\u7701\u601d\u8a55\u932f\uff09', 8, 10],
];

const clean = (text) => String(text || '').replace(/[\u3002\s]+$/, '').trim();

// Same enumeration punctuation as the Python version.
function join(items) {
  const cleaned = items.map(clean).filter(Boolean);
  if (!cleaned.length) return '\uff08\u9019\u4e00\u984c\u9084\u6c92\u6709\u9078\u9805\uff09';
  return cleaned.join('\u3001');
}

const stageSlice = (list, low, high) => list.slice(low - 1, high);

function single(answers, position) {
  const value = answers[position - 1];
  return value && String(value).trim() ? String(value).trim() : '\uff08\u672a\u4f5c\u7b54\uff09';
}

export function buildLocalReflection(article, answers, gists) {
  const summary = gists && gists.length ? gists : answers;
  const first = join(stageSlice(summary, 1, 3));
  const middle = join(stageSlice(summary, 4, 7));
  const last = join(stageSlice(summary, 8, 10));

  const puzzle = [
    `\u8b80\u5b8c${article.displayTitle}\uff0c\u6211\u5148\u627e\u51fa\u7dda\u7d22\uff1a${first}\u3002`,
    `\u518d\u6df1\u5165\u4e00\u9ede\uff1a${middle}\u3002`,
    `\u6700\u5f8c\u56de\u982d\u770b\u6574\u7bc7\uff1a${last}\u3002`,
    '\u5341\u500b\u7b54\u6848\u6fc4\u8d77\u4f86\uff0c\u5c31\u662f\u6211\u8b80\u5b8c\u9019\u7bc7\u6587\u7ae0\u7684\u5b8c\u6574\u7406\u89e3\u3002',
  ].join('');

  const bodies = [
    [
      '\u4e00\u958b\u59cb\u6211\u5148\u4e0d\u6025\u7740\u4e0b\u7d50\u8ad6\uff0c\u53ea\u628a\u6587\u7ae0\u88e1\u5beb\u7684\u4e8b\u5be6\u4e00\u500b\u4e00\u500b\u627e\u51fa\u4f86\u3002',
      `\u4f60\u7684\u7b2c 1 \u984c\u9078\u4e86\u300c${single(answers, 1)}\u300d\uff0c\u7b2c 2 \u984c\u662f\u300c${single(answers, 2)}\u300d\uff0c`,
      `\u7b2c 3 \u984c\u662f\u300c${single(answers, 3)}\u300d\u3002`,
      '\u9019\u4e00\u6b65\u5c31\u50cf\u770b\u8aaa\u660e\u66f8\u7684\u76ee\u9304\uff0c\u5148\u628a\u7dda\u7d22\u6293\u9f4a\uff0c\u5f8c\u9762\u624d\u770b\u5f97\u61c2\u3002',
    ].join(''),
    [
      '\u7dda\u7d22\u6293\u9f4a\u4e4b\u5f8c\uff0c\u6211\u958b\u59cb\u628a\u524d\u5f8c\u7684\u4e8b\u60c5\u4e32\u8d77\u4f86\u3002',
      `\u4f60\u5728\u7b2c 4 \u5230\u7b2c 7 \u984c\u9078\u5230\u7684\u662f\uff1a${middle}\u3002`,
      '\u9019\u4e00\u6b65\u6703\u7528\u5230\u300c\u70ba\u4ec0\u9ebc\u300d\uff1a\u4f5c\u8005\u70ba\u4ec0\u9ebc\u8981\u9019\u6a23\u5beb\uff1f\u8b80\u8005\u7684\u5fc3\u60c5\u70ba\u4ec0\u9ebc\u6703\u8b8a\uff1f',
      '\u7b54\u6848\u5c31\u85cf\u5728\u9019\u4e9b\u770b\u8d77\u4f86\u5f88\u666e\u901a\u7684\u7d30\u7bc0\u88e1\u3002',
    ].join(''),
    [
      '\u6700\u5f8c\u4e00\u6b65\uff0c\u6211\u628a\u6574\u7bc7\u6587\u7ae0\u62c9\u5230\u6700\u9ad8\u7684\u5730\u65b9\u4f86\u770b\u3002',
      `\u4f60\u7684\u7b2c 8\u30019\u300110 \u984c\u7b54\u6848\u662f\uff1a${last}\u3002`,
      '\u9019\u4e09\u984c\u8b93\u6211\u660e\u767d\uff1a\u8b80\u5b8c\u4e00\u7bc7\u6587\u7ae0\uff0c\u4e0d\u53ea\u8981\u77e5\u9053\u300c\u767c\u751f\u4e86\u4ec0\u9ebc\u300d\uff0c',
      '\u9084\u8981\u60f3\u300c\u5b83\u60f3\u544a\u8b72\u6211\u4ec0\u9ebc\u300d\uff0c\u7136\u5f8c\u628a\u5b83\u9023\u56de\u81ea\u5df1\u7684\u751f\u6d3b\u3002',
    ].join(''),
  ];

  return {
    puzzle,
    steps: bodies.map((body, index) => ({
      number: index + 1,
      title: COT_STAGES[index][0],
      body,
    })),
    source: 'local',
  };
}
