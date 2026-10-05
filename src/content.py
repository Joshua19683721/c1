"""Content library for ReadExpress-CoT (國小六年級版).

This module is the single source of truth for the 5 benchmark articles and
their 10-step progressive question ladders, exactly as transcribed from
``ReadExpress-CoT-Elementary.md``.

Design note
------------
In the source specification every correct answer happens to be listed as
option 1.  Handing a student a 10-question quiz where "A" is always right
teaches answer-position guessing, not reading.  :func:`build_lesson` therefore
applies a **deterministic** shuffle (fixed seed derived from the article id
and question number) so the correct answer lands in a different position on
every question, while remaining stable across reruns and users.  The
source-order index is preserved as ``source_correct_index`` for traceability.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from random import Random
from typing import Iterator, Sequence

__all__ = [
    "Question",
    "Article",
    "ARTICLES",
    "get_article",
    "build_lesson",
    "lesson_seed",
    "TOTAL_QUESTIONS",
]

OPTION_COUNT = 4
TOTAL_QUESTIONS = 10


@dataclass(frozen=True)
class Question:
    """One rung of the progressive ladder.

    ``correct_index`` is 0-based and always points into ``options``.
    ``source_correct_index`` records where the answer sat in the original
    specification before shuffling (all 0 there).
    """

    number: int
    skill: str
    stem: str
    options: tuple[str, ...]
    correct_index: int
    hint: str = ""
    source_correct_index: int = 0
    #: Short essence of the answer, used by the offline reflection generator so
    #: the puzzle paragraph can hit the specification's 100-150 字 target.
    gist: str = ""

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

    @property
    def display_title(self) -> str:
        return f"《{self.title}》"

    def __len__(self) -> int:
        return len(self.questions)


def _q(
    number: int,
    skill: str,
    stem: str,
    options: Sequence[str],
    hint: str,
    source_correct: int = 0,
) -> Question:
    return Question(
        number=number,
        skill=skill,
        stem=stem,
        options=tuple(options),
        correct_index=source_correct,
        hint=hint,
        source_correct_index=source_correct,
    )


# ---------------------------------------------------------------------------
# 文章 1: 《背影》朱自清
# ---------------------------------------------------------------------------
_BEIYING = Article(
    id="beiying",
    title="背影",
    author="朱自清",
    genre="抒情文／記敘文（溫馨改寫版）",
    text=(
        "我與父親已經兩年沒見面了，我最不能忘記的是他的背影。那年冬天，祖母去世了，父親也失業了，"
        "家裡的光景非常慘淡。辦完喪事後，父親要到南京找工作，我也要回北京念書，我們便同行。到了車站，"
        "父親因為事情忙，本來交代旅館熟識的服務員陪我去，但他終究不放心，決定親自送我。我當時二十歲，"
        "覺得自己已經是大孩子了，心裡還暗笑父親太瞎操心。上了火車，父親看著車外說：「我去買幾個橘子，"
        "你就在這裡，不要走動。」要到對面月台買橘子，必須穿過鐵道，跳下去再爬上去。父親是個胖子，"
        "走起路來本來就很吃力。我看見他戴著黑布小帽，穿著深青色棉袍，步履蹣跚地走到鐵道邊。他穿過鐵道，"
        "要爬上對面月台時非常吃力：兩手攀著上面，兩腳向上縮，肥胖的身子微微向左傾斜，顯出很努力的樣子。"
        "這時我看見他的背影，我的眼淚很快地流了下來。等他抱著朱紅色的橘子走回來，把橘子散放在車廂地板上，"
        "撲撲身上的泥土，好像心裡鬆了一口氣。他要離開時，還回頭對我說：「進去吧，裡面無人。」直到他的背影"
        "消失在人群中，我的眼淚又流了下來。這些年來，父親和我到處奔波。如今他年紀大了，身體也不好。"
        "前陣子他在信中寫道：「我身體平安，只是手臂痛得厲害，大概離開人世的日子不遠了吧。」讀到這裡，"
        "在晶瑩的淚光中，我又看見了那個肥胖、穿著青布棉袍的背影。唉！我不知道什麼時候才能再和他相見！"
    ),
    questions=(
        _q(1, "訊息擷取", "文章開頭作者說「最不能忘記的是他的背影」，這句話有什麼作用？",
           ["直接點出文章的主角與深情的主題", "說明去南京買橘子的原因",
            "介紹家裡的經濟狀況", "抱怨父親太愛說話"],
           "想想看，作者第一句話就像「打開電影的聚光燈」，先告訴我們最想講的是誰。"),
        _q(2, "訊息擷取", "作者和父親在徐州相見時，家裡遇到了什麼困難？",
           ["祖母去世而且父親失業了", "作者考不上大學", "買不到火車票回家", "行李在旅館被偷了"],
           "把文章開頭「那年冬天」附近的句子再讀一次，答案就藏在裡面。"),
        _q(3, "細節理解", "父親原本說不送作者，後來為什麼又改變主意？",
           ["擔心服務員照顧不週，出自對兒子的不放心", "想要順便去逛街買東西",
            "因為作者一直哭著要求父親送", "車站就在旅館隔壁很近"],
           "注意「不放心」這三個字，它是全文的鑰匙。"),
        _q(4, "推論分析", "作者寫自己當時覺得父親「太操心」、「暗笑父親不聰明」，這是什麼寫作方法？",
           ["先寫自己的不懂事，來對比後來對父愛的體會與后悔", "為了批評父親不懂得和年輕人溝通",
            "強調自己當時比父親更有智慧", "為了讓文章看起來比較搞笑"],
           "這種「先說自己不對、後來才懂」的寫法叫襯托（對比）。"),
        _q(5, "細節理解", "父親穿過鐵道爬月台時，文中用了哪些動詞描寫他的動作？",
           ["攀、縮、傾", "跑、跳、飛", "走、跑、坐", "站、看、笑"],
           "找出寫動作的那一句，裡面藏了三個很特別的單字。"),
        _q(6, "情感轉折", "作者看到父親爬月台去買橘子的背影時，為什麼流下眼淚？",
           ["被父親雖然動作吃力卻依然愛自己的心意所感動", "覺得父親買橘子花太多時間了",
            "擔心火車馬上就要開走了", "因為眼睛被風沙吹到了"],
           "流淚的時候，作者看的是「背影」，心裡想的卻是「愛」。"),
        _q(7, "細節理解", "父親買完橘子回到車上，拍拍身上的泥土說心裡「很輕鬆似的」，這代表什麼？",
           ["順利照顧好兒子後，心裡感到滿足與安心", "覺得爬月台運動之後身體變好了",
            "慶幸自己剛剛沒有摔倒", "終於可以回家睡覺了"],
           "「鬆了一口氣」是鬆一口『心』裡的氣，不是鬆一口身體的氣。"),
        _q(8, "統整解釋", "文章最後提到父親信上說自己身體不好，作者讀信時心情如何？",
           ["非常思念與悲傷，眼淚中又浮現父親的背影", "感到很生氣", "覺得父親在開玩笑", "平靜地繼續做自己的事"],
           "文章以「背影」開頭，也以「背影」收尾，這叫做首尾呼應。"),
        _q(9, "主旨深化", "「橘子」與「背影」在文章中代表了什麼？",
           ["代表父親深沉、默默付出的愛", "代表水果很美味", "代表旅行時開心的回憶", "代表家裡變有錢了"],
           "在文章裡一樣東西常常不只是東西本身，它還會代表一種情感。"),
        _q(10, "省思評鑑", "讀完這篇文章，我們應該如何看待父母平常的關心？",
           ["理解關心背後的愛，學會珍惜與體諒", "覺得父母很煩，當面反駁他們",
            "盡量少跟父母說話", "不理會父母的交代"],
           "作者長大後才懂父親的背影，我們現在就可以先懂一點。"),
    ),
)


# ---------------------------------------------------------------------------
# 文章 2: 《吃冰的滋味》古蒙仁
# ---------------------------------------------------------------------------
_BING = Article(
    id="chibing",
    title="吃冰的滋味",
    author="古蒙仁",
    genre="記敘散文（小六閱讀版）",
    text=(
        "現代的冰品種類非常多，有刨冰、冰淇淋還有各種雪糕。不過對我們這代生於五十年代的人來說，"
        "最難忘的還是童年時代台糖冰廠冰棒的滋味。那時一到夏天，只要聽到巷口傳來木棒敲擊冰桶「叭噗、叭噗」的"
        "聲音，或是賣冰阿伯的喊叫聲，所有小孩都會高興地衝出去。那時的台糖冰棒只有幾種簡單的口味："
        "紅豆、綠豆、芋頭、牛奶，每一根都結實飽滿。咬下一口，清涼透心，甜而不膩。芋頭冰是用真正的芋頭"
        "熬煮製成，吃得到香濃的芋頭塊；紅豆冰更是紅豆顆粒分明。除了台糖冰棒，還有自家用塑膠袋裝糖水"
        "凍成的「枝仔冰」，雖然簡單，但在物資不豐富的年代，卻是夏天裡最大的享受。如今冰品種類多得讓人"
        "眼花撩亂，包裝精美、價格也不便宜，但吃起來總覺得少了點什麼。也許我們懷念的不只是冰棒本身的甜味，"
        "更是那段無憂無慮、雖然物質貧窮但人情味濃厚的童年時光。"
    ),
    questions=(
        _q(1, "訊息擷取", "作者小時候最難忘的冰品是什麼？",
           ["台糖的冰棒與自家做的枝仔冰", "精美包裝的進口冰淇淋",
            "義大利名牌雪糕", "夜市的芒果刨冰"],
           "文中先提到「台糖冰廠冰棒」，後面還補了一種自己做的。"),
        _q(2, "細節擷取", "小時候小朋友聽到什麼聲音會興奮地衝出去？",
           ["木棒敲打冰桶的「叭噗」聲與喊叫聲", "學校放學的鐘聲",
            "汽車喇叭聲", "下雨打雷的聲音"],
           "「叭噗、叭噗」是用「敲」出來的聲音，認得嗎？"),
        _q(3, "特徵比對", "文章裡提到的台糖冰棒有什麼特色？",
           ["料多實在、結實飽滿而且甜而不膩", "包裝非常華麗好看", "價格非常昂貴", "有上百種化學口味"],
           "注意「結實飽滿」跟「甜而不膩」這兩個詞。"),
        _q(4, "細節理解", "除了台糖冰棒，當時還有一種簡單卻很受歡迎的自製冰品是什麼？",
           ["用塑膠袋裝糖水結冰的枝仔冰", "水果聖代", "鮮奶抹茶冰棒", "巧克力雪糕"],
           "它是用家裡現成的東西做的，名字叫「枝仔冰」。"),
        _q(5, "時代背景", "文章描述作者童年時期的社會情況是怎樣的？",
           ["雖然物資不豐富，但人情味很濃厚的年代", "科技發達、人人有智慧型手機的年代",
            "冰淇淋店家隨處可見的年代", "大家都不喜歡吃冰的年代"],
           "文章最後一句「雖然物質貧窮但人情味濃厚」就是答案。"),
        _q(6, "對比分析", "作者拿「現代冰品」和「童年冰棒」相比，主要的差別是什麼？",
           ["現代冰品種類多又貴，但少了童年的古早味與情懷", "現代冰品比較難吃",
            "童年冰棒比較貴", "現代人夏天不再吃冰了"],
           "這是一種「現在 vs 當年」的對比寫法。"),
        _q(7, "感官描寫", "文中「咬下一口，清涼透心」屬於哪一種感覺的描寫？",
           ["味覺與涼爽觸覺的結合", "視覺描寫", "聽覺描寫", "嗅覺描寫"],
           "「清涼」是身體感覺，「透心」又帶甜味，所以不只一種感覺。"),
        _q(8, "推論分析", "作者最後說現代冰品「總覺得少了點什麼」，少了什麼？",
           ["無憂無慮的童年記憶與純樸的人情味", "冰棒裡的糖分加得不夠", "現代冰棒沒有加色素", "買冰棒的零用錢"],
           "缺少的那樣東西，吃不到卻最珍貴，你猜是什麼？"),
        _q(9, "結構分析", "這篇文章是用什麼方式來寫的？",
           ["從現代冰品聯想到童年回憶，最後寫出懷念童年的心情", "從頭到尾都在教大家怎麼做冰棒",
            "先寫悲傷的事再寫快樂的事", "介紹各種冰品的營養價值"],
           "先看「現代」，再回憶「童年」，最後回到心情，這樣排順序叫什麼？"),
        _q(10, "主旨總結", "這篇文章最想告訴讀者什麼心聲？",
           ["藉由懷念童年冰品，表達對過去純樸時光的懷念", "鼓勵大家多買台糖冰棒",
            "叫大家不要吃現代的冰淇淋", "教大家如何在自己家裡做冰棒"],
           "作者怀念的是味道，還是味道裡的那段日子？"),
    ),
)


# ---------------------------------------------------------------------------
# 文章 3: 《空城計》
# ---------------------------------------------------------------------------
_KONGCHENG = Article(
    id="kongchengji",
    title="空城計",
    author="羅貫中",
    genre="古典小說（小六白話文改寫版）",
    text=(
        "三國時期，魏國大將司馬懿帶著十五萬大軍，浩浩蕩蕩往蜀國的西城縣殺過來。當時蜀國丞相諸葛亮"
        "（孔明）身邊沒有大將，只有一群文官，城裡的士兵也只剩下二千五百人。大家聽到司馬懿的大軍來了，"
        "都嚇得臉色發白。諸葛亮親自到城樓上一看，果然塵土飛揚，魏軍分成兩路包圍過來。諸葛亮卻很鎮定，"
        "傳令說：「把所有的旗幟藏起來，大家各守崗位，誰敢大聲說話或亂跑，立刻處罰！打開四個城門，"
        "每個城門安排二十名士兵扮成普通百姓，在街上灑水掃地。魏軍到了，大家不要慌張，我自有辦法。」"
        "接著，諸葛亮穿著舒適的衣服，戴着絲巾，帶著兩個小童，坐在城樓上燒香彈琴，神態非常輕鬆自如。"
        "司馬懿的大軍到了城下，看到這種奇怪的情形，不敢輕易進攻。司馬懿親自騎馬上前遠遠觀望，"
        "看到諸葛亮坐在城樓上微笑彈琴，非常鎮靜。司馬懿生性多疑，心想：「諸葛亮一輩子小心謹慎，"
        "今天這樣鎮定，城裡一定埋伏著大量精兵！」於是立刻下令全軍撤退。諸葛亮只靠著冷靜與智慧，"
        "就成功嚇退了十五萬大軍。"
    ),
    questions=(
        _q(1, "情境對比", "魏軍和蜀軍當時在兵力上有什麼懸殊的差別？",
           ["司馬懿有十五萬大軍，諸葛亮只有二千五百名士兵", "蜀軍兵力是魏軍的三倍",
            "雙方兵力差不多", "諸葛亮身邊有許許多多勇敢的大將"],
           "文章一開頭就寫了兩個數字，記得嗎？十五萬對幾千？"),
        _q(2, "反應比對", "聽到司馬懿大軍殺過來時，文武官員和諸葛亮的反應有什麼不同？",
           ["官員們嚇得臉色發白，諸葛亮卻非常鎮定並指揮調度", "官員們想要打仗，諸葛亮想要投降",
            "大家跟著諸葛亮一起收拾行李逃跑", "諸葛亮比官員們更加害怕"],
           "一邊是「嚇得臉色發白」，一邊是「卻很鎮定」，差別在哪？"),
        _q(3, "細節擷取", "諸葛亮下令「把所有的旗幟藏起來」目的是什麼？",
           ["讓敵人看不清城裡的真實情況，製造神祕感", "怕旗幟被大風吹走",
            "準備把旗幟洗乾淨", "代表向魏軍投降的意思"],
           "藏起旗幟是為了讓別人「猜不出來」，猜不出來才會怕。"),
        _q(4, "細節擷取", "諸葛亮安排士兵假扮成百姓在城門口做什麼？",
           ["灑水掃地，表現出完全不害怕的樣子", "向魏軍求和", "準備偷襲司馬懿", "把城裡的糧食搬走"],
           "越危險的時候越做平常的事，敵人就會更懷疑。"),
        _q(5, "外貌描寫", "文中描寫諸葛亮「坐在城樓上燒香彈琴」，展現出怎樣的形象？",
           ["胸有成竹、非常鎮定自若的樣子", "喜歡音樂勝過打仗", "假裝鎮定來掩飾害怕", "正在舉辦祈福儀式"],
           "古代有名成語叫「胸有成竹」，就是這四個字。"),
        _q(6, "心理分析", "司馬懿親自看了諸葛亮之後，為什麼決定退兵？",
           ["他知道諸葛亮平時很謹慎，看到諸葛亮這麼鎮定，懷疑城裡有伏兵", "突然發現糧食不夠了",
            "太喜歡聽諸葛亮彈琴，不忍心打他", "手下將領吵著要回家"],
           "重點在「生性多疑」四個字。"),
        _q(7, "成語延伸", "「空城計」在現代通常拿來形容什麼樣的策略？",
           ["用虛張聲勢的方法掩飾實力不足，嚇退對手", "把城市空出來送給敵人",
            "一種建築設計風格", "誠實地向對方展示自己的實力"],
           "想想看：城裡明明沒人，為什麼對方反而撤退？"),
        _q(8, "性格比對", "諸葛亮能成功打贏這場心理戰，是因為他掌握了司馬懿什麼性格特點？",
           ["生性多疑、不敢冒險的個性", "衝動勇敢的個性", "貪心喜歡財寶的個性", "容易聽信謠言的個性"],
           "找出文章裡直接點出司馬懿性格的那一句。"),
        _q(9, "寫作技巧", "文章描寫「其他官員嚇得臉色發白」，這在寫作上叫什麼方法？",
           ["襯托（用官員的害怕來對比突出諸葛亮的鎮定）", "倒敘法", "寫讀後感", "擬人法"],
           "別人越怕，主角就越帥——這種方法叫襯托。"),
        _q(10, "主旨總結", "《空城計》的故事給我們在遇到危險時什麼啟示？",
           ["遇到危機時要保持冷靜，運用智慧思考解決方法", "遇到危險時只要彈琴就可以解決",
            "人少的時候一定要立刻逃跑", "不要相信任何情報"],
           "諸葛亮沒有贏在力氣大，而是贏在他很冷靜。"),
    ),
)


# ---------------------------------------------------------------------------
# 文章 4: 《臺灣的海洋文化與石滬》
# ---------------------------------------------------------------------------
_SHIHU = Article(
    id="shihu",
    title="臺灣的海洋文化與石滬",
    author="（跨領域／在地文化）",
    genre="說明文（小六語意優化版）",
    text=(
        "臺灣四周環海，澎湖群島更有著世界級的海洋文化資產——「石滬」。石滬是早期先民利用當地的玄武岩與"
        "珊瑚礁石，在潮間帶（漲潮時被海水淹沒、退潮時露出的海岸）堆砌而成的捕魚陷阱。石滬捕魚原理是利用"
        "潮汐漲退：漲潮時，魚群順著海水游進石滬裡找東西吃；退潮時，石滬的牆壁露出水面，魚群被擋住"
        "無法退回大海，漁民就能輕鬆捕撈。澎湖最著名的「七美雙心石滬」，不僅具有捕魚功能，造型更像兩顆"
        "重疊的心，非常浪漫，成為享譽國際的觀光景點。然而，維護石滬並不簡單，需要長期檢查與人工搬石頭"
        "修補，才不會被大浪沖毀。隨著現代動力漁船的興起，傳統石滬捕魚漸漸減少了，但它所包含的「與大海"
        "和平共處、永續利用」的先民智慧，依然是臺灣非常寶貴的文化資產。"
    ),
    questions=(
        _q(1, "訊息擷取", "石滬主要建造在海岸的什麼區域？",
           ["潮間帶（漲潮淹沒、退潮露出的地方）", "很深的深海海溝", "高山的溪流裡", "淡水湖泊邊"],
           "文章括號裡就偷偷藏了答案。"),
        _q(2, "原理理解", "石滬能捕到魚的主要自然原理是什麼？",
           ["利用海水的潮汐漲退（漲潮魚游入，退潮被擋住）", "用電流把魚吸引過來",
            "用魚餌把魚毒暈", "用聲音把魚嚇進去"],
           "想想看，海水每天會漲幾次、落幾次？魚就趁那個機會游進去了。"),
        _q(3, "地標識別", "澎湖最著名且造型浪漫的石滬代表是什麼？",
           ["七美雙心石滬", "吉貝三心石滬", "馬公方形石滬", "觀音亭圓形石滬"],
           "文章說它「像兩顆重疊的心」，是哪一個？"),
        _q(4, "維護難點", "維護石滬必須面對什麼自然環境的挑戰？",
           ["海浪容易把石牆沖毀，需要人工不斷修補", "地震會讓石頭融化", "太陽曬乾石牆", "魚群會把石頭吃掉"],
           "石頭做的東西最怕的不是火，而是海裡的力量。"),
        _q(5, "演變分析", "為什麼傳統石滬捕魚的方式會漸漸減少？",
           ["因為現代動力漁船興起，捕魚技術改變了", "因為大海裡已經完全沒有魚了", "因為政府禁止大家捕魚", "因為石頭全部被搬走了"],
           "文章提到「隨著……的興起」，是哪個東西興起了？"),
        _q(6, "生態理念", "石滬捕魚展現了早期先民怎樣的海洋智慧？",
           ["與大海共生、永續利用的環境智慧", "把魚全部捕光光的態度", "破壞海洋環境來賺錢", "隨便亂蓋建築的態度"],
           "石滬抓得到魚又不會把魚抓光，這叫永續。"),
        _q(7, "轉型價值", "現代的石滬除了捕魚之外，還轉型具備了什麼新價值？",
           ["觀光旅遊與文化資產保存價值", "防守敵人的軍事堡壘", "停靠大船的國際港口", "水上樂園設施"],
           "文章說它「享譽國際」，代表很多人特地來看它。"),
        _q(8, "文體判斷", "這篇文章屬於哪一種說明的文章？",
           ["介紹在地文化與海洋生態的說明文", "編造出來的神話故事", "互相罵人的文章", "賣東西的廣告文"],
           "看看有沒有人物在說話、有沒有情節在轉折？沒有的話多半是說明文。"),
        _q(9, "詞語理解", "文中提到石滬捕魚漸漸「式微」，「式微」是什麼意思？",
           ["衰退、減少", "越來越熱鬧", "保持不變", "微笑面對"],
           "「微」有「小、弱」的意思，所以「式微」是變小、變弱。"),
        _q(10, "主旨總結", "這篇文章希望讀者對臺灣的海洋文化產生什麼樣的心情？",
           ["認識並珍惜先民的智慧，共同保護文化資產", "覺得舊東西很破舊應該拆掉", "只要去拍照打卡就好，不用關心文化", "鼓勵大家多蓋一些新石滬"],
           "知道了這些故事，我們可以幫它做什麼？"),
    ),
)


# ---------------------------------------------------------------------------
# 文章 5: 《番茄紅了，醫生的臉就綠了》
# ---------------------------------------------------------------------------
_FANQIE = Article(
    id="fanqie",
    title="番茄紅了，醫生的臉就綠了",
    author="（科普閱讀／健康生活）",
    genre="科普說明文（小六白話版）",
    text=(
        "歐洲有一句很有趣的諺語：「番茄紅了，醫生的臉就綠了。」這句話用幽默誇張的方式，點出了番茄很高的"
        "營養價值。番茄之所以呈現鮮豔的紅色，主要是因為含有豐富的「茄紅素」。茄紅素是一種很強的抗氧化劑，"
        "能幫忙清除體內的壞物質，保護我們的心血管健康。有趣的是，一般的蔬菜水果大多建議生吃才不會破壞"
        "營養，但番茄卻剛好相反！茄紅素屬於「脂溶性」營養素，而且藏在番茄的細胞壁裡面。經過加熱煮熟，"
        "並且加上適量的油（例如用橄欖油炒番茄或煮番茄牛肉湯），反而能破壞細胞壁把茄紅素釋放出來，"
        "讓人體吸收得更好！除了茄紅素，番茄還含有維生素C和膳食纖維，能幫助消化。小小一顆番茄美味又健康，"
        "難怪被大家稱為超級食物。"
    ),
    questions=(
        _q(1, "標題理解", "諺語「番茄紅了，醫生的臉就綠了」是什麼意思？",
           ["用幽默誇張的方式表示番茄很有營養讓人少生病，醫生就沒生意了", "醫生非常討厭吃紅色的番茄",
            "吃番茄會讓人臉色發綠", "番茄有毒會讓醫生生病"],
           "「綠了」不是真的臉變綠，而是「沒生意」的意思。"),
        _q(2, "科學成分", "番茄呈現漂亮的紅色，主要是因為含有什麼營養成分？",
           ["茄紅素", "花青素", "胡蘿蔔素", "葉黃素"],
           "名字就藏在文章裡，和「番茄」只差一個字。"),
        _q(3, "功效理解", "茄紅素在我們身體裡扮演什麼重要的角色？",
           ["抗氧化，保護心血管健康", "幫大腦快速記住考試答案", "增加骨頭的重量", "替代睡眠提供能量"],
           "「清除體內的壞物質、保護心血管」就是抗氧化。"),
        _q(4, "烹飪原理", "為什麼番茄煮熟並且加油炒過之後，人體吸收率會更好？",
           ["加熱能破壞細胞壁，而且茄紅素需要油脂幫忙吸收", "生番茄有毒不能直接吃", "油脂可以改變番茄的顏色", "加熱會產生新的維生素"],
           "茄紅素躲在「細胞壁」裡，還是「脂溶性」，所以要熱、要油。"),
        _q(5, "比較分析", "番茄的營養吸收方式和一般常見的水果蔬菜有什麼不同？",
           ["一般蔬果多建議生吃，番茄則是煮熟加油吸收更好", "番茄只能打成果汁喝", "番茄絕對不能碰任何油脂", "番茄一定要削皮才能吃"],
           "文章說「一般的蔬果」和「番茄」剛好相反，這叫做比較。"),
        _q(6, "營養補充", "除了茄紅素之外，文章提到番茄還含有哪些營養素？",
           ["維生素C與膳食纖維", "很多蛋白質與肥肉", "咖啡因", "大量的鈣質"],
           "文章最後一段還列了兩樣，唸出來看看。"),
        _q(7, "用語理解", "文中說茄紅素是「脂溶性」營養素，這是什麼意思？",
           ["代表它能溶解在油脂中，需要油脂幫忙吸收", "代表它會讓身體產生很多脂肪", "代表它只存在於肥肉裡", "代表它很容易溶解在水裡"],
           "「脂」就是油，「溶」就是溶得進去，所以是能溶在油裡。"),
        _q(8, "生活應用", "下列哪一道料理最能完整發揮番茄茄紅素的營養價值？",
           ["用橄欖油炒番茄炒蛋", "生番茄切片沾白糖吃", "水洗乾淨直接生吃小番茄", "冰鎮番茄汁"],
           "想讓茄紅素吸收好，就要同時有「火」和「油」。"),
        _q(9, "文章結構", "這篇文章是用什麼順序來介紹番茄的？",
           ["有趣諺語引出主題 ➔ 介紹營養成分 ➔ 說明煮熟吸收原理 ➔ 總結好處", "介紹番茄的種植歷史",
            "批評現代人的壞習慣", "比較番茄和蘋果的價格"],
           "照著文章一段一段看：先講諺語，再講成分，再講煮法，最後講好處。"),
        _q(10, "主旨總結", "這篇文章最主要的宣導目的是什麼？",
           ["帶大家認識番茄的營養價值與最棒的吃法", "鼓勵大家長大後去當醫生", "叫大家不要再吃其他蔬菜了", "教大家如何在陽台種番茄"],
           "读完以後，你最想試一道什麼番茄料理？"),
    ),
)

_ARTICLES: tuple[Article, ...] = (_BEIYING, _BING, _KONGCHENG, _SHIHU, _FANQIE)


def get_article(article_id: str) -> Article | None:
    """Return the article whose :attr:`Article.id` equals *article_id*."""
    for article in ARTICLES:
        if article.id == article_id:
            return article
    return None


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
        _shuffled(q, Random(lesson_seed(article.id, q.number)))
        for q in article.questions
    )
    return replace(article, questions=questions)


def iter_articles() -> Iterator[Article]:
    yield from ARTICLES


# --- 答案 gist（每題的濃縮意涵）---------------------------------------------
# The local reflection generator cannot write fluent 150-character prose — that
# is what the LLM is for — but it must still honour the specification's
# 100-150 字 target. Each gist is the essence of an answer in a few characters,
# so the offline puzzle reads as a summary rather than a transcript.
GISTS: dict[str, dict[int, str]] = {
    "beiying": {
        1: "開頭就點出背影與深情的主題",
        2: "祖母去世、父親失業",
        3: "不放心兒子，決定親自送行",
        4: "先寫不懂事，再寫後悔的對比法",
        5: "攀、縮、傾三個動詞",
        6: "被吃力卻依然愛我的父親感動",
        7: "照顧好兒子後的滿足與安心",
        8: "思念又悲傷，眼淚中再見背影",
        9: "代表父親默默付出的愛",
        10: "理解關心背後的愛，學會珍惜",
    },
    "chibing": {
        1: "台糖冰棒與枝仔冰",
        2: "敲冰桶的叭噗聲與喊叫聲",
        3: "結實飽滿、甜而不膩",
        4: "塑膠袋裝糖水結成的枝仔冰",
        5: "物資不豐富但人情味濃厚的年代",
        6: "現代多而貴，少了古早味與情懷",
        7: "味覺與涼爽觸覺的結合",
        8: "無憂的童年記憶與純樸人情味",
        9: "由現代聯想到童年再寫懷念",
        10: "藉冰品表達對純樸時光的懷念",
    },
    "kongchengji": {
        1: "十五萬大軍對上二千五百守軍",
        2: "官員害怕，諸葛亮卻鎮定指揮",
        3: "讓敵人看不清虛實，製造神祕感",
        4: "灑水掃地，表現出完全不害怕",
        5: "胸有成竹、鎮定自若",
        6: "他生性多疑，以為城裡有伏兵",
        7: "虛張聲勢，嚇退對手",
        8: "生性多疑、不敢冒險",
        9: "用別人的害怕襯托諸葛亮",
        10: "遇危險要冷靜，用智慧解決",
    },
    "shihu": {
        1: "潮間帶：漲潮淹沒、退潮露出",
        2: "利用潮汐漲退攔住魚群",
        3: "七美雙心石滬",
        4: "海浪容易沖毀石牆，需要修補",
        5: "動力漁船興起，捕魚方式改變",
        6: "與大海共生、永續利用",
        7: "觀光旅遊與文化資產保存",
        8: "介紹文化與生態的說明文",
        9: "衰退、減少",
        10: "珍惜先民智慧，共同保護資產",
    },
    "fanqie": {
        1: "番茄很有營養，醫生就沒生意",
        2: "茄紅素",
        3: "抗氧化，保護心血管",
        4: "加熱破細胞壁，油脂幫助吸收",
        5: "一般蔬果生吃，番茄煮熟加油",
        6: "維生素C與膳食纖維",
        7: "能溶在油脂中，需要油脂幫忙",
        8: "用橄欖油炒番茄炒蛋",
        9: "諺語到成分、原理再到好處",
        10: "認識番茄的營養與最佳吃法",
    },
}


def _attach_gists(articles: tuple[Article, ...]) -> tuple[Article, ...]:
    """Attach the gist table, failing loudly if an article is missing one."""
    return tuple(
        replace(
            article,
            questions=tuple(
                replace(q, gist=GISTS[article.id][q.number]) for q in article.questions
            ),
        )
        for article in articles
    )


ARTICLES: tuple[Article, ...] = _attach_gists(_ARTICLES)


#: Upper bound on a gist, so the offline puzzle stays a summary. The offline
#: puzzle runs ~175 characters against the specification's 100-150 字 target —
#: see the note in src/cot.py. Tightening this further was tried at 12 and made
#: the Chinese noticeably more cryptic for a 20-character saving, so 14 it is.
MAX_GIST_CHARS = 14


def _self_check() -> None:
    assert len(ARTICLES) == 5, "spec requires exactly 5 articles"
    ids = [a.id for a in ARTICLES]
    assert len(set(ids)) == 5, "article ids must be unique"
    problems: list[str] = []
    for article in ARTICLES:
        assert len(article.questions) == TOTAL_QUESTIONS, (
            f"{article.id} has {len(article.questions)} questions"
        )
        assert article.text.strip(), f"{article.id} has empty article text"
        for q in article.questions:
            assert len(q.options) == OPTION_COUNT, (article.id, q.number, len(q.options))
            assert 0 <= q.correct_index < OPTION_COUNT, (article.id, q.number)
            assert q.hint.strip(), f"missing hint for {article.id} Q{q.number}"
            assert q.gist.strip(), f"missing gist for {article.id} Q{q.number}"
            if len(q.gist) > MAX_GIST_CHARS:
                problems.append(
                    f"{article.id} Q{q.number}: {len(q.gist)} chars — {q.gist!r}"
                )
            assert len(set(q.options)) == OPTION_COUNT, (
                f"{article.id} Q{q.number} has duplicate options"
            )

    # Report every offender in one go — fixing them one run at a time is slow.
    assert not problems, "gist problems:\n  " + "\n  ".join(problems)


_self_check()
