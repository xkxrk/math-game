"""大乐透号码特征分析引擎。

提供 9 项核心分析指标：
  - 遗漏值: 每个号码距上次出现已隔几期
  - 和值: 5 个前区号码之和
  - 奇偶比: 奇数:偶数
  - 大小比: 大号(≥18):小号(≤17)
  - 跨度: 最大号 - 最小号
  - 区间分布: 1-12 / 13-23 / 24-35 三区号码数
  - 连号: 相邻号码对数
  - 重号: 与上期重复的号码数
  - AC 值: 号码间差值去重后的种类数

注：以上指标仅作为历史规律参考，不改变彩票本身的随机性。
"""

from collections import Counter
from typing import Optional

import config


# 区间划分（前区 1-35）
ZONE_BOUNDARIES = [(1, 12), (13, 23), (24, 35)]
# 大小分界（前区）
BIG_SMALL_THRESHOLD = 17  # ≤17 为小，≥18 为大


# ------------------------------------------------------------------ #
# 单组号码特征计算
# ------------------------------------------------------------------ #

def combo_stats(red_balls: list, blue_balls: list, prev_reds: Optional[list] = None) -> dict:
    """计算单组号码组合的形态特征。

    参数:
        red_balls: 前区 5 个号码（字符串或整数均可）
        blue_balls: 后区 2 个号码
        prev_reds: 上一期前区号码（可选，用于计算重号）

    返回:
        {
            "red_balls": [排序后的整数列表],
            "blue_balls": [排序后的整数列表],
            "sum": 和值,
            "odd_even": "3:2",  # 奇:偶
            "big_small": "2:3",  # 大:小
            "span": 跨度,
            "zones": [z1, z2, z3],  # 三区分布
            "consecutive": 连号对数,
            "repeat_count": 与上期重号数(无上期则 None),
            "ac_value": AC 值,
            "tail_groups": 同尾号组数,
        }
    """
    reds = sorted(int(x) for x in red_balls)
    blues = sorted(int(x) for x in blue_balls)

    # 和值
    sum_val = sum(reds)

    # 奇偶比
    odd_count = sum(1 for r in reds if r % 2 == 1)
    even_count = 5 - odd_count
    odd_even = f"{odd_count}:{even_count}"

    # 大小比
    big_count = sum(1 for r in reds if r >= BIG_SMALL_THRESHOLD + 1)
    small_count = 5 - big_count
    big_small = f"{big_count}:{small_count}"

    # 跨度
    span = reds[-1] - reds[0] if reds else 0

    # 区间分布
    zones = [sum(1 for r in reds if lo <= r <= hi) for lo, hi in ZONE_BOUNDARIES]

    # 连号
    consecutive = 0
    for i in range(len(reds) - 1):
        if reds[i + 1] - reds[i] == 1:
            consecutive += 1

    # 重号
    repeat_count = None
    if prev_reds is not None:
        prev_set = set(int(x) for x in prev_reds)
        repeat_count = sum(1 for r in reds if r in prev_set)

    # AC 值（号码间差值的去重种类数 - 4）
    diffs = set()
    for i in range(len(reds)):
        for j in range(i + 1, len(reds)):
            diffs.add(abs(reds[i] - reds[j]))
    ac_value = len(diffs) - (len(reds) - 1) if len(reds) > 1 else 0

    # 同尾号（个位相同的号码组数，>=2 才算一组）
    tails = Counter(r % 10 for r in reds)
    tail_groups = sum(1 for c in tails.values() if c >= 2)

    return {
        "red_balls": [str(r).zfill(2) for r in reds],
        "blue_balls": [str(b).zfill(2) for b in blues],
        "sum": sum_val,
        "odd_even": odd_even,
        "big_small": big_small,
        "span": span,
        "zones": zones,
        "consecutive": consecutive,
        "repeat_count": repeat_count,
        "ac_value": ac_value,
        "tail_groups": tail_groups,
    }


# ------------------------------------------------------------------ #
# 历史数据分析
# ------------------------------------------------------------------ #

def miss_values(records: list, num_type: str = "red") -> dict:
    """计算每个号码的遗漏值（距最近一次出现已隔几期）。

    参数:
        records: LotteryRecord 列表，按期号升序（旧→新）
        num_type: "red" 前区(1-35) / "blue" 后区(1-12)

    返回:
        { "01": 遗漏期数, "02": ..., ... }  当前未出现的号码遗漏值=总期数
    """
    if num_type == "red":
        pool = list(range(1, config.RED_MAX + 1))
        field = "red_balls"
    else:
        pool = list(range(1, config.BLUE_MAX + 1))
        field = "blue_balls"

    # records 升序，从最新期往前找
    miss = {}
    for num in pool:
        miss[str(num).zfill(2)] = 0
        found = False
        for rec in reversed(records):
            nums = [int(x) for x in getattr(rec, field).split(",")]
            if num in nums:
                found = True
                break
            miss[str(num).zfill(2)] += 1
        if not found:
            miss[str(num).zfill(2)] = len(records)
    return miss


def frequency_stats(records: list, num_type: str = "red", top: Optional[int] = None) -> list:
    """统计号码出现频率，返回排序后的列表。

    返回: [{"num": "01", "count": 18, "rate": 0.12}, ...]
    """
    if num_type == "red":
        pool = list(range(1, config.RED_MAX + 1))
        field = "red_balls"
    else:
        pool = list(range(1, config.BLUE_MAX + 1))
        field = "blue_balls"

    counter = Counter()
    for rec in records:
        nums = [int(x) for x in getattr(rec, field).split(",")]
        for n in nums:
            counter[n] += 1

    total = len(records) or 1
    result = []
    for num in pool:
        c = counter.get(num, 0)
        result.append({
            "num": str(num).zfill(2),
            "count": c,
            "rate": round(c / total, 4),
        })
    result.sort(key=lambda x: x["count"], reverse=True)
    if top:
        result = result[:top]
    return result


def sum_distribution(records: list) -> dict:
    """前区和值分布统计。

    返回:
        {
            "buckets": [{"range": "60-79", "count": 5, "rate": 0.05}, ...],
            "min": 60, "max": 180, "avg": 110.5,
            "recent": [120, 95, ...],  # 最近 N 期和值
        }
    """
    sums = []
    for rec in records:
        reds = [int(x) for x in rec.red_balls.split(",")]
        sums.append(sum(reds))

    if not sums:
        return {"buckets": [], "min": 0, "max": 0, "avg": 0, "recent": []}

    # 分桶: 60-79, 80-99, 100-119, 120-139, 140-159, 160+
    bucket_defs = [("60-79", 60, 79), ("80-99", 80, 99), ("100-119", 100, 119),
                   ("120-139", 120, 139), ("140-159", 140, 159), ("160+", 160, 9999)]
    buckets = []
    total = len(sums)
    for name, lo, hi in bucket_defs:
        c = sum(1 for s in sums if lo <= s <= hi)
        buckets.append({
            "range": name,
            "count": c,
            "rate": round(c / total, 4),
        })

    return {
        "buckets": buckets,
        "min": min(sums),
        "max": max(sums),
        "avg": round(sum(sums) / total, 2),
        "recent": sums[-30:][::-1],  # 最近 30 期，新→旧
    }


def ratio_distribution(records: list, ratio_type: str = "odd_even") -> dict:
    """奇偶比或大小比历史分布。

    参数:
        ratio_type: "odd_even" 奇偶比 / "big_small" 大小比

    返回: { "3:2": 45, "2:3": 38, ... }
    """
    counter = Counter()
    for rec in records:
        reds = sorted(int(x) for x in rec.red_balls.split(","))
        if ratio_type == "odd_even":
            a = sum(1 for r in reds if r % 2 == 1)
        else:  # big_small
            a = sum(1 for r in reds if r >= BIG_SMALL_THRESHOLD + 1)
        b = 5 - a
        counter[f"{a}:{b}"] += 1
    return dict(counter)


def span_distribution(records: list) -> dict:
    """跨度分布。返回 {跨度值: 次数}。"""
    counter = Counter()
    spans = []
    for rec in records:
        reds = sorted(int(x) for x in rec.red_balls.split(","))
        span = reds[-1] - reds[0]
        counter[span] += 1
        spans.append(span)
    return {
        "distribution": dict(counter),
        "min": min(spans) if spans else 0,
        "max": max(spans) if spans else 0,
        "avg": round(sum(spans) / len(spans), 2) if spans else 0,
    }


def pool_trend(records: list) -> list:
    """奖池金额趋势（按期号升序）。

    返回: [{"issue": "26070", "pool": 850000000}, ...]
    """
    trend = []
    for rec in records:
        amount = _parse_amount(rec.prize_pool)
        trend.append({
            "issue": rec.issue,
            "date": rec.date.isoformat() if rec.date else None,
            "pool": amount,  # 可能为 None
        })
    return trend


# ------------------------------------------------------------------ #
# 综合诊断
# ------------------------------------------------------------------ #

def diagnose_combo(
    red_balls: list,
    blue_balls: list,
    records: list,
    prev_reds: Optional[list] = None,
) -> dict:
    """号码组合诊断器：返回组合体检报告。

    参数:
        red_balls, blue_balls: 待诊断的号码
        records: 历史开奖记录列表（用于历史分位对比）
        prev_reds: 上一期前区号码（可选）

    返回:
        {
            "stats": {形态指标},
            "history_compare": {
                "sum_percentile": 65.0,  # 和值在历史中的分位
                "span_percentile": 50.0,
                "odd_even_rate": "3:2 出现 45 次 (22.5%)",
                "big_small_rate": "2:3 出现 38 次 (19.0%)",
                "similar_count": 3,  # 历史完全相同的组合出现次数
            },
            "miss_of_picks": {"01": 5, "12": 0, ...},  # 所选号码的遗漏值
            "score": 78,  # 综合评分 0-100
            "tips": ["和值偏高(分位 92%)", "奇偶比 5:0 历史罕见(0.5%)", ...]
        }
    """
    stats = combo_stats(red_balls, blue_balls, prev_reds)

    # 历史对比
    history_sums = []
    history_spans = []
    history_odd_even = Counter()
    history_big_small = Counter()
    picks_set = set(int(x) for x in red_balls)
    similar_count = 0

    for rec in records:
        reds = sorted(int(x) for x in rec.red_balls.split(","))
        history_sums.append(sum(reds))
        history_spans.append(reds[-1] - reds[0])
        oe_a = sum(1 for r in reds if r % 2 == 1)
        bs_a = sum(1 for r in reds if r >= BIG_SMALL_THRESHOLD + 1)
        history_odd_even[f"{oe_a}:{5 - oe_a}"] += 1
        history_big_small[f"{bs_a}:{5 - bs_a}"] += 1
        if set(reds) == picks_set:
            similar_count += 1

    total = len(records) or 1

    # 和值/跨度分位
    sum_pct = _percentile(history_sums, stats["sum"])
    span_pct = _percentile(history_spans, stats["span"])

    # 奇偶/大小比频率
    oe_count = history_odd_even.get(stats["odd_even"], 0)
    bs_count = history_big_small.get(stats["big_small"], 0)

    # 所选号码的遗漏值
    miss_of_picks = miss_values(records, "red")
    picks_miss = {num: miss_of_picks.get(num, 0) for num in stats["red_balls"]}

    # 评分与提示
    score, tips = _score_and_tips(
        stats, sum_pct, span_pct,
        oe_count / total, bs_count / total,
        similar_count, picks_miss,
    )

    return {
        "stats": stats,
        "history_compare": {
            "sum_percentile": round(sum_pct, 1),
            "span_percentile": round(span_pct, 1),
            "odd_even_rate": f"{stats['odd_even']} 出现 {oe_count} 次 ({oe_count / total * 100:.1f}%)",
            "big_small_rate": f"{stats['big_small']} 出现 {bs_count} 次 ({bs_count / total * 100:.1f}%)",
            "similar_count": similar_count,
        },
        "miss_of_picks": picks_miss,
        "score": score,
        "tips": tips,
    }


# ------------------------------------------------------------------ #
# 内部工具
# ------------------------------------------------------------------ #

def _percentile(data: list, value: float) -> float:
    """计算 value 在 data 中的分位（0-100）。"""
    if not data:
        return 50.0
    below = sum(1 for x in data if x < value)
    return below / len(data) * 100


def _score_and_tips(
    stats: dict,
    sum_pct: float,
    span_pct: float,
    oe_rate: float,
    bs_rate: float,
    similar_count: int,
    picks_miss: dict,
) -> tuple:
    """根据形态指标生成评分与提示。返回 (score 0-100, tips 列表)。"""
    score = 100
    tips = []

    # 和值分位（理想 30-70 分位）
    if sum_pct < 10 or sum_pct > 90:
        score -= 15
        tips.append(f"和值 {stats['sum']} 处于历史 {sum_pct:.0f}% 分位，{'偏低' if sum_pct < 50 else '偏高'}，较罕见")
    elif sum_pct < 20 or sum_pct > 80:
        score -= 5

    # 奇偶比（理想 2:3/3:2，至少 1:4 或 4:1 都罕见）
    if stats["odd_even"] in ("2:3", "3:2"):
        pass
    elif stats["odd_even"] in ("1:4", "4:1"):
        score -= 10
        tips.append(f"奇偶比 {stats['odd_even']} 历史占比 {oe_rate * 100:.1f}%，较罕见")
    elif stats["odd_even"] in ("0:5", "5:0"):
        score -= 25
        tips.append(f"奇偶比 {stats['odd_even']} 历史罕见({oe_rate * 100:.1f}%)，建议避免")

    # 大小比
    if stats["big_small"] in ("2:3", "3:2"):
        pass
    elif stats["big_small"] in ("1:4", "4:1"):
        score -= 10
        tips.append(f"大小比 {stats['big_small']} 历史占比 {bs_rate * 100:.1f}%，较罕见")
    elif stats["big_small"] in ("0:5", "5:0"):
        score -= 25
        tips.append(f"大小比 {stats['big_small']} 历史罕见({bs_rate * 100:.1f}%)，建议避免")

    # 跨度
    if span_pct < 10 or span_pct > 90:
        score -= 10
        tips.append(f"跨度 {stats['span']} 处于历史 {span_pct:.0f}% 分位，号码分布{'过聚簇' if span_pct < 50 else '过分散'}")

    # 连号（0-2 对常见）
    if stats["consecutive"] >= 3:
        score -= 10
        tips.append(f"连号 {stats['consecutive']} 对，历史较少见")

    # AC 值（理想 ≥4）
    if stats["ac_value"] < 4:
        score -= 10
        tips.append(f"AC 值 {stats['ac_value']} 偏低，号码间关联性过强")

    # 历史完全重复
    if similar_count > 0:
        score -= 5
        tips.append(f"该组合历史上出现过 {similar_count} 次")

    # 遗漏值提示
    high_miss = [(num, m) for num, m in picks_miss.items() if m >= 30]
    if high_miss:
        tips.append(f"所选号码中遗漏较久的: {', '.join(f'{n}({m}期)' for n, m in high_miss)}")

    score = max(0, min(100, score))
    if not tips:
        tips.append("形态指标整体正常，落在历史常见区间")
    return score, tips


def _parse_amount(s) -> Optional[int]:
    """解析金额字符串(如 '10,000,000' 或 '8.02亿')为整数。"""
    if not s:
        return None
    cleaned = str(s).replace(",", "").replace(" ", "").strip()
    if "亿" in cleaned:
        try:
            return int(float(cleaned.replace("亿", "")) * 1_0000_0000)
        except (ValueError, TypeError):
            return None
    try:
        return int(float(cleaned))
    except (ValueError, TypeError):
        return None


# ================================================================== #
# 新增功能：期望值 / 策略对比 / 沙盒模拟
# ================================================================== #

import math
import random

import prize
import config

# DLT 总组合数 = C(35,5) × C(12,2) = 324632 × 66 = 21,425,712
def _dlt_total_combinations() -> int:
    """大乐透总组合数：C(35,5) × C(12,2)。"""
    red_comb = math.comb(config.RED_MAX, config.RED_PICK)  # C(35,5)
    blue_comb = math.comb(config.BLUE_MAX, config.BLUE_PICK)  # C(12,2)
    return red_comb * blue_comb


def _query_records(db, lottery_type: str, limit: int = 100):
    """查询最近 limit 期记录（升序 旧→新）。"""
    import models

    rows = (
        db.query(models.LotteryRecord)
        .filter(models.LotteryRecord.lottery_type == lottery_type)
        .order_by(models.LotteryRecord.issue.asc())
        .limit(limit)
        .all()
    )
    return rows


def expected_value(db, lottery_type: str, limit: int = 100) -> dict:
    """奖金期望值计算器。

    返回：
        {
            "total_combinations": 总组合数,
            "current_pool": 当前奖池(元),
            "first_prize_ev": 一等奖单注期望值(元),
            "is_positive_ev": 期望值是否 > 2元成本,
            "pool_history_percentile": 当前奖池在历史中的分位,
            "pool_history_stats": {min/max/median/p25/p75},
            "recommendation": 推荐文字,
        }
    """
    records = _query_records(db, lottery_type, limit=limit)
    if not records:
        return {
            "total_combinations": _dlt_total_combinations(),
            "current_pool": 0,
            "first_prize_ev": 0.0,
            "is_positive_ev": False,
            "pool_history_percentile": 0.0,
            "pool_history_stats": {"min": 0, "max": 0, "median": 0, "p25": 0, "p75": 0},
            "recommendation": "无历史数据",
        }

    # 最新一期奖池
    latest = records[-1]
    current_pool = _parse_amount(latest.prize_pool) or 0

    total_comb = _dlt_total_combinations()
    # 一等奖期望值 = 当前奖池 / 总组合数
    first_prize_ev = round(current_pool / total_comb, 2) if total_comb else 0.0
    is_positive_ev = first_prize_ev > prize.BET_COST

    # 历史奖池分位统计
    history_pools = []
    for rec in records:
        amt = _parse_amount(rec.prize_pool)
        if amt is not None:
            history_pools.append(amt)

    if history_pools:
        sorted_pools = sorted(history_pools)
        n = len(sorted_pools)
        # 当前奖池分位
        below = sum(1 for p in sorted_pools if p < current_pool)
        percentile = round(below / n * 100, 1)
        pool_stats = {
            "min": sorted_pools[0],
            "max": sorted_pools[-1],
            "median": _percentile_value(sorted_pools, 50),
            "p25": _percentile_value(sorted_pools, 25),
            "p75": _percentile_value(sorted_pools, 75),
        }
    else:
        percentile = 0.0
        pool_stats = {"min": 0, "max": 0, "median": 0, "p25": 0, "p75": 0}

    # 推荐文字
    if current_pool >= prize.HIGH_POOL_THRESHOLD and is_positive_ev:
        recommendation = (
            f"当前奖池{current_pool / 1_0000_0000:.2f}亿，一等奖期望值{first_prize_ev}元，"
            f"远高于2元成本，可考虑加注"
        )
    elif is_positive_ev:
        recommendation = (
            f"当前奖池{current_pool / 1_0000_0000:.2f}亿，一等奖期望值{first_prize_ev}元，"
            f"高于2元成本，可适度投注"
        )
    else:
        recommendation = (
            f"当前奖池{current_pool / 1_0000_0000:.2f}亿，一等奖期望值{first_prize_ev}元，"
            f"低于2元成本，奖池偏低，建议谨慎"
        )

    return {
        "total_combinations": total_comb,
        "current_pool": current_pool,
        "first_prize_ev": first_prize_ev,
        "is_positive_ev": is_positive_ev,
        "pool_history_percentile": percentile,
        "pool_history_stats": pool_stats,
        "recommendation": recommendation,
    }


def _percentile_value(sorted_data: list, pct: float):
    """从已排序的列表中取得指定分位的值（线性插值）。"""
    if not sorted_data:
        return 0
    n = len(sorted_data)
    k = (pct / 100) * (n - 1)
    lo = int(k)
    hi = min(lo + 1, n - 1)
    frac = k - lo
    return int(round(sorted_data[lo] * (1 - frac) + sorted_data[hi] * frac))


def _hot_picks(records: list):
    """热号策略：最近 30 期出现频率最高的 5 个前区 + 2 个后区。"""
    recent = records[-30:] if len(records) >= 30 else records
    red_freq = frequency_stats(recent, "red")
    blue_freq = frequency_stats(recent, "blue")
    reds = [item["num"] for item in red_freq[:5]]
    blues = [item["num"] for item in blue_freq[:2]]
    return reds, blues


def _cold_picks(records: list):
    """冷号回补：当前遗漏值最大的 5 个前区 + 2 个后区。"""
    red_miss = miss_values(records, "red")
    blue_miss = miss_values(records, "blue")
    red_sorted = sorted(red_miss.items(), key=lambda x: x[1], reverse=True)
    blue_sorted = sorted(blue_miss.items(), key=lambda x: x[1], reverse=True)
    reds = [num for num, _ in red_sorted[:5]]
    blues = [num for num, _ in blue_sorted[:2]]
    return reds, blues


def _balanced_picks(records: list):
    """均衡策略：3 热 + 2 冷（前区），1 热 + 1 冷（后区）。"""
    hot_reds, hot_blues = _hot_picks(records)
    cold_reds, cold_blues = _cold_picks(records)
    # 前 3 热 + 后 2 冷（去重后取够 5 个）
    reds = list(hot_reds[:3])
    for num in cold_reds:
        if num not in reds:
            reds.append(num)
        if len(reds) >= 5:
            break
    blues = list(hot_blues[:1])
    for num in cold_blues:
        if num not in blues:
            blues.append(num)
        if len(blues) >= 2:
            break
    return reds, blues


def _random_picks(seed: int = 42):
    """随机策略：固定 seed 保证可复现。"""
    rng = random.Random(seed)
    reds = sorted(rng.sample(range(1, config.RED_MAX + 1), config.RED_PICK))
    blues = sorted(rng.sample(range(1, config.BLUE_MAX + 1), config.BLUE_PICK))
    reds_str = [str(r).zfill(2) for r in reds]
    blues_str = [str(b).zfill(2) for b in blues]
    return reds_str, blues_str


def strategy_compare(db, lottery_type: str, limit: int = 100) -> dict:
    """回测策略对比：4 种策略各在最近 limit 期上的命中率/ROI 对比。

    策略：
      1. 热号策略：选最近 30 期频率最高的号码
      2. 冷号回补：选当前遗漏值最大的号码
      3. 随机策略：固定 seed 随机生成
      4. 均衡策略：3 热 + 2 冷(前区)，1 热 + 1 冷(后区)
    """
    records = _query_records(db, lottery_type, limit=limit)
    if not records:
        return {"strategies": [], "periods": 0}

    # 4 种策略选出的固定号码
    strategies_def = [
        {"name": "热号策略", "reds_fn": lambda: _hot_picks(records)},
        {"name": "冷号回补", "reds_fn": lambda: _cold_picks(records)},
        {"name": "随机策略", "reds_fn": lambda: _random_picks(42)},
        {"name": "均衡策略", "reds_fn": lambda: _balanced_picks(records)},
    ]

    result_strategies = []
    for strat in strategies_def:
        reds, blues = strat["reds_fn"]()

        total_cost = 0
        total_winnings = 0
        win_count = 0
        level_stats = {}
        cumulative_roi = []  # 累计 ROI 曲线

        for rec in records:
            total_cost += prize.BET_COST
            actual_reds = rec.red_balls.split(",")
            actual_blues = rec.blue_balls.split(",")
            p = prize.calc_prize(
                reds,
                blues,
                actual_reds,
                actual_blues,
                rec.first_prize_amount or "",
                rec.second_prize_amount or "",
                rec.prize_pool or "",
                issue=rec.issue,
            )
            total_winnings += p["amount"]
            if p["level"] > 0:
                win_count += 1
                level_stats[p["desc"]] = level_stats.get(p["desc"], 0) + 1
            # 累计 ROI
            cum_roi = ((total_winnings - total_cost) / total_cost * 100) if total_cost else 0
            cumulative_roi.append(round(cum_roi, 2))

        net_profit = total_winnings - total_cost
        roi = ((total_winnings - total_cost) / total_cost * 100) if total_cost else 0
        win_rate = (win_count / len(records) * 100) if records else 0

        result_strategies.append({
            "name": strat["name"],
            "red_balls": reds,
            "blue_balls": blues,
            "total_cost": total_cost,
            "total_winnings": total_winnings,
            "net_profit": net_profit,
            "win_count": win_count,
            "win_rate": round(win_rate, 2),
            "roi": round(roi, 2),
            "level_stats": level_stats,
            "cumulative_roi": cumulative_roi,
        })

    return {
        "strategies": result_strategies,
        "periods": len(records),
    }


def sandbox_simulate(db, lottery_type: str, rules: dict, limit: int = 100) -> dict:
    """自定义策略沙盒：按规则生成 combo_count 注号码，对每注在最近 limit 期模拟购买。

    rules 参数：
        {
            "sum_min": 80, "sum_max": 130,
            "odd_even": ["2:3", "3:2"],
            "big_small": ["2:3", "3:2"],
            "span_min": 15, "span_max": 30,
            "consecutive": false,
            "combo_count": 5,
        }
    """
    records = _query_records(db, lottery_type, limit=limit)

    sum_min = rules.get("sum_min", 0)
    sum_max = rules.get("sum_max", 999)
    odd_even_set = rules.get("odd_even") or ["5:0", "4:1", "3:2", "2:3", "1:4", "0:5"]
    big_small_set = rules.get("big_small") or ["5:0", "4:1", "3:2", "2:3", "1:4", "0:5"]
    span_min = rules.get("span_min", 0)
    span_max = rules.get("span_max", 999)
    allow_consecutive = rules.get("consecutive", True)
    combo_count = rules.get("combo_count", 5)

    def _passes_rules(reds_int: list, blues_int: list) -> bool:
        stats = combo_stats(reds_int, blues_int)
        if not (sum_min <= stats["sum"] <= sum_max):
            return False
        if stats["odd_even"] not in odd_even_set:
            return False
        if stats["big_small"] not in big_small_set:
            return False
        if not (span_min <= stats["span"] <= span_max):
            return False
        if not allow_consecutive and stats["consecutive"] > 0:
            return False
        return True

    # 生成合格号码（尝试 combo_count × 20 次）
    generated = []
    attempts = 0
    max_attempts = combo_count * 50
    rng = random.Random(123)
    while len(generated) < combo_count and attempts < max_attempts:
        attempts += 1
        reds_int = sorted(rng.sample(range(1, config.RED_MAX + 1), config.RED_PICK))
        blues_int = sorted(rng.sample(range(1, config.BLUE_MAX + 1), config.BLUE_PICK))
        if not _passes_rules(reds_int, blues_int):
            continue
        # 去重（同一组号码不重复加入）
        key = (tuple(reds_int), tuple(blues_int))
        if any(g["_key"] == key for g in generated):
            continue
        stats = combo_stats(reds_int, blues_int)
        generated.append({
            "_key": key,
            "red_balls": [str(r).zfill(2) for r in reds_int],
            "blue_balls": [str(b).zfill(2) for b in blues_int],
            "stats": stats,
        })

    # 在最近 limit 期上模拟购买每注
    total_cost = 0
    total_winnings = 0
    win_count = 0
    level_stats = {}

    if records and generated:
        for rec in records:
            for combo in generated:
                total_cost += prize.BET_COST
                actual_reds = rec.red_balls.split(",")
                actual_blues = rec.blue_balls.split(",")
                p = prize.calc_prize(
                    combo["red_balls"],
                    combo["blue_balls"],
                    actual_reds,
                    actual_blues,
                    rec.first_prize_amount or "",
                    rec.second_prize_amount or "",
                    rec.prize_pool or "",
                    issue=rec.issue,
                )
                total_winnings += p["amount"]
                if p["level"] > 0:
                    win_count += 1
                    level_stats[p["desc"]] = level_stats.get(p["desc"], 0) + 1

    net_profit = total_winnings - total_cost
    roi = ((total_winnings - total_cost) / total_cost * 100) if total_cost else 0
    # 中奖率 = 中奖次数 / 总投注次数
    total_bets = len(records) * len(generated) if records and generated else 0
    win_rate = (win_count / total_bets * 100) if total_bets else 0

    # 清理内部字段
    cleaned_combos = [
        {"red_balls": g["red_balls"], "blue_balls": g["blue_balls"], "stats": g["stats"]}
        for g in generated
    ]

    return {
        "rules": rules,
        "generated_combos": cleaned_combos,
        "simulation": {
            "total_cost": total_cost,
            "total_winnings": total_winnings,
            "net_profit": net_profit,
            "win_rate": round(win_rate, 2),
            "roi": round(roi, 2),
            "level_stats": level_stats,
            "total_bets": total_bets,
        },
    }


# 历史复盘工具：形态对比 + 综合评分
def review_score(actual_record, your_reds: list, your_blues: list) -> dict:
    """历史复盘：将用户号码与实际开奖对比，返回命中/形态对比/综合评分。

    参数:
        actual_record: LotteryRecord 单条记录
        your_reds, your_blues: 用户选择的号码

    返回:
        {
            "actual_red_balls": [...], "actual_blue_balls": [...],
            "red_hits": int, "blue_hits": int, "level": int, "amount": int, "desc": str,
            "your_stats": {...}, "actual_stats": {...},
            "score": int,  # 0-100
        }
    """
    actual_reds = actual_record.red_balls.split(",")
    actual_blues = actual_record.blue_balls.split(",")

    # 计算奖金等级
    p = prize.calc_prize(
        your_reds, your_blues, actual_reds, actual_blues,
        actual_record.first_prize_amount or "",
        actual_record.second_prize_amount or "",
        actual_record.prize_pool or "",
        issue=actual_record.issue,
    )

    # 形态统计
    your_stats = combo_stats(your_reds, your_blues)
    actual_stats = combo_stats(actual_reds, actual_blues)

    # 综合评分：命中数 * 20 + 形态接近度 * 40
    hit_score = (p["red_hits"] + p["blue_hits"]) * 20

    # 形态接近度（4 项各 10 分）
    form_score = 0
    if your_stats["odd_even"] == actual_stats["odd_even"]:
        form_score += 10
    if your_stats["big_small"] == actual_stats["big_small"]:
        form_score += 10
    # 和值接近度（差值越小得分越高）
    sum_diff = abs(your_stats["sum"] - actual_stats["sum"])
    form_score += max(0, 10 - sum_diff // 5)
    # 跨度接近度
    span_diff = abs(your_stats["span"] - actual_stats["span"])
    form_score += max(0, 10 - span_diff // 3)

    score = min(100, hit_score + form_score)

    return {
        "actual_red_balls": actual_reds,
        "actual_blue_balls": actual_blues,
        "red_hits": p["red_hits"],
        "blue_hits": p["blue_hits"],
        "level": p["level"],
        "amount": p["amount"],
        "desc": p["desc"],
        "your_stats": your_stats,
        "actual_stats": actual_stats,
        "score": score,
    }
