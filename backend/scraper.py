"""大乐透历史数据抓取器（数据源：500.com）。"""
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

import config
import models

logger = logging.getLogger(__name__)


class DltScraper:
    """超级大乐透历史开奖抓取。"""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _parse_date(date_str: str):
        date_str = (date_str or "").strip()
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

    def _fetch_table_rows(self, url: str):
        try:
            resp = requests.get(
                url, headers=config.SCRAPER_HEADERS, timeout=20
            )
            resp.raise_for_status()
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
            tbody = soup.find("tbody", id="tdata")
            if not tbody:
                return []
            return tbody.find_all("tr") or []
        except Exception as e:
            logger.error(f"抓取失败 {url}: {e}")
            return []

    def scrape(self, limit: int = 100, upsert: bool = False, want_issue: str | None = None) -> dict:
        """抓取大乐透历史数据。

        Args:
            limit: 抓取条数
            upsert: 是否更新已存在记录
            want_issue: 期望期号，抓到即停
        """
        want_issue = (want_issue or "").strip() or None
        seen: dict[str, dict] = {}

        for url_template in config.SCRAPER_URLS:
            url = url_template.format(limit=limit)
            rows = self._fetch_table_rows(url)
            if not rows:
                continue
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 15:
                    continue
                issue = cols[0].text.strip()
                if not issue:
                    continue
                # 大乐透：前区5个(col 1-5)，后区2个(col 6-7)
                reds = ",".join(cols[i].text.strip() for i in range(1, 6))
                blues = ",".join(cols[i].text.strip() for i in range(6, 8))
                # 奖池/中奖信息(col 8-13)，日期(col 14)
                prize_pool = cols[8].text.strip() if len(cols) > 8 else ""
                first_prize_count = cols[9].text.strip() if len(cols) > 9 else ""
                first_prize_amount = cols[10].text.strip() if len(cols) > 10 else ""
                second_prize_count = cols[11].text.strip() if len(cols) > 11 else ""
                second_prize_amount = cols[12].text.strip() if len(cols) > 12 else ""
                sales = cols[13].text.strip() if len(cols) > 13 else ""
                date = self._parse_date(cols[14].text.strip()) if len(cols) > 14 else None
                if date is None:
                    continue
                seen[issue] = {
                    "issue": issue,
                    "date": date,
                    "red_balls": reds,
                    "blue_balls": blues,
                    "prize_pool": prize_pool,
                    "first_prize_count": first_prize_count,
                    "first_prize_amount": first_prize_amount,
                    "second_prize_count": second_prize_count,
                    "second_prize_amount": second_prize_amount,
                    "sales": sales,
                }
            if want_issue and want_issue in seen:
                break

        added, updated = 0, 0
        prize_fields = [
            "prize_pool",
            "first_prize_count",
            "first_prize_amount",
            "second_prize_count",
            "second_prize_amount",
            "sales",
        ]
        for issue, payload in seen.items():
            existing = (
                self.db.query(models.LotteryRecord)
                .filter_by(lottery_type=config.LOTTERY_TYPE, issue=issue)
                .first()
            )
            if not existing:
                rec = models.LotteryRecord(
                    lottery_type=config.LOTTERY_TYPE,
                    issue=issue,
                    date=payload["date"],
                    red_balls=payload["red_balls"],
                    blue_balls=payload["blue_balls"],
                )
                for f in prize_fields:
                    setattr(rec, f, payload.get(f, ""))
                self.db.add(rec)
                added += 1
                continue
            if not upsert:
                continue
            changed = False
            if payload["date"] and existing.date != payload["date"]:
                existing.date = payload["date"]
                changed = True
            if (existing.red_balls or "").strip() != payload["red_balls"]:
                existing.red_balls = payload["red_balls"]
                changed = True
            if (existing.blue_balls or "").strip() != payload["blue_balls"]:
                existing.blue_balls = payload["blue_balls"]
                changed = True
            for f in prize_fields:
                if (getattr(existing, f) or "").strip() != (payload.get(f) or "").strip():
                    setattr(existing, f, payload.get(f, ""))
                    changed = True
            if changed:
                updated += 1

        if added or updated:
            self.db.commit()

        return {"added": added, "updated": updated, "seen": len(seen)}
