"""hub 逻辑测试：词表纠错层（DESIGN_OVERVIEW §8.3/§8.6）。"""

from hub.operator.correct import TextCorrector


def test_bio_cli_term_cases():
    """§8.5 五样本实测输出的纠错收益。"""
    cases = [
        ("会让小张把特事跑一遍。", "会让小张把测试跑一遍。"),
        ("8BWA比隊跑一遍,參考基因組用HG38。", "8BWA比对跑一遍,参考基因组用hg38。"),
        (
            "用fastq 检查一下测序数据的质量,然后用multiq会总。",
            "用fastq 检查一下测序数据的质量,然后用multiq汇总。",
        ),
        (
            "在內,Passport倉庫上rebase一下主分支,然後提交PR。",
            "在内,Passport仓库上rebase一下主分支,然后提交PR。",
        ),
        (
            "看一下Graphub，CI的結果，clippy的警告都修掉。",
            "看一下github，CI的结果，clippy的警告都修掉。",
        ),
    ]
    c = TextCorrector()
    for raw, expect in cases:
        assert c.correct(raw) == expect, f"\nraw={raw}\ngot={c.correct(raw)}\nexp={expect}"


def test_word_boundary_no_false_positive():
    """拉丁术语词边界匹配：PR 不误伤 Python。"""
    c = TextCorrector()
    assert c.correct("用Python写PR") == "用Python写PR"
    assert c.correct("看下Github的CI") == "看下github的CI"


def test_user_terms_override():
    """用户词表 JSON 热更新：可覆盖/扩展。"""
    c = TextCorrector.from_dict({"user_terms": ["MYGENE"], "fixes": [], "trad2simp": {}})
    assert c.correct("mygene") == "MYGENE"
