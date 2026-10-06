# -*- coding: utf-8 -*-
"""Fallback Simplified to Traditional character table.

Generated from OpenCC's s2t table for the characters listed in
src.zh.SIMPLIFIED_ONLY. It exists so the classroom guarantee does not
quietly disappear when the optional OpenCC dependency is missing: without
it to_traditional() returned the model reply untouched, and a Simplified
reflection would reach the screen unchanged.

OpenCC stays the primary converter. This table only covers single
characters, so phrase level Taiwan wording (軟體 over 軟件) is not handled
here.
"""

from __future__ import annotations

__all__ = ['FALLBACK_PAIRS', 'FALLBACK_MAP']

#: Alternating simplified/traditional characters, two per entry.
FALLBACK_PAIRS = (
    '们們个個静靜现現学學书書说說语語读讀写寫给給应應该該认認识識这這么麼为爲吗嗎体體对對错錯进進过過还還没沒点點热熱爱愛双雙边邊万萬与與专專'
    '东東丝絲严嚴丧喪狮獅猫貓猪豬鸡雞鸭鴨鹅鵝马馬鸟鳥鱼魚龙龍龟龜蚁蟻蚂螞铁鐵银銀铅鉛纸紙笔筆图圖馆館记記声聲听聽观觀见見觉覺变變让讓谁誰请請'
    '谢謝讲講词詞语語门門问問间間关關开開无無长長为爲车車动動务務员員园園围圍场場处處复復备備够夠头頭妇婦妈媽宝寶实實将將层層岁歲师師帮幫广廣'
    '当當录錄忆憶忧憂怀懷态態总總恶惡戏戲战戰户戶报報担擔数數旧舊时時显顯术術机機条條极極树樹样樣检檢欢歡气氣汉漢汤湯沟溝泪淚济濟湾灣满滿灯燈'
    '灵靈烦煩烧燒赏賞虫蟲写寫览覽团團圆圓坚堅奖獎怜憐恳懇撑撐摇搖摊攤兴興乐樂习習义義乡鄉亲親众衆优優会會传傳伤傷价價仅僅从從仓倉仪儀产產亚亞'
)

FALLBACK_MAP: dict[str, str] = {
    FALLBACK_PAIRS[i]: FALLBACK_PAIRS[i + 1]
    for i in range(0, len(FALLBACK_PAIRS), 2)
}
