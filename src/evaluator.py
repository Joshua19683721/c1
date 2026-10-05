# -*- coding: utf-8 -*-
"""Pipeline 1 — option_evaluator.

Resolves one student answer to one of the four options and produces warm,
age-appropriate feedback.

Resolution cascade (each step only runs if the previous one abstains):

1. **Explicit number** — 3 / 第三個 / 我選二. Deterministic, instant, and exactly
   the 寬容數字解析 the specification puts first. No LLM call, so tapping or
   saying a number stays fast enough for a classroom.
2. **LLM judgement** — the option_evaluator pipeline from the YAML config, with
   its JSON reply validated against the real option list before it is trusted.
3. **Local fuzzy match** — the offline fallback for paraphrase and STT slips.
4. **Abstain** — hand back the best candidate as a *suggestion* for the student
   to confirm, rather than silently marking a real attempt wrong.

Step 2 being ahead of step 3 is deliberate: on the benchmark corpus the local
matcher accepts most paraphrases but is well below an LLM on free-form Chinese
paraphrase. Anything it is unsure about is worth spending a model call on.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import parser
from .content import Question
from .llm import LLMClient, LLMUnavailable, default_client, extract_json_object
from .prompts import get_pipeline, render_prompt

__all__ = ['EvaluationResult', 'evaluate_answer', 'feedback_for']

_NUMBER_HOWS = ('cued', 'bare', 'isolated')

#: Rotating praise so ten correct answers in a row never read like a machine.
_PRAISE = (
    '答對啦！你讀得很仔細喔！',
    '太棒了！就是這個意思！',
    '真厲害，這一題你完全掌握了！',
    '正確！你的想法和文章一樣呢！',
    '很好！繼續保持這個讀法！',
)

#: We deliberately do not vary the opener for wrong answers — a rotating set of
#: "抱歉" wastes a sixth grader's attention on the tone instead of the content.
_WRONG_OPENER = '再想想看喔！'


@dataclass(frozen=True)
class EvaluationResult:
    """Outcome of Pipeline 1 for a single attempt."""

    #: Option we are willing to act on (0-based), or None when unsure.
    index: int | None
    #: True/False once we know; None when the attempt could not be resolved.
    is_correct: bool | None
    selected_text: str
    feedback: str
    #: Which cascade step resolved it.
    how: str
    score: float
    #: Best candidate offered for confirmation when index is None.
    suggestion: int | None = None
    #: Human-readable diagnostic, e.g. why the LLM was skipped.
    note: str = ''

    @property
    def resolved(self) -> bool:
        return self.index is not None

    @property
    def needs_confirmation(self) -> bool:
        """True when we have a candidate to offer but will not auto-accept it."""
        return self.index is None and self.suggestion is not None


def _feedback_correct(question: Question) -> str:
    return _PRAISE[(question.number - 1) % len(_PRAISE)]


def feedback_for(question: Question, is_correct: bool, reveal: bool = False) -> str:
    """Deterministic fallback feedback.

    A wrong answer gets the question's own hint rather than the right option, so
    the student gets another chance instead of being told the answer.
    """
    if is_correct:
        return _feedback_correct(question)
    if reveal:
        return f'正確答案是第 {question.display_number} 個選項，你再讀一次文章看看。'
    hint = question.hint or '再讀一次文章，答案就藏在裡面喔。'
    return f'{_WRONG_OPENER} 提示：{hint}'


def _validate_llm_payload(
    payload: dict, question: Question
) -> tuple[int | None, str, bool | None]:
    """Check a model reply against the real option list before trusting it.

    A hallucinated index, or text that does not resemble the option it claims,
    is discarded rather than shown to a child.
    """
    raw_index = payload.get('detected_option_index')
    if isinstance(raw_index, str) and raw_index.strip().isdigit():
        raw_index = int(raw_index.strip())
    if not isinstance(raw_index, int) or not 0 <= raw_index < len(question.options):
        return None, '', None

    claimed = str(payload.get('selected_option_text', '') or '')
    actual = question.options[raw_index]
    if claimed.strip() and parser.normalize(claimed) != parser.normalize(actual):
        # The model picked a real option but described a different one.
        return raw_index, actual, None

    is_correct = payload.get('is_correct')
    if not isinstance(is_correct, bool):
        is_correct = None
    return raw_index, actual, is_correct


def _ask_llm(
    question: Question, student_input: str, client: LLMClient
) -> EvaluationResult | None:
    pipeline = get_pipeline('option_evaluator')
    prompt = render_prompt(
        pipeline.first.prompt_template,
        current_question=question.stem,
        opt1=question.options[0],
        opt2=question.options[1],
        opt3=question.options[2],
        opt4=question.options[3],
        correct_index=question.display_number,
        student_input=student_input,
    )
    try:
        reply = client.complete(prompt, json_mode=True)
        payload = extract_json_object(reply)
    except (LLMUnavailable, ValueError) as exc:
        return None

    index, selected_text, claimed = _validate_llm_payload(payload, question)
    if index is None:
        return None

    is_correct = claimed if claimed is not None else (index == question.correct_index)
    feedback = str(payload.get('feedback_message', '') or '').strip()
    if not feedback:
        feedback = feedback_for(question, is_correct)

    # The model can mis-grade itself; the answer key is authoritative.
    if is_correct != (index == question.correct_index):
        is_correct = index == question.correct_index
        feedback = feedback_for(question, is_correct)

    return EvaluationResult(
        index=index,
        is_correct=is_correct,
        selected_text=selected_text,
        feedback=feedback,
        how='llm',
        score=float(payload.get('score', 1.0) or 1.0),
        suggestion=index,
        note='由 AI 助教判讀',
    )


def _ask_local(question: Question, student_input: str) -> EvaluationResult:
    index, how, score = parser.combine_signals(student_input, question.options)

    if index is not None:
        is_correct = index == question.correct_index
        return EvaluationResult(
            index=index,
            is_correct=is_correct,
            selected_text=question.options[index],
            feedback=feedback_for(question, is_correct),
            how='number' if how in _NUMBER_HOWS else 'fuzzy',
            score=score,
            suggestion=index,
            note='本地寬容解析',
        )

    match = parser.fuzzy_match_option(student_input, question.options)
    return EvaluationResult(
        index=None,
        is_correct=None,
        selected_text='',
        feedback='我還聽不太懂耶，你可以直接按一個選項，或把答案的關鍵字說一次嗎？',
        how=match.how,
        score=match.score,
        suggestion=match.suggestion,
        note='無法確定，請學生確認',
    )


def evaluate_answer(
    question: Question,
    student_input: str,
    client: LLMClient | None = None,
    allow_llm: bool = True,
) -> EvaluationResult:
    """Resolve one student answer for one question.

    Parameters
    ----------
    question:
        The rung being asked; carries the options, key and hint.
    student_input:
        Raw text from a tap, the keyboard, or speech recognition.
    client:
        LLM backend. Defaults to the process-wide client.
    allow_llm:
        Set False to force the fully offline path (used by the tests).
    """
    text = (student_input or '').strip()
    if not text:
        return EvaluationResult(
            index=None,
            is_correct=None,
            selected_text='',
            feedback='先選一個答案，或說出你的想法吧！',
            how='empty',
            score=0.0,
        )

    # Stage 1 — explicit numbers win outright, no model call.
    index, how = parser.extract_option_index(text, len(question.options))
    if index is not None:
        is_correct = index == question.correct_index
        return EvaluationResult(
            index=index,
            is_correct=is_correct,
            selected_text=question.options[index],
            feedback=feedback_for(question, is_correct),
            how='number',
            score=1.0,
            suggestion=index,
            note='寬容數字解析',
        )

    note = '本地寬容解析'
    if allow_llm:
        result = _ask_llm(question, text, client or default_client())
        if result is not None:
            return result
        note = 'AI 暫時無法連線，改用本地寬容解析'

    fallback = _ask_local(question, text)
    return EvaluationResult(
        index=fallback.index,
        is_correct=fallback.is_correct,
        selected_text=fallback.selected_text,
        feedback=fallback.feedback,
        how=fallback.how,
        score=fallback.score,
        suggestion=fallback.suggestion,
        note=note,
    )
