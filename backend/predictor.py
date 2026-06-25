"""预测器：LLM 预测 + 启发式加权随机兜底。"""
import json
import logging
import random
import re
import time
from urllib.parse import urlparse, urlunparse

import requests
from sqlalchemy.orm import Session

import analyzer
import config
import models

logger = logging.getLogger(__name__)


class Predictor:
    def __init__(self, db: Session):
        self.db = db

    # ---------- 公共入口 ----------

    def get_settings(self) -> dict:
        rows = self.db.query(models.AppSettings).all()
        return {r.key: r.value for r in rows}

    def predict(self, count: int = 1, history=None) -> dict:
        """生成预测。"""
        if history is None:
            history = (
                self.db.query(models.LotteryRecord)
                .filter_by(lottery_type=config.LOTTERY_TYPE)
                .order_by(models.LotteryRecord.issue.desc())
                .limit(100)
                .all()
            )
        if not history:
            return {"error": "暂无历史数据，请先抓取数据"}

        settings = self.get_settings()
        api_key = settings.get("llm_api_key") or ""
        base_url = settings.get("llm_base_url") or config.DEFAULT_LLM_BASE_URL
        model = settings.get("llm_model") or config.DEFAULT_LLM_MODEL

        if not api_key or not model:
            # 无 API Key 时走启发式
            return self._heuristic_predict(history, count)

        llm = self._call_llm(history, api_key, base_url, model, count)
        if not llm or "error" in llm:
            logger.warning(f"LLM 预测失败，降级启发式: {llm}")
            return self._heuristic_predict(history, count)

        validated = self._validate(llm.get("predictions", []), count)
        if len(validated) < count:
            logger.warning(f"LLM 有效预测不足({len(validated)}/{count})，降级启发式")
            return self._heuristic_predict(history, count)

        return {
            "analysis": llm.get("analysis", ""),
            "predictions": validated,
            "meta": llm.get("meta") or {"used_llm": True, "model": model},
        }

    # ---------- LLM 调用 ----------

    def _call_llm(self, history, api_key, base_url, model, count):
        cfg = {
            "red_max": config.RED_MAX,
            "red_pick": config.RED_PICK,
            "blue_max": config.BLUE_MAX,
            "blue_pick": config.BLUE_PICK,
        }
        data_lines = [
            f"期号:{h.issue}, 前区:{h.red_balls}, 后区:{h.blue_balls}"
            for h in reversed(history[:30])
        ]
        data_str = "\n".join(data_lines)

        # 频率统计（兼容原格式）
        freq_str = self._frequency_stats(history[:50])

        # 结构化分析数据（基于最近 50 期）
        analysis_str = self._structured_analysis(history[:50])

        prompt = f"""
你是中国超级大乐透(dlt)号码分析助手。请基于最近开奖数据和**结构化统计分析**，生成下一期候选号码组合，并给出可解释的选号理由。
要求：
1) 只返回 JSON（不要 markdown，不要多余文字）。
2) JSON 结构必须为：{{"analysis":"总体分析", "predictions":[...]}}。
3) "analysis" 字段：给出整体概率分析，包括冷热号判断、遗漏值、奇偶比、大小比、和值区间、AC值等统计观察（200字以内）。
4) "predictions" 必须恰好包含 {count} 组，且每组互不重复。
5) 每组必须包含：
   - "red_balls": {cfg["red_pick"]} 个不重复号码字符串，范围 "01"~"{cfg["red_max"]:02d}"，升序
   - "blue_balls": {cfg["blue_pick"]} 个不重复号码字符串，范围 "01"~"{cfg["blue_max"]:02d}"，升序
   - "reason": 该组号码的选择理由，必须引用下列结构化数据（如热号/冷号/遗漏值/奇偶比/和值区间等，50字以内）

最近 30 期开奖数据：
{data_str}

最近 50 期号码频率统计：
{freq_str}

最近 50 期结构化统计分析（请基于这些数据做选号决策）：
{analysis_str}
""".strip()

        t0 = time.monotonic()
        try:
            url = self._build_chat_url(base_url)
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": min(8192, 3000 + count * 200),
                "temperature": 0.2,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            last_exc = None
            for attempt in range(3):
                try:
                    r = requests.post(url, headers=headers, json=payload, timeout=(30, 600))
                    break
                except (requests.Timeout, requests.ConnectionError) as e:
                    last_exc = e
                    if attempt < 2:
                        time.sleep(2)
            else:
                raise last_exc or requests.Timeout("LLM 请求超时")

            if r.status_code < 200 or r.status_code >= 300:
                return {"error": f"LLM HTTP {r.status_code}", "raw": (r.text or "")[:500]}

            data = r.json() if r.content else {}
            content = (
                ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            ).strip()

            # 去除 markdown 代码块
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                else:
                    return {"error": "LLM 返回非 JSON", "raw": content}

            latency_ms = int((time.monotonic() - t0) * 1000)
            # 记录日志
            self._log_generation(history[0].issue if history else "", model, base_url, latency_ms, prompt, content)

            if isinstance(parsed, dict):
                parsed["meta"] = {
                    "used_llm": True,
                    "model": model,
                    "base_url": base_url,
                    "latency_ms": latency_ms,
                }
                return parsed
            return {"error": "LLM 返回格式无效", "raw": content}
        except Exception as e:
            logger.error(f"LLM 调用异常: {e}")
            return {"error": f"LLM 调用失败: {e}"}

    @staticmethod
    def _build_chat_url(base_url: str) -> str:
        base = (base_url or config.DEFAULT_LLM_BASE_URL).strip().rstrip("/")
        parsed = urlparse(base)
        path = (parsed.path or "").rstrip("/")
        if "/chat/completions" in path:
            return base
        segs = [s for s in path.split("/") if s]
        if segs and segs[-1] == "v1":
            new_path = path + "/chat/completions"
        elif "v1" in segs:
            new_path = path + "/chat/completions"
        else:
            new_path = path + "/v1/chat/completions"
        return urlunparse(parsed._replace(path=new_path))

    def _log_generation(self, based_on_issue, model, base_url, latency_ms, prompt, content):
        try:
            self.db.add(
                models.AiGenerationLog(
                    lottery_type=config.LOTTERY_TYPE,
                    based_on_issue=based_on_issue,
                    llm_model=model,
                    llm_base_url=base_url,
                    llm_latency_ms=latency_ms,
                    prompt=prompt,
                    raw_content=content,
                )
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"记录 AI 日志失败: {e}")

    # ---------- 校验 ----------

    def _validate(self, preds: list, count: int) -> list:
        cfg = {
            "red_max": config.RED_MAX,
            "red_pick": config.RED_PICK,
            "blue_max": config.BLUE_MAX,
            "blue_pick": config.BLUE_PICK,
        }
        seen = set()
        out = []
        for item in preds or []:
            if not isinstance(item, dict):
                continue
            reds = item.get("red_balls") or item.get("reds") or item.get("red")
            blues = item.get("blue_balls") or item.get("blues") or item.get("blue")
            if isinstance(reds, str):
                reds = [x.strip() for x in re.split(r"[,\s]+", reds) if x.strip()]
            if isinstance(blues, str):
                blues = [x.strip() for x in re.split(r"[,\s]+", blues) if x.strip()]
            if not isinstance(reds, list) or not isinstance(blues, list):
                continue

            reds_i, blues_i = [], []
            ok = True
            for x in reds:
                v = x if isinstance(x, int) else (int(x) if str(x).strip().isdigit() else None)
                if v is None or v < 1 or v > cfg["red_max"]:
                    ok = False
                    break
                reds_i.append(v)
            if not ok:
                continue
            for x in blues:
                v = x if isinstance(x, int) else (int(x) if str(x).strip().isdigit() else None)
                if v is None or v < 1 or v > cfg["blue_max"]:
                    ok = False
                    break
                blues_i.append(v)
            if not ok:
                continue
            if len(set(reds_i)) != cfg["red_pick"] or len(set(blues_i)) != cfg["blue_pick"]:
                continue

            reds_s = [f"{v:02d}" for v in sorted(reds_i)]
            blues_s = [f"{v:02d}" for v in sorted(blues_i)]
            key = (",".join(reds_s), ",".join(blues_s))
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "red_balls": reds_s,
                "blue_balls": blues_s,
                "reason": item.get("reason", ""),
            })
            if len(out) >= count:
                break
        return out

    # ---------- 频率统计 ----------

    def _frequency_stats(self, history) -> str:
        """生成频率统计文本，供 LLM 分析参考。"""
        cfg = {
            "red_max": config.RED_MAX,
            "blue_max": config.BLUE_MAX,
        }
        red_counts = {i: 0 for i in range(1, cfg["red_max"] + 1)}
        blue_counts = {i: 0 for i in range(1, cfg["blue_max"] + 1)}
        for h in history:
            for n in self._parse_nums(h.red_balls):
                if 1 <= n <= cfg["red_max"]:
                    red_counts[n] += 1
            for n in self._parse_nums(h.blue_balls):
                if 1 <= n <= cfg["blue_max"]:
                    blue_counts[n] += 1

        total = len(history) or 1
        # 前区热号(出现>=5次) 和 冷号(出现<=1次)
        red_hot = sorted(red_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        red_cold = sorted(
            [(i, red_counts[i]) for i in range(1, cfg["red_max"] + 1)],
            key=lambda x: x[1],
        )[:8]
        blue_hot = sorted(blue_counts.items(), key=lambda x: x[1], reverse=True)[:4]
        blue_cold = sorted(blue_counts.items(), key=lambda x: x[1])[:4]

        lines = [
            f"统计期数: {total}",
            "前区热号(出现最多): "
            + ", ".join(f"{n:02d}({c}次)" for n, c in red_hot),
            "前区冷号(出现最少): "
            + ", ".join(f"{n:02d}({c}次)" for n, c in red_cold),
            "后区热号: " + ", ".join(f"{n:02d}({c}次)" for n, c in blue_hot),
            "后区冷号: " + ", ".join(f"{n:02d}({c}次)" for n, c in blue_cold),
        ]
        return "\n".join(lines)

    def _structured_analysis(self, history) -> str:
        """生成结构化分析数据（遗漏值/和值/奇偶/大小/跨度），供 LLM 决策参考。

        注意：history 是按 issue desc 排序（新→旧），analyzer 期望升序（旧→新），需反转。
        """
        if not history:
            return "暂无数据"

        # 反转为升序（旧→新）
        records_asc = list(reversed(history))

        lines = []

        # 1. 遗漏值排行（前区 Top5 + 后区 Top3）
        try:
            red_miss = analyzer.miss_values(records_asc, "red")
            blue_miss = analyzer.miss_values(records_asc, "blue")
            red_sorted = sorted(red_miss.items(), key=lambda x: x[1], reverse=True)[:5]
            blue_sorted = sorted(blue_miss.items(), key=lambda x: x[1], reverse=True)[:3]
            lines.append("【遗漏值排行】(距上次出现已隔几期)")
            lines.append("前区遗漏最久: " + ", ".join(f"{n}({m}期)" for n, m in red_sorted))
            lines.append("后区遗漏最久: " + ", ".join(f"{n}({m}期)" for n, m in blue_sorted))
        except Exception as e:
            logger.warning(f"遗漏值计算失败: {e}")

        # 2. 和值分布
        try:
            sum_dist = analyzer.sum_distribution(records_asc)
            lines.append(
                f"【和值分布】平均{sum_dist['avg']}, 范围{sum_dist['min']}-{sum_dist['max']}"
            )
            bucket_str = "; ".join(
                f"{b['range']}({b['count']}期,{b['rate']*100:.0f}%)"
                for b in sum_dist["buckets"]
            )
            lines.append(f"分桶: {bucket_str}")
        except Exception as e:
            logger.warning(f"和值分布计算失败: {e}")

        # 3. 奇偶比分布
        try:
            oe_dist = analyzer.ratio_distribution(records_asc, "odd_even")
            oe_sorted = sorted(oe_dist.items(), key=lambda x: x[1], reverse=True)
            total = sum(oe_dist.values()) or 1
            oe_str = ", ".join(f"{r}({c}次,{c/total*100:.0f}%)" for r, c in oe_sorted)
            lines.append(f"【奇偶比历史分布】{oe_str}")
        except Exception as e:
            logger.warning(f"奇偶比计算失败: {e}")

        # 4. 大小比分布
        try:
            bs_dist = analyzer.ratio_distribution(records_asc, "big_small")
            bs_sorted = sorted(bs_dist.items(), key=lambda x: x[1], reverse=True)
            total = sum(bs_dist.values()) or 1
            bs_str = ", ".join(f"{r}({c}次,{c/total*100:.0f}%)" for r, c in bs_sorted)
            lines.append(f"【大小比历史分布】(大≥18:小≤17) {bs_str}")
        except Exception as e:
            logger.warning(f"大小比计算失败: {e}")

        # 5. 跨度分布
        try:
            span_dist = analyzer.span_distribution(records_asc)
            lines.append(
                f"【跨度分布】平均{span_dist['avg']}, 范围{span_dist['min']}-{span_dist['max']}"
            )
        except Exception as e:
            logger.warning(f"跨度分布计算失败: {e}")

        # 6. 上期开奖形态（参考重号）
        try:
            if len(records_asc) >= 2:
                latest = records_asc[-1]
                prev = records_asc[-2]
                latest_stats = analyzer.combo_stats(
                    latest.red_balls.split(","),
                    latest.blue_balls.split(","),
                    prev.red_balls.split(","),
                )
                lines.append(
                    f"【上期开奖形态】和值{latest_stats['sum']}, 奇偶{latest_stats['odd_even']}, "
                    f"大小{latest_stats['big_small']}, 跨度{latest_stats['span']}, "
                    f"重号{latest_stats['repeat_count']}个"
                )
        except Exception as e:
            logger.warning(f"上期形态计算失败: {e}")

        return "\n".join(lines)

    # ---------- 启发式兜底 ----------

    def _heuristic_predict(self, history, count: int) -> dict:
        cfg = {
            "red_max": config.RED_MAX,
            "red_pick": config.RED_PICK,
            "blue_max": config.BLUE_MAX,
            "blue_pick": config.BLUE_PICK,
        }
        red_hist, blue_hist = self._weights_from_history(cfg, history)
        red_boost, blue_boost = self._weights_from_evaluations(cfg)

        red_w = {i: 1.0 + red_hist[i] * 0.35 + red_boost[i] * 0.15 for i in red_hist}
        blue_w = {i: 1.0 + blue_hist[i] * 0.45 + blue_boost[i] * 0.20 for i in blue_hist}

        seen = set()
        out = []
        tries = 0
        while len(out) < count and tries < count * 50:
            tries += 1
            reds = self._sample(list(range(1, cfg["red_max"] + 1)), red_w, cfg["red_pick"])
            blues = self._sample(list(range(1, cfg["blue_max"] + 1)), blue_w, cfg["blue_pick"])
            reds_s = [f"{v:02d}" for v in sorted(reds)]
            blues_s = [f"{v:02d}" for v in sorted(blues)]
            key = (",".join(reds_s), ",".join(blues_s))
            if key in seen:
                continue
            seen.add(key)
            # 生成选择理由
            hot_reds = [n for n in reds if red_hist[n] >= 3]
            cold_reds = [n for n in reds if red_hist[n] <= 1]
            reason_parts = []
            if hot_reds:
                reason_parts.append(f"前区热号{','.join(f'{n:02d}' for n in hot_reds)}")
            if cold_reds:
                reason_parts.append(f"冷号{','.join(f'{n:02d}' for n in cold_reds)}")
            odd_count = sum(1 for n in reds if n % 2 == 1)
            reason_parts.append(f"奇偶{odd_count}:{cfg['red_pick']-odd_count}")
            reason = "，".join(reason_parts) if reason_parts else "加权随机抽样"
            out.append({"red_balls": reds_s, "blue_balls": blues_s, "reason": reason})

        return {
            "analysis": "基于历史频率与命中表现的加权随机生成（未使用 LLM）。",
            "predictions": out,
            "meta": {"used_llm": False, "model": "heuristic"},
        }

    def _weights_from_history(self, cfg, history):
        red_counts = {i: 0 for i in range(1, cfg["red_max"] + 1)}
        blue_counts = {i: 0 for i in range(1, cfg["blue_max"] + 1)}
        for h in history:
            for n in self._parse_nums(h.red_balls):
                if 1 <= n <= cfg["red_max"]:
                    red_counts[n] += 1
            for n in self._parse_nums(h.blue_balls):
                if 1 <= n <= cfg["blue_max"]:
                    blue_counts[n] += 1
        return red_counts, blue_counts

    def _weights_from_evaluations(self, cfg, limit=200):
        red_boost = {i: 0.0 for i in range(1, cfg["red_max"] + 1)}
        blue_boost = {i: 0.0 for i in range(1, cfg["blue_max"] + 1)}
        rows = (
            self.db.query(models.PredictionRecord)
            .filter_by(lottery_type=config.LOTTERY_TYPE, evaluated=True)
            .order_by(models.PredictionRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        for r in rows:
            if r.total_hits is None:
                continue
            act_red = set(self._parse_nums(r.actual_red_balls))
            act_blue = set(self._parse_nums(r.actual_blue_balls))
            for n in self._parse_nums(r.red_balls):
                if n in act_red:
                    red_boost[n] += 1.0 + r.total_hits / 10.0
            for n in self._parse_nums(r.blue_balls):
                if n in act_blue:
                    blue_boost[n] += 1.0 + r.total_hits / 10.0
        return red_boost, blue_boost

    @staticmethod
    def _sample(items, weights, k):
        pool = list(items)
        picked = []
        for _ in range(min(k, len(pool))):
            total = sum(max(0.0, float(weights.get(n, 0.0))) for n in pool)
            if total <= 0:
                choice = random.choice(pool)
            else:
                r = random.random() * total
                acc = 0.0
                choice = pool[-1]
                for n in pool:
                    acc += max(0.0, float(weights.get(n, 0.0)))
                    if acc >= r:
                        choice = n
                        break
            pool.remove(choice)
            picked.append(choice)
        return picked

    @staticmethod
    def _parse_nums(s) -> list[int]:
        if not s:
            return []
        out = []
        for x in str(s).split(","):
            x = x.strip()
            if x and x.isdigit():
                out.append(int(x))
        return out
