# -*- coding: utf-8 -*-
"""Pipeline 2 — cot_reflection_generator.

Turns a finished lesson into two things:

* the **閱讀思考拼圖** — the student's own ten answers stitched back into one
  paragraph, so they can see that the ten questions were ten windows onto the
  same article;
* a **3-step Chain-of-Thought** — 尋找線索 → 串聯情意 → 大腦昇華 — explaining how
  those ten answers assemble into full understanding.

Both halves come from the YAML pipeline when an LLM is configured, and from a
deterministic generator otherwise. The offline generator is deliberately written
to quote the student's actual answers rather than to paraphrase them, so it stays
specific to the article they just read.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .content import Article
from .llm import LLMClient, LLMUnavailable, default_client
from .prompts import get_pipeline, render_prompt

__all__ = [
    'CoTStep',
    'ReflectionResult',
    'generate_reflection',
    'build_local_reflection',
    'COT_STAGES',
]

#: Question ranges for the three CoT stages, exactly as the specification maps them.
COT_STAGES: tuple[tuple[str, int, int], ...] = (
    ('尋找線索（細節理解）', 1, 3),
    ('串聯情意（推論分析）', 4, 7),
    ('大腦昇華（省思評鑑）', 8, 10),
)

_STEP_MARKER_RE = re.compile(r'第\s*([123])\s*步')
_PART1_RE = re.compile(r'第一\s*部分|Reading\s*Semantic\s*Puzzle', re.IGNORECASE)
_PART2_RE = re.compile(r'第二\s*部分|Chain[- ]of[- ]Thought', re.IGNORECASE)


@dataclass(frozen=True)
class CoTStep:
    number: int
    title: str
    body: str


@dataclass(frozen=True)
class ReflectionResult:
    puzzle: str
    steps: tuple[CoTStep, ...]
    #: 'llm' or 'local' — surfaced in the UI so a teacher knows which ran.
    source: str
    note: str = ''

    @property
    def is_llm(self) -> bool:
        return self.source == 'llm'


# --- deterministic generator ------------------------------------------------

def _join(answers: list[str]) -> str:
    """Quote a run of answers with Chinese enumeration punctuation."""
    cleaned = [a.strip('。 ') for a in answers if a.strip()]
    if not cleaned:
        return '（這一題還沒有選項）'
    if len(cleaned) == 1:
        return cleaned[0]
    return '、'.join(cleaned[:-1]) + '、' + cleaned[-1]


def _stage_slice(answers: list[str], low: int, high: int) -> list[str]:
    return answers[low - 1: high]


def build_local_reflection(
    article: Article,
    answers: list[str],
    gists: list[str] | None = None,
) -> ReflectionResult:
    """Build the puzzle + CoT locally.

    This is the offline path, so it quotes rather than re-writes: an LLM might
    smooth the language, but it could also quietly invent a claim the student
    never made. Quoting keeps the reflection honest.

    The gist list holds the short essence of each answer. Using it for the puzzle
    keeps that paragraph inside the specification's 100-150 字 window; the CoT
    steps still quote the student's full wording for the first three answers so
    the reasoning stays concrete.
    """
    answers = list(answers)
    summary = list(gists) if gists else list(answers)
    first = _join(_stage_slice(summary, 1, 3))
    middle = _join(_stage_slice(summary, 4, 7))
    last = _join(_stage_slice(summary, 8, 10))

    puzzle = (
        f'讀完{article.display_title}，我先找出線索：{first}。'
        f'再深入一點：{middle}。'
        f'最後回頭看整篇：{last}。'
        f'十個答案湊起來，就是我讀完這篇文章的完整理解。'
    )

    step_bodies = (
        '一開始我先不急著下結論，只把文章裡寫的事實一個一個找出來。'
        f'你的第 1 題選了「{_single(answers, 1)}」，第 2 題是「{_single(answers, 2)}」，'
        f'第 3 題是「{_single(answers, 3)}」。'
        '這一步就像看說明書的目錄，先把線索抓齊，後面才看得懂。',

        '線索抓齊之後，我開始把前後的事情串起來。'
        f'你在第 4 到第 7 題選到的是：{middle}。'
        '這一步會用到「為什麼」：作者為什麼要這樣寫？讀者的心情為什麼會變？'
        '答案就藏在這些看起來很普通的細節裡。',

        '最後一步，我把整篇文章拉到最高的地方來看。'
        f'你的第 8、9、10 題答案是：{last}。'
        '這三題讓我明白：讀完一篇文章，不只要知道「發生了什麼」，'
        '還要想「它想告訴我什麼」，然後把它連回自己的生活。',
    )

    steps = tuple(
        CoTStep(number=i + 1, title=title, body=body)
        for i, ((title, _low, _high), body) in enumerate(zip(COT_STAGES, step_bodies))
    )
    return ReflectionResult(
        puzzle=puzzle,
        steps=steps,
        source='local',
        note='離線版：直接引用你的答案，忠實呈現你的理解',
    )


def _single(answers: list[str], position: int) -> str:
    if 0 < position <= len(answers) and answers[position - 1].strip():
        return answers[position - 1].strip()
    return '（未作答）'


# --- LLM path ---------------------------------------------------------------

def _clean_section(text: str) -> str:
    """Drop markdown heading hashes and collapse blank lines."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            stripped = stripped.lstrip('#').strip()
        if stripped:
            lines.append(stripped)
    return '\n\n'.join(
        block for block in '\n'.join(lines).split('\n\n') if block.strip()
    ).strip()


def _parse_llm_reflection(text: str) -> tuple[str, tuple[CoTStep, ...]] | None:
    """Split the model's Markdown into (puzzle, 3 steps), or None if unusable."""
    part1 = _PART1_RE.search(text)
    part2 = _PART2_RE.search(text)

    if part1 and part2 and part1.start() < part2.start():
        puzzle = _clean_section(text[part1.end(): part2.start()])
    else:
        return None

    cot_region = text[part2.end():] if part2 else ''
    markers = list(_STEP_MARKER_RE.finditer(cot_region))
    if len(markers) < 3:
        return None

    steps: list[CoTStep] = []
    for number in (1, 2, 3):
        marker = next(m for m in markers if int(m.group(1)) == number)
        following = [m.start() for m in markers if m.start() > marker.start()]
        end = following[0] if following else len(cot_region)
        body = _clean_section(cot_region[marker.end(): end])
        body = body.lstrip('：: ').strip()
        if not body:
            return None
        title = COT_STAGES[number - 1][0]
        steps.append(CoTStep(number=number, title=title, body=body))

    if not puzzle:
        return None
    return puzzle, tuple(steps)


def generate_reflection(
    article: Article,
    answers: list[str],
    client: LLMClient | None = None,
    allow_llm: bool = True,
) -> ReflectionResult:
    """Produce the end-of-session reflection, preferring the LLM when usable."""
    gists = [q.gist for q in article.questions][: len(answers)]
    local = build_local_reflection(article, answers, gists)

    if not allow_llm:
        return local

    pipeline = get_pipeline('cot_reflection_generator')
    answer_list = '\n'.join(
        f'{i + 1}. {text}' for i, text in enumerate(answers) if text.strip()
    )
    prompt = render_prompt(
        pipeline.first.prompt_template,
        article_title=f'{article.display_title}（{article.author}）',
        article_text=article.text,
        question_count=len([a for a in answers if a.strip()]),
        answer_list=answer_list,
        first_span='3',
        middle_span='4',
        last_span='3',
    )

    try:
        reply = (client or default_client()).complete(prompt)
    except LLMUnavailable as exc:
        return ReflectionResult(
            puzzle=local.puzzle,
            steps=local.steps,
            source='local',
            note=f'AI 暫時無法連線（{type(exc).__name__}），改用離線版反思',
        )

    parsed = _parse_llm_reflection(reply)
    if parsed is None:
        return ReflectionResult(
            puzzle=local.puzzle,
            steps=local.steps,
            source='local',
            note='AI 回覆格式不符，改用離線版反思',
        )

    puzzle, steps = parsed
    return ReflectionResult(
        puzzle=puzzle,
        steps=steps,
        source='llm',
        note='由 AI 國語老師生成',
    )
