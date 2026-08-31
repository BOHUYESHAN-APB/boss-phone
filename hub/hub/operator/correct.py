"""词表纠错层（DESIGN_OVERVIEW §8.3，Python 本地实现，无 LLM 依赖）。

专有名词（BWA/fastqc/hg38、仓库名、CLI 命令）识别差的解法不是换更强的 STT，
而是"词表约束纠错"。本层做确定性本地纠错——离线、可热更新（读 JSON 不烧固件）、
可度量（hub-lite --no-correct 关掉对比，见 §8.4 任务 3）。LLM 级音近纠错属
provider 之上的增强，本地层先兜底保证健壮。

三件套：
  1. user_terms  权威术语表 → 拉丁词大小写归一（词边界匹配，不误伤子串）
  2. fixes       音近/形近替换表 → 有序、长词优先替换
  3. trad2simp   繁简归一（内置常用字 + 用户可扩展）
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

# 权威术语表：来自实测/常见专有名词（§8.5）
DEFAULT_USER_TERMS = [
    "BWA", "hg38", "fastqc", "multiqc", "rebase", "PR", "clippy",
    "github", "ai-passport",
]

# 音近/形近替换表：(目标, [常见误识别名])——别名整词替换为目标
DEFAULT_FIXES: list[tuple[str, list[str]]] = [
    ("测试", ["特事"]),      # §8.5 01-daily
    ("汇总", ["会总"]),      # §8.5 03-bio-fastqc
    ("比对", ["比隊"]),      # §8.5 02-bio-bwa 繁简
    ("仓库", ["倉庫"]),      # §8.5 04-cli 繁简
    ("github", ["Graphub"]), # §8.5 05-mixed 音近
    ("内", ["內"]),          # §8.5 04-cli 繁简
]

# 繁→简常用字（内置子集，用户词表 JSON 可覆盖扩展）
DEFAULT_TRAD2SIMP: dict[str, str] = {
    "倉": "仓", "庫": "库", "內": "内", "體": "体", "國": "国", "與": "与",
    "為": "为", "說": "说", "時": "时", "現": "现", "點": "点", "當": "当",
    "會": "会", "員": "员", "車": "车", "門": "门", "問": "问", "題": "题",
    "實": "实", "驗": "验", "數": "数", "據": "据", "質": "质", "務": "务",
    "這": "这", "個": "个", "來": "来", "們": "们", "後": "后", "對": "对",
    "過": "过", "還": "还", "裡": "里", "於": "于", "級": "级", "結": "结",
    "組": "组", "織": "织", "壓": "压", "縮": "缩", "轉": "转", "寫": "写",
    "讀": "读", "頭": "头", "條": "条", "長": "长", "網": "网", "郵": "邮",
    "報": "报", "匯": "汇", "單": "单", "冊": "册", "約": "约", "給": "给",
    "參": "参", "經": "经", "統": "统", "維": "维", "護": "护", "課": "课", "證": "证",
    "認": "认", "製": "制", "訊": "讯", "話": "话", "語": "语", "請": "请",
    "講": "讲", "譯": "译", "資": "资", "輕": "轻", "輸": "输", "運": "运",
    "進": "进", "遠": "远", "選": "选", "釋": "释", "錯": "错", "鍵": "键",
    "關": "关", "陣": "阵", "隊": "队", "際": "际", "雲": "云", "電": "电",
    "頻": "频", "頁": "页", "風": "风", "養": "养", "餘": "余", "馬": "马",
    "鳥": "鸟", "鴻": "鸿", "號": "号", "號碼": "号码",
}


class TextCorrector:
    """确定性词表纠错器：user_terms 大小写归一 + fixes 替换 + 繁简归一。"""

    def __init__(
        self,
        user_terms: Iterable[str] = (),
        fixes: Iterable[tuple[str, list[str]]] = (),
        trad2simp: dict[str, str] | None = None,
    ) -> None:
        self.user_terms = list(user_terms) or list(DEFAULT_USER_TERMS)
        self.fixes = list(fixes) or list(DEFAULT_FIXES)
        self.trad2simp = dict(trad2simp) if trad2simp is not None else dict(DEFAULT_TRAD2SIMP)

        # 拉丁术语：词边界匹配（(?<![A-Za-z0-9])t(?![A-Za-z0-9])），
        # 避免误伤子串——例如 PR 不能改掉 Python 里的 "Py"。
        self._term_re = [
            (re.compile(rf"(?<![A-Za-z0-9]){re.escape(t)}(?![A-Za-z0-9])", re.IGNORECASE), t)
            for t in self.user_terms
        ]
        # 替换表摊平并按"别名长度降序"，保证长词优先匹配
        flat = [(a, t) for t, aliases in self.fixes for a in aliases]
        flat.sort(key=lambda x: len(x[0]), reverse=True)
        self._fixes = [(a, t) for a, t in flat]

    def correct(self, text: str) -> str:
        out = text
        # 1) 音近/形近替换（长词优先）
        for alias, target in self._fixes:
            out = out.replace(alias, target)
        # 2) 拉丁术语大小写归一（词边界）
        for rx, target in self._term_re:
            out = rx.sub(target, out)
        # 3) 繁简归一
        out = "".join(self.trad2simp.get(ch, ch) for ch in out)
        # 4) 空白归一（连续空白 → 单个空格，去首尾）
        return " ".join(out.split())

    def to_dict(self) -> dict:
        return {
            "user_terms": self.user_terms,
            "fixes": [[t, aliases] for t, aliases in self.fixes],
            "trad2simp": self.trad2simp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TextCorrector":
        return cls(
            user_terms=data.get("user_terms", ()),
            fixes=[(t, aliases) for t, aliases in data.get("fixes", ())],
            trad2simp=data.get("trad2simp"),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "TextCorrector":
        """从用户词表 JSON 加载（热更新：改文件重载即可，不烧固件）。"""
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls.from_dict(data)
