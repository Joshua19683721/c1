# -*- coding: utf-8 */
"""Content model and loader for ReadExpress-CoT (國小六年級版).

The article text itself lives in src/categories/<slug>.py, one module per
108 課綱 reading domain. This module owns the data model, the aggregator and
the option shuffling.

Why split: the specification asks for 200 articles. 200 articles in a single
file is a ~1.4 MB module that nobody dares touch, and every addition risks
colliding with unrelated edits. One module per category means adding an article
is adding a small file.

Article fields
--------------
id, title, author, genre, text, questions, category

Every question additionally carries:

hint        A nudge used when the student is wrong. Deliberately does NOT
            give the answer away, so the student gets another try.
explanation Why the correct option is correct. Shown after an attempt, and
            this is what turns a wrong answer into a learning moment.
gist       A few-character essence, used by the offline reflection generator.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from hashlib import sha256
from importlib import import_module
from random import Random
from typing import Sequence

from .categories import CATEGORY_ORDER

__all__ = [
    "Q",
    "article",
    "q",
    "Question",
    "Article",
    "ARTICLES",
    "BY_CATEGORY",
    "get_article",
    "build_lesson",
    "lesson_seed",
    "articles_in_category",
    "DAYS_IN_YEAR",
    "day_of_year",
    "daily_article",
    "article_for_day",
    "today_lessons",
    "TOTAL_QUESTIONS",
    "OPTION_COUNT",
    "MAX_GIST_CHARS",
]

OPTION_COUNT = 4
TOTAL_QUESTIONS = 10

#: Upper bound on a gist, so the offline puzzle stays a summary. The offline
#: puzzle runs ~175 characters against the specification's 100-150 字 target —
#: see the note in src/cot.py. Tightening this further was tried at 12 and made
#: the Chinese noticeably more cryptic for a 20-character saving, so 14 it is.
MAX_GIST_CHARS = 14


@dataclass(frozen=True)
class Question:
    """One rung of the progressive ladder.

    ``correct_index`` is 0-based and always points into ``options``.
    """

    number: int
    skill: str
    stem: str
    options: tuple[str, ...]
    correct_index: int
    hint: str = ""
    explanation: str = ""
    gist: str = ""
    source_correct_index: int = 0

    @property
    def correct_text(self) -> str:
        return self.options[self.correct_index]

    @property
    def display_number(self) -> int:
        """Human-facing 1-based number of the correct option."""
        return self.correct_index + 1


@dataclass(frozen=True)
class Article:
    id: str
    title: str
    author: str
    genre: str
    text: str
    questions: tuple[Question, ...]
    category: str = "narrative"
    #: 1-based day of the year this article is scheduled for (1..365). Assigned
    #: from position within the category unless the module sets it explicitly.
    day: int = 0

    @property
    def display_title(self) -> str:
        return f"《{self.title}》"

    def __len__(self) -> int:
        return len(self.questions)


def Q(
    skill: str,
    stem: str,
    options: str,
    correct_index: int,
    hint: str,
    explanation: str,
    gist: str,
) -> tuple[str, str, str, int, str, str, str]:
    """One question, written on a single line.

    Options are packed into one pipe-separated string. A little cryptic to read,
    but this library is heading for thousands of questions and the expanded form
    costs roughly twice as much to write and review. The expanded q() below stays
    available for when readability matters more than volume.

    Question numbers are assigned by article(), so they cannot drift out of
    order as questions are added.
    """
    parts = tuple(part.strip() for part in options.split('|'))
    if len(parts) != OPTION_COUNT:
        raise ValueError(
            f'expected {OPTION_COUNT} options, got {len(parts)}: {options!r}'
        )
    if len(set(parts)) != OPTION_COUNT:
        raise ValueError(f'duplicate option: {options!r}')
    if not 0 <= correct_index < OPTION_COUNT:
        raise ValueError(f'correct_index out of range: {options!r}')
    return (skill, stem, options, correct_index, hint, explanation, gist)


def article(
    id: str,
    title: str,
    author: str,
    genre: str,
    text: str,
    questions: Sequence[tuple[str, str, str, int, str, str, str]],
    category: str,
) -> Article:
    """Build an Article from the compact Q() form.

    Question numbers are assigned here rather than written by hand, which is one
    fewer thing to get wrong in a 4,000-question library.
    """
    built = tuple(
        q(
            number, skill, stem,
            tuple(part.strip() for part in packed.split('|')),
            hint, explanation, gist, correct_index,
        )
        for number, (skill, stem, packed, correct_index, hint, explanation, gist)
        in enumerate(questions, start=1)
    )
    return Article(
        id=id, title=title, author=author, genre=genre, text=text,
        questions=built, category=category,
    )

def q(
    number: int,
    skill: str,
    stem: str,
    options: tuple[str, ...],
    hint: str,
    explanation: str,
    gist: str,
    correct_index: int = 0,
) -> Question:
    """Terse constructor for a question written by hand in a category module.

    ``correct_index`` is 0-based and defaults to 0, matching how the
    specification lists the answers; build_lesson() shuffles from there.
    """
    return Question(
        number=number,
        skill=skill,
        stem=stem,
        options=options,
        correct_index=correct_index,
        hint=hint,
        explanation=explanation,
        gist=gist,
        source_correct_index=correct_index,
    )


def _load_categories() -> tuple[Article, ...]:
    """Import every category module and concatenate what it exports.

    A missing module is an error rather than a silent empty list: a typo in a
    slug would otherwise look like "this category has no articles yet".
    """
    articles: list[Article] = []
    for slug in CATEGORY_ORDER:
        module = import_module(f"{__package__}.categories.{slug}")
        articles.extend(getattr(module, "ARTICLES", ()))
    return tuple(articles)


#: 每天一篇：一年 365 個位置。閏年的第 366 天沿用第 365 天。
DAYS_IN_YEAR = 365


def _assign_days(articles: Sequence[Article]) -> tuple[Article, ...]:
    """Give every article a slot in the year.

    A category module may pin an explicit day; anything left at 0 takes the
    next free position in that category. Sequential positions mean the exported
    day map is stable: re-running the export never reshuffles the calendar.
    """
    counters: dict[str, int] = {}
    assigned: list[Article] = []
    for article in articles:
        counters[article.category] = counters.get(article.category, 0) + 1
        if article.day:
            assigned.append(article)
        else:
            assigned.append(replace(article, day=counters[article.category]))
    return tuple(assigned)


ARTICLES: tuple[Article, ...] = _assign_days(_load_categories())

BY_CATEGORY: dict[str, tuple[Article, ...]] = {
    slug: tuple(a for a in ARTICLES if a.category == slug) for slug in CATEGORY_ORDER
}


def day_of_year(when: date | None = None) -> int:
    """1-based day of the year for *when* (today by default)."""
    return (when or date.today()).timetuple().tm_yday


def article_for_day(slug: str, day: int) -> Article | None:
    """The article this category reads on day-of-year *day*.

    An article whose day matches wins. Until a category is filled to 365, the
    remaining days fall back to cycling through what exists, so the app always
    has something to show on the way to a full library.
    """
    group = BY_CATEGORY.get(slug, ())
    if not group:
        return None
    slot = min(max(day, 1), DAYS_IN_YEAR)
    for article in group:
        if article.day == slot:
            return article
    return group[(slot - 1) % len(group)]


def daily_article(slug: str, when: date | None = None) -> Article | None:
    """The article this category reads on *when* (today by default)."""
    return article_for_day(slug, day_of_year(when))


def today_lessons(when: date | None = None) -> tuple[tuple[str, Article | None], ...]:
    """(slug, today's article) for every category, in navigation order."""
    return tuple((slug, daily_article(slug, when)) for slug in CATEGORY_ORDER)


def get_article(article_id: str) -> Article | None:
    for article in ARTICLES:
        if article.id == article_id:
            return article
    return None


def articles_in_category(slug: str) -> tuple[Article, ...]:
    return BY_CATEGORY.get(slug, ())


def lesson_seed(article_id: str, question_number: int) -> int:
    """Stable per-question seed so option shuffling never shifts between runs."""
    digest = sha256(f"{article_id}::{question_number}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _shuffled(question: Question, rng: Random) -> Question:
    order = list(range(len(question.options)))
    rng.shuffle(order)
    new_options = tuple(question.options[i] for i in order)
    new_correct = order.index(question.correct_index)
    return replace(question, options=new_options, correct_index=new_correct)


def build_lesson(article_id: str, shuffle: bool = True) -> Article:
    """Return an :class:`Article` ready to be shown to a student.

    When *shuffle* is ``True`` (the default) each question's four options are
    permuted with a deterministic seed, so the correct answer is not always
    option 1.  Set ``shuffle=False`` to reproduce the specification layout
    verbatim.
    """
    article = get_article(article_id)
    if article is None:
        raise KeyError(f"unknown article id: {article_id!r}")
    if not shuffle:
        return article
    questions = tuple(
        _shuffled(item, Random(lesson_seed(article.id, item.number)))
        for item in article.questions
    )
    return replace(article, questions=questions)


def _self_check() -> list[str]:
    """Validate the whole library at import time.

    Returns the list of problems rather than raising on the first one, so a
    content mistake shows up once with everything that is wrong.
    """
    problems: list[str] = []

    seen: set[str] = set()
    for article in ARTICLES:
        if article.id in seen:
            problems.append(f"duplicate article id: {article.id}")
        seen.add(article.id)

        if article.category not in BY_CATEGORY:
            problems.append(f"{article.id}: unknown category {article.category!r}")
        if not article.text.strip():
            problems.append(f"{article.id}: empty article text")

        if len(article.questions) != TOTAL_QUESTIONS:
            problems.append(
                f"{article.id}: {len(article.questions)} questions, expected {TOTAL_QUESTIONS}"
            )

        for number, item in enumerate(article.questions, start=1):
            where = f"{article.id} Q{item.number}"
            if item.number != number:
                problems.append(f"{where}: out of order, expected number {number}")
            if len(item.options) != OPTION_COUNT:
                problems.append(f"{where}: {len(item.options)} options, expected {OPTION_COUNT}")
            if len(set(item.options)) != OPTION_COUNT:
                problems.append(f"{where}: duplicate options")
            if not 0 <= item.correct_index < OPTION_COUNT:
                problems.append(f"{where}: correct_index out of range")
            if not item.hint.strip():
                problems.append(f"{where}: missing hint")
            if not item.explanation.strip():
                problems.append(f"{where}: missing explanation")
            if not item.gist.strip():
                problems.append(f"{where}: missing gist")
            elif len(item.gist) > MAX_GIST_CHARS:
                problems.append(f"{where}: gist is {len(item.gist)} chars (max {MAX_GIST_CHARS})")

    return problems


_PROBLEMS = _self_check()
if _PROBLEMS:
    raise AssertionError(
        "content library problems:\n  " + "\n  ".join(_PROBLEMS[:20])
        + (f"\n  … and {len(_PROBLEMS) - 20} more" if len(_PROBLEMS) > 20 else "")
    )
