# -*- coding: utf-8 */
"""閱讀素養分類registry — 對應 108 課綱的領域與段能力。

每個類別是一個 slug,對應 src/categories/ 底下的一個模組。
文章寫在類別模組裡,不集中在 content.py —— 上千篇如果塞在同一個檔案,
那會是一個沒有人敢動的巨型檔案。
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ['Category', 'CATEGORIES', 'CATEGORY_ORDER', 'category_by_slug']


@dataclass(frozen=True)
class Category:
    slug: str
    label: str
    icon: str
    blurb: str


CATEGORIES: dict[str, Category] = {
    c.slug: c
    for c in (
        Category(
            slug="narrative",
            label="記敘與抒情",
            icon="\U0001F4DC",
            blurb="寫人、寫事、寫心情。訓練學生跟著敘事線索還原畫面與情感。",
        ),
        Category(
            slug="expository",
            label="說明與科普",
            icon="\U0001F52C",
            blurb="說明一件事的原理與結構。訓練判斷資訊之間的因果關係。",
        ),
        Category(
            slug="classical",
            label="古典與成語",
            icon="\U0001F3EE",
            blurb="古文、詩詞與成語故事。訓練字詞理解與古今語意對照。",
        ),
        Category(
            slug="myth_biography",
            label="神話與傳記",
            icon="\U0001F409",
            blurb="神話與人物傳記。訓練讀出先民的想像，以及傳記中的時間與轉折。",
        ),
        Category(
            slug="poetry",
            label="現代詩",
            icon="\U0001F33B",
            blurb="用分行與意象表達感受。訓練學生辨識比喻與通感。",
        ),
        Category(
            slug="fiction",
            label="小說與戲劇",
            icon="\U0001F3AD",
            blurb="有人物、有情節、有轉折。訓練預測與推論。",
        ),
        Category(
            slug="taiwan",
            label="臺灣文化與鄉土",
            icon="\U0001F5FA\uFE0F",
            blurb="這塊土地上的生活與技藝。訓練理解地方文化如何形成。",
        ),
        Category(
            slug="society",
            label="人物、社會與環境",
            icon="\U0001F30D",
            blurb="人如何和世界相處。訓練分辨論點、找出價值立場。",
        ),
        Category(
            slug="argument_application",
            label="議論與應用",
            icon="\u2696\ufe0f",
            blurb="議論文與應用文。訓練分辨論點與論據，並讀懂書信、啟事、說明書的格式。",
        ),
        Category(
            slug="fable",
            label="寓言與童話",
            icon="\U0001F9D9",
            blurb="短小的故事包著一個道理。訓練推論寓意與應用。",
        ),
    )
}

#: 顯示順序（依導覽層次：由敘事到應用）。
CATEGORY_ORDER: tuple[str, ...] = (
    "narrative",
    "expository",
    "classical",
    "myth_biography",
    "poetry",
    "fiction",
    "taiwan",
    "society",
    "argument_application",
    "fable",
)


def category_by_slug(slug: str) -> Category | None:
    return CATEGORIES.get(slug)
