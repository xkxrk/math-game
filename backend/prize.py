"""大乐透奖金等级计算(支持双规则)。

自第26014期(2026年1月31日)起，奖级从9个合并为7个。
- 期号 < 26014: 旧规则(9级)
- 期号 >= 26014: 新规则(7级)

旧规则(9级)固定奖金:
  三等奖: 5+0     10,000元
  四等奖: 4+2      3,000元
  五等奖: 4+1        300元
  六等奖: 3+2        200元
  七等奖: 4+0        100元
  八等奖: 3+1 / 2+2   15元
  九等奖: 3+0 / 2+1 / 1+2 / 0+2  5元
  不中:   2+0 / 1+1 / 0+1 / 1+0 / 0+0

新规则(7级)固定奖金:
  三等奖: 5+0 / 4+2    奖池<8亿: 5,000元  奖池≥8亿: 6,666元
  四等奖: 4+1          奖池<8亿: 300元    奖池≥8亿: 380元
  五等奖: 4+0 / 3+2    奖池<8亿: 150元    奖池≥8亿: 200元
  六等奖: 3+1 / 2+2    奖池<8亿: 15元     奖池≥8亿: 18元
  七等奖: 3+0 / 2+1 / 1+2 / 0+2  奖池<8亿: 5元  奖池≥8亿: 7元
  不中:   2+0 / 1+1 / 0+1 / 1+0 / 0+0
"""

# 规则变更期号: 自第26014期起执行新规则
RULE_CHANGE_ISSUE = "26014"

# 8亿元奖池阈值(仅新规则使用)
HIGH_POOL_THRESHOLD = 8_0000_0000  # 8亿

# ===== 新规则(7级)固定奖金表 =====
FIXED_PRIZES_NEW = {
    3: {"low": 5000, "high": 6666},
    4: {"low": 300, "high": 380},
    5: {"low": 150, "high": 200},
    6: {"low": 15, "high": 18},
    7: {"low": 5, "high": 7},
}

# ===== 旧规则(9级)固定奖金表 =====
# 旧规则无8亿奖池上浮机制，统一金额
FIXED_PRIZES_OLD = {
    3: 10_000,   # 三等奖: 5+0
    4: 3_000,    # 四等奖: 4+2
    5: 300,      # 五等奖: 4+1
    6: 200,      # 六等奖: 3+2
    7: 100,      # 七等奖: 4+0
    8: 15,       # 八等奖: 3+1 / 2+2
    9: 5,        # 九等奖: 3+0 / 2+1 / 1+2 / 0+2
}

# 浮动奖金默认值(当期无实际数据时使用)
DEFAULT_FLOATING = {
    1: 5_000_000,   # 一等奖默认500万
    2: 200_000,     # 二等奖默认20万
}

BET_COST = 2  # 每注2元


def is_new_rule(issue: str) -> bool:
    """判断指定期号是否使用新规则(>=26014)。"""
    if not issue:
        return True  # 默认新规则
    return str(issue).strip().zfill(5) >= RULE_CHANGE_ISSUE


def calc_prize(
    pred_reds: list,
    pred_blues: list,
    actual_reds: list,
    actual_blues: list,
    first_prize_amount: str = "",
    second_prize_amount: str = "",
    prize_pool: str = "",
    issue: str = "",
) -> dict:
    """计算单注奖金(按期号自动选择规则版本)。

    返回: {
        "level": 等级(0=不中, 1-9),
        "amount": 奖金金额(元),
        "red_hits": 前区命中数,
        "blue_hits": 后区命中数,
        "desc": 描述,
        "rule": "new" / "old",
    }
    """
    pred_r = set(int(x) for x in pred_reds)
    pred_b = set(int(x) for x in pred_blues)
    actual_r = set(int(x) for x in actual_reds)
    actual_b = set(int(x) for x in actual_blues)

    r_hits = len(pred_r & actual_r)
    b_hits = len(pred_b & actual_b)

    use_new = is_new_rule(issue)
    if use_new:
        level = _get_level_new(r_hits, b_hits)
        pool_high = _is_high_pool(prize_pool)
        amount = _get_amount_new(level, first_prize_amount, second_prize_amount, pool_high)
        rule = "new"
    else:
        level = _get_level_old(r_hits, b_hits)
        amount = _get_amount_old(level, first_prize_amount, second_prize_amount)
        rule = "old"

    if level == 0:
        desc = "未中奖"
    else:
        cn = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九"}
        desc = f"{cn.get(level, str(level))}等奖"

    return {
        "level": level,
        "amount": amount,
        "red_hits": r_hits,
        "blue_hits": b_hits,
        "desc": desc,
        "rule": rule,
    }


# ===== 新规则(7级) =====

def _get_level_new(r: int, b: int) -> int:
    """新规则7个奖级:
      一等奖: 5+2
      二等奖: 5+1
      三等奖: 5+0 / 4+2
      四等奖: 4+1
      五等奖: 4+0 / 3+2
      六等奖: 3+1 / 2+2
      七等奖: 3+0 / 2+1 / 1+2 / 0+2
      不中:   2+0 / 1+1 / 0+1 / 1+0 / 0+0
    """
    if r == 5 and b == 2:
        return 1
    if r == 5 and b == 1:
        return 2
    if (r == 5 and b == 0) or (r == 4 and b == 2):
        return 3
    if r == 4 and b == 1:
        return 4
    if (r == 4 and b == 0) or (r == 3 and b == 2):
        return 5
    if (r == 3 and b == 1) or (r == 2 and b == 2):
        return 6
    if (r == 3 and b == 0) or (r == 2 and b == 1) or (r == 1 and b == 2) or (r == 0 and b == 2):
        return 7
    return 0


def _get_amount_new(level: int, first_amount: str, second_amount: str, pool_high: bool) -> int:
    """新规则奖金金额。"""
    if level == 0:
        return 0
    if level in FIXED_PRIZES_NEW:
        key = "high" if pool_high else "low"
        return FIXED_PRIZES_NEW[level][key]
    # 浮动奖金: 优先用当期实际数据
    if level == 1:
        return _parse_amount(first_amount) or DEFAULT_FLOATING[1]
    if level == 2:
        return _parse_amount(second_amount) or DEFAULT_FLOATING[2]
    return 0


# ===== 旧规则(9级) =====

def _get_level_old(r: int, b: int) -> int:
    """旧规则9个奖级:
      一等奖: 5+2
      二等奖: 5+1
      三等奖: 5+0
      四等奖: 4+2
      五等奖: 4+1
      六等奖: 3+2
      七等奖: 4+0
      八等奖: 3+1 / 2+2
      九等奖: 3+0 / 2+1 / 1+2 / 0+2
      不中:   2+0 / 1+1 / 0+1 / 1+0 / 0+0
    """
    # 一等奖: 5+2
    if r == 5 and b == 2:
        return 1
    # 二等奖: 5+1
    if r == 5 and b == 1:
        return 2
    # 三等奖: 5+0
    if r == 5 and b == 0:
        return 3
    # 四等奖: 4+2
    if r == 4 and b == 2:
        return 4
    # 五等奖: 4+1
    if r == 4 and b == 1:
        return 5
    # 六等奖: 3+2
    if r == 3 and b == 2:
        return 6
    # 七等奖: 4+0
    if r == 4 and b == 0:
        return 7
    # 八等奖: 3+1 / 2+2
    if (r == 3 and b == 1) or (r == 2 and b == 2):
        return 8
    # 九等奖: 3+0 / 2+1 / 1+2 / 0+2
    if (r == 3 and b == 0) or (r == 2 and b == 1) or (r == 1 and b == 2) or (r == 0 and b == 2):
        return 9
    # 不中: 2+0 / 1+1 / 0+1 / 1+0 / 0+0
    return 0


def _get_amount_old(level: int, first_amount: str, second_amount: str) -> int:
    """旧规则奖金金额(无奖池上浮机制)。"""
    if level == 0:
        return 0
    if level in FIXED_PRIZES_OLD:
        return FIXED_PRIZES_OLD[level]
    # 浮动奖金: 优先用当期实际数据
    if level == 1:
        return _parse_amount(first_amount) or DEFAULT_FLOATING[1]
    if level == 2:
        return _parse_amount(second_amount) or DEFAULT_FLOATING[2]
    return 0


# ===== 通用工具 =====

def _is_high_pool(prize_pool: str) -> bool:
    """判断奖池是否≥8亿元(仅新规则使用)。"""
    amount = _parse_amount(prize_pool)
    if amount is None:
        return False
    return amount >= HIGH_POOL_THRESHOLD


def _parse_amount(s: str) -> int | None:
    """解析金额字符串(如 '10,000,000' 或 '8.02亿')为整数。"""
    if not s:
        return None
    cleaned = str(s).replace(",", "").replace(" ", "").strip()
    # 处理"亿"单位
    if "亿" in cleaned:
        try:
            return int(float(cleaned.replace("亿", "")) * 1_0000_0000)
        except (ValueError, TypeError):
            return None
    try:
        return int(float(cleaned))
    except (ValueError, TypeError):
        return None


def format_amount(amount: int) -> str:
    """格式化金额为中文表示。"""
    if amount >= 1_0000_0000:
        return f"{amount / 1_0000_0000:.2f}亿"
    if amount >= 1_0000:
        return f"{amount / 1_0000:.1f}万"
    return f"{amount}元"
