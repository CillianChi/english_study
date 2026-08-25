"""Static category code -> display name lookup.

Category names live in code, not in the DB, because they're a fixed
31-entry taxonomy shared by every word — no reason to duplicate the
string on every row (that's what caused the original category_code bug).
"""

CATEGORY_NAMES: dict[str, str] = {
    "WORK": "職場／辦公室日常",
    "TITLE": "職稱與部門角色",
    "MEET": "會議與簡報",
    "HR": "人資／招聘",
    "FIN": "財務／會計",
    "BANK": "銀行與投資",
    "MKT": "行銷與業務",
    "ORDER": "採購／訂單",
    "MFG": "生產與製造",
    "LOG": "物流與運輸",
    "CS": "客戶服務",
    "LEGAL": "法律與合約",
    "TRAVEL": "差旅與交通",
    "HOTEL": "飯店與住宿",
    "FOOD": "餐飲",
    "SHOP": "購物與零售",
    "HOME": "居家／房間／家具",
    "HEALTH": "醫療與健康",
    "TECH": "科技與電腦",
    "EDU": "教育與學術",
    "WEATHER": "天氣與環境",
    "GOV": "政府／公共事務",
    "MEDIA": "媒體與傳播",
    "ARTS": "藝術娛樂／運動休閒",
    "EMOTION": "情緒與個性形容詞",
    "TIME": "時間／頻率／程度副詞",
    "VERB": "通用商務動詞",
    "FUNC": "連接詞／介系詞等功能詞",
    "GENN": "一般名詞",
    "GENADJ": "一般形容詞",
    "GENADV": "一般副詞",
}
