# -*- coding: utf-8 */
"""寓言與童話類文章（待補）。

訓練重點：推論寓意並連結到生活應用。篇幅短，適合練習歸納。

新增文章的方式：直接複製同類別既有的 q(...) 結構，改成新的題目，
再把 Article 加進底下的 ARTICLES tuple 即可。
src/content.py 在 import 時會檢查每一篇的題數、選項數、提示、解析與 gist，
有缺漏會立刻報錯，所以補文章時漏填欄位不可能悄悄通過。
"""

from __future__ import annotations

from ..content import Article

CATEGORY = "fable"

ARTICLES: tuple[Article, ...] = ()
