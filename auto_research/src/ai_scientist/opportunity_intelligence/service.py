from __future__ import annotations

import hashlib
import html as html_module
import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import Engine, select

from . import models
from .repository import OpportunityRepository, new_id


@dataclass(frozen=True)
class OfficialOpportunitySource:
    venue_name: str
    venue_year: int
    opportunity_type: str
    title: str
    official_url: str
    source_priority: int = 100
    parent_event: str | None = None
    track_name: str | None = None


OFFICIAL_SOURCES = (
    OfficialOpportunitySource("ICLR", 2027, "MAIN_CONFERENCE_CFP", "ICLR 2027 Call for Papers", "https://iclr.cc/Conferences/2027/CallForPapers"),
    OfficialOpportunitySource("NeurIPS", 2026, "MAIN_CONFERENCE_CFP", "NeurIPS 2026 Call for Papers", "https://neurips.cc/Conferences/2026/CallForPapers"),
    OfficialOpportunitySource("NeurIPS", 2026, "DATASET_BENCHMARK_TRACK", "NeurIPS 2026 Evaluations & Datasets", "https://neurips.cc/Conferences/2026/CallForEvaluationsDatasets", track_name="Evaluations & Datasets"),
    OfficialOpportunitySource("NeurIPS", 2026, "POSITION_PAPER_CALL", "NeurIPS 2026 Position Papers", "https://neurips.cc/Conferences/2026/CallForPositionPapers", track_name="Position Papers"),
    OfficialOpportunitySource("NeurIPS", 2026, "COMPETITION", "NeurIPS 2026 Competitions", "https://neurips.cc/Conferences/2026/CallForCompetitions", track_name="Competitions"),
    OfficialOpportunitySource("ICML", 2026, "MAIN_CONFERENCE_CFP", "ICML 2026 Call for Papers", "https://icml.cc/Conferences/2026/CallForPapers"),
    OfficialOpportunitySource("AISTATS", 2026, "MAIN_CONFERENCE_CFP", "AISTATS 2026 Call for Papers", "https://virtual.aistats.org/Conferences/2026/CallForPapers"),
    OfficialOpportunitySource("AAAI", 2027, "MAIN_CONFERENCE_CFP", "AAAI-27 Call for Papers", "https://aaai.org/conference/aaai/aaai-27/"),
    OfficialOpportunitySource("CVPR", 2026, "MAIN_CONFERENCE_CFP", "CVPR 2026 Call for Papers", "https://cvpr.thecvf.com/Conferences/2026/CallForPapers"),
    OfficialOpportunitySource("ICCV", 2027, "MAIN_CONFERENCE_CFP", "ICCV 2027 Call for Papers", "https://iccv.thecvf.com/Conferences/2027/CallForPapers"),
    OfficialOpportunitySource("ECCV", 2026, "MAIN_CONFERENCE_CFP", "ECCV 2026 Call for Papers", "https://eccv.ecva.net/Conferences/2026/CallForPapers"),
    OfficialOpportunitySource("ACL", 2026, "MAIN_CONFERENCE_CFP", "ACL 2026 Call for Papers", "https://2026.aclweb.org/calls/main_conference_papers/"),
    OfficialOpportunitySource("EMNLP", 2026, "MAIN_CONFERENCE_CFP", "EMNLP 2026 Call for Papers", "https://2026.emnlp.org/calls/main_conference_papers/"),
    OfficialOpportunitySource("CoRL", 2026, "MAIN_CONFERENCE_CFP", "CoRL 2026 Call for Papers", "https://www.corl.org/call-for-papers"),
    OfficialOpportunitySource("RSS", 2027, "MAIN_CONFERENCE_CFP", "RSS 2027 Call for Papers", "https://roboticsconference.org/information/call-for-papers/"),
    OfficialOpportunitySource("ICRA", 2027, "MAIN_CONFERENCE_CFP", "ICRA 2027 Call for Papers", "https://2027.ieee-icra.org/announcements/call-for-technical-papers/"),
    OfficialOpportunitySource("IROS", 2026, "MAIN_CONFERENCE_CFP", "IROS 2026 Call for Papers", "https://2026.ieee-iros.org/"),
)

MONITORING_JOBS = {
    "daily_cfp_watch": {"cadence": "daily", "command": "ai-scientist opportunities sync"},
    "weekly_workshop_watch": {"cadence": "weekly", "command": "ai-scientist opportunities sync"},
    "weekly_recent_paper_watch": {"cadence": "weekly", "command": "ai-scientist literature sync-production"},
    "monthly_topic_trend_refresh": {"cadence": "monthly", "command": "ai-scientist opportunities sync"},
}


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._link_parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if self._ignored_depth:
            self._ignored_depth += 1
            return
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth = 1
            return
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._link_parts = []

    def handle_data(self, data):
        if self._ignored_depth:
            return
        value = " ".join(data.split())
        if value:
            self.parts.append(value)
            if self._href:
                self._link_parts.append(value)

    def handle_endtag(self, tag):
        if self._ignored_depth:
            self._ignored_depth -= 1
            return
        if tag == "a" and self._href:
            self.links.append((self._href, " ".join(self._link_parts)))
            self._href = None


MONTHS = {name.lower(): number for number, name in enumerate(
    ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"), 1
)}
MONTHS.update({name[:3].lower(): number for name, number in list(MONTHS.items())})
DATE_PATTERN = re.compile(
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+"
    r"(?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<year>20\d{2})"
    r"(?:\s+(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<ampm>AM|PM)?)?\s*(?P<zone>UTC-12|AOE|UTC|PST|PDT|EST|EDT|CET|CEST|[A-Za-z_]+/[A-Za-z_]+)?",
    re.IGNORECASE,
)


def normalize_deadline(raw: str) -> datetime:
    match = DATE_PATTERN.search(raw)
    if not match:
        raise ValueError(f"unrecognized deadline: {raw}")
    hour = int(match.group("hour") or 23)
    minute = int(match.group("minute") or 59)
    second = 0 if match.group("hour") else 59
    if match.group("ampm"):
        hour %= 12
        if match.group("ampm").upper() == "PM":
            hour += 12
    zone_name = (match.group("zone") or "UTC").upper()
    fixed_offsets = {"AOE": -12, "UTC-12": -12, "PST": -8, "PDT": -7, "EST": -5, "EDT": -4, "CET": 1, "CEST": 2}
    zone = timezone(timedelta(hours=fixed_offsets[zone_name])) if zone_name in fixed_offsets else ZoneInfo("UTC" if zone_name == "UTC" else match.group("zone"))
    month_key = match.group("month").lower()
    return datetime(int(match.group("year")), MONTHS.get(month_key, MONTHS[month_key[:3]]), int(match.group("day")), hour, minute, second, tzinfo=zone).astimezone(timezone.utc)


def initialize_opportunity_database(engine: Engine) -> None:
    from ai_scientist.research_store.models import metadata
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS research")
    metadata.create_all(engine, tables=list(models.TABLES.values()))


def _default_fetch(url: str) -> str:
    response = httpx.get(url, timeout=30, follow_redirects=True, headers={"User-Agent": "ai-scientist-opportunity-intelligence/2"})
    response.raise_for_status()
    return response.text


class OpportunityService:
    def __init__(self, repository: OpportunityRepository, *, static_fetch: Callable[[str], str] | None = None, browser_fetch: Callable[[str], str] | None = None):
        self.repository = repository
        self.static_fetch = static_fetch or _default_fetch
        self.browser_fetch = browser_fetch

    def _fetch(self, url: str) -> tuple[str, str]:
        try:
            return self.static_fetch(url), "HTTP"
        except Exception as first_error:
            if self.browser_fetch:
                try:
                    return self.browser_fetch(url), "PLAYWRIGHT"
                except Exception:
                    pass
            raise first_error

    @staticmethod
    def _parse(html: str) -> tuple[str, list[tuple[str, str]]]:
        parser = _TextParser()
        parser.feed(html)
        return html_module.unescape("\n".join(parser.parts)), parser.links

    @staticmethod
    def _deadline(text: str) -> tuple[str | None, datetime | None, str | None]:
        positives = {
            "full paper submission deadline": 160, "full papers due": 160,
            "contributed paper submission deadline": 150, "deadline for paper submissions": 150,
            "electronic paper submissions due": 145, "paper submission deadline": 140,
            "paper deadline": 135, "paper submissions due": 130, "submission deadline": 120,
        }
        exclusions = (
            "acceptance notification", "author notification", "notification of final", "final decisions",
            "submission site opens", "submission site open", "site opens", "site open", "paper video", "supplementary", "camera ready",
            "abstract deadline", "abstract submission deadline", "abstracts due", "registration",
            "reviews released", "rebuttal", "accompanying videos",
        )
        def segment_score(segment: str, *, before: bool) -> tuple[float, int] | None:
            value = segment.lower()
            matches = []
            for label, weight in positives.items():
                for found in re.finditer(re.escape(label), value):
                    distance = len(value) - found.end() if before else found.start()
                    matches.append((weight - distance / 10, distance))
            return max(matches) if matches else None

        search_text = re.sub(r"\s+", " ", text)
        matches = list(DATE_PATTERN.finditer(search_text))
        candidates: list[tuple[float, str]] = []
        lines = [line.strip() for line in text.splitlines() if line.strip() and any(char.isalnum() for char in line)]
        event_words = ("deadline", "due", "released", "rebuttal", "decision", "notification", "period")
        for date_start, line in enumerate(lines):
            if not DATE_PATTERN.search(line):
                continue
            label_start = date_start
            while label_start and any(word in lines[label_start - 1].lower() for word in event_words) and not DATE_PATTERN.search(lines[label_start - 1]):
                label_start -= 1
            labels = lines[label_start:date_start]
            date_rows = []
            for date_line in lines[date_start:]:
                date_match = DATE_PATTERN.search(date_line)
                if not date_match:
                    break
                date_rows.append(date_match.group(0).strip())
            if len(labels) < 2:
                continue
            for label_index, label in enumerate(labels):
                lower = label.lower()
                target = "paper submission deadline" in lower or "full papers due" in lower or (
                    "submission deadline" in lower and not any(word in lower for word in ("abstract", "supplement", "registration", "video"))
                )
                if target and label_index < len(date_rows):
                    candidates.append((1000, date_rows[label_index]))
                    break
            if candidates:
                break
        for index, match in enumerate(matches):
            previous_end = matches[index - 1].end() if index else max(0, match.start() - 180)
            next_start = matches[index + 1].start() if index + 1 < len(matches) else min(len(text), match.end() + 180)
            before_segment = search_text[previous_end:match.start()][-180:]
            after_segment = search_text[match.end():next_start][:180]
            before_score = segment_score(before_segment, before=True)
            after_score = segment_score(after_segment, before=False)
            before_excluded = any(label in before_segment.lower() for label in exclusions)
            after_excluded = any(label in after_segment.lower() for label in exclusions)
            if "paper video" in after_segment.lower():
                continue
            if after_score and not (index == 0 and before_excluded):
                score, _ = after_score
            elif before_score:
                score, _ = before_score
                score += 0.5
            elif before_excluded or after_excluded:
                continue
            else:
                start = max(0, match.start() - 180)
                context = search_text[start:min(len(search_text), match.end() + 180)].lower()
                date_position = match.start() - start
                broad = []
                for label, weight in positives.items():
                    for found in re.finditer(re.escape(label), context):
                        distance = min(abs(found.start() - date_position), abs(found.end() - date_position))
                        broad.append((weight - distance / 10, distance))
                if not broad:
                    continue
                score, _ = max(broad)
            local_context = search_text[max(0, match.start() - 180):min(len(search_text), match.end() + 260)].lower()
            if "accompanying videos" in local_context and score < 145:
                continue
            raw = match.group(0).strip()
            suffix = search_text[match.end():min(len(search_text), match.end() + 140)]
            time_zone = re.search(r"(?P<time>(?:\d{1,2}:\d{2}\s*(?:AM|PM)?|\d{1,2}\s*(?:AM|PM)))\s*(?P<zone>UTC-12|AOE|UTC|PST|PDT|EST|EDT|CET|CEST)\b", suffix, re.I)
            if not match.group("hour") and time_zone:
                raw = f"{raw} {time_zone.group('time').strip()} {time_zone.group('zone').upper()}"
            candidates.append((score, raw))
        if not candidates:
            return None, None, None
        raw = max(candidates, key=lambda item: item[0])[1]
        zone_match = re.search(r"(UTC-12|AOE|UTC|PST|PDT|EST|EDT|CET|CEST)\b", raw, re.I)
        zone = zone_match.group(1).upper() if zone_match else "UTC"
        if zone == "UTC-12":
            zone = "AOE"
        return raw, normalize_deadline(raw), zone

    @staticmethod
    def _status(deadline: datetime | None, now: datetime) -> str:
        if deadline is None:
            return "UNKNOWN"
        return "CLOSED" if deadline < now else ("OPEN" if deadline - now <= timedelta(days=180) else "UPCOMING")

    def sync_source(self, source: OfficialOpportunitySource, *, now: datetime | None = None) -> dict:
        checked_at = now or datetime.now(timezone.utc)
        try:
            raw_html, method = self._fetch(source.official_url)
        except Exception:
            existing = self.repository.get_opportunity_by_url(source.official_url)
            values = {
                "opportunity_type": source.opportunity_type, "title": source.title, "venue_name": source.venue_name,
                "venue_year": source.venue_year, "parent_event": source.parent_event, "track_name": source.track_name,
                "official_url": source.official_url, "cfp_text": existing["cfp_text"] if existing else "",
                "topic_text": existing["topic_text"] if existing else "", "submission_deadline_raw": existing["submission_deadline_raw"] if existing else None,
                "submission_deadline_utc": existing["submission_deadline_utc"] if existing else None, "timezone": existing["timezone"] if existing else None,
                "deadline_type": existing["deadline_type"] if existing else None, "status": "UNKNOWN", "source_priority": source.source_priority,
                "official_verified": bool(existing and existing["official_verified"]), "last_checked_at": checked_at,
                "content_hash": existing["content_hash"] if existing else None, "retrieval_method": "FAILED", "stale": True,
            }
            return self.repository.save_opportunity(values)
        text, links = self._parse(raw_html)
        deadline_raw, deadline, zone = self._deadline(text)
        content_hash = hashlib.sha256(raw_html.encode("utf-8")).hexdigest()
        values = {
            "opportunity_type": source.opportunity_type, "title": source.title, "venue_name": source.venue_name,
            "venue_year": source.venue_year, "parent_event": source.parent_event, "track_name": source.track_name,
            "official_url": source.official_url, "cfp_text": text, "topic_text": text,
            "submission_deadline_raw": deadline_raw, "submission_deadline_utc": deadline, "timezone": zone,
            "deadline_type": "FULL_PAPER" if deadline else None, "status": self._status(deadline, checked_at),
            "source_priority": source.source_priority, "official_verified": True, "last_checked_at": checked_at,
            "content_hash": content_hash, "retrieval_method": method, "stale": False,
        }
        saved = self.repository.save_opportunity(values)
        self.repository.insert(models.opportunity_snapshots, snapshot_id=new_id(), opportunity_id=saved["opportunity_id"], raw_content=raw_html, retrieved_at=checked_at, content_hash=content_hash, source_url=source.official_url, retrieval_method=method)
        self._save_topics(saved["opportunity_id"], text)
        self._save_workshops(source, links, checked_at)
        return saved

    def _save_topics(self, opportunity_id: str, text: str) -> None:
        vocabulary = ("robotics", "reinforcement learning", "world model", "multimodal", "uncertainty quantification", "agentic systems", "evaluation", "datasets and benchmarks")
        lower = text.lower()
        for topic in vocabulary:
            if topic not in lower:
                continue
            with self.repository.engine.connect() as connection:
                existing = connection.execute(select(models.opportunity_topics).where(models.opportunity_topics.c.opportunity_id == opportunity_id, models.opportunity_topics.c.normalized_topic == topic)).first()
            if not existing:
                self.repository.insert(models.opportunity_topics, opportunity_topic_id=new_id(), opportunity_id=opportunity_id, topic=topic, normalized_topic=topic, source_span=topic, weight=1.0)

    def _save_workshops(self, source: OfficialOpportunitySource, links: list[tuple[str, str]], now: datetime) -> None:
        for href, label in links:
            if "workshop" not in f"{href} {label}".lower() or not label:
                continue
            self.repository.save_opportunity({
                "opportunity_type": "WORKSHOP_CFP", "title": label, "venue_name": source.venue_name,
                "venue_year": source.venue_year, "parent_event": f"{source.venue_name} {source.venue_year}", "track_name": label,
                "official_url": urljoin(source.official_url, href), "cfp_text": label, "topic_text": label,
                "submission_deadline_raw": None, "submission_deadline_utc": None, "timezone": None, "deadline_type": None,
                "status": "UNKNOWN", "source_priority": source.source_priority, "official_verified": True,
                "last_checked_at": now, "content_hash": hashlib.sha256(label.encode()).hexdigest(), "retrieval_method": "HTTP", "stale": False,
            })

    def sync(self, sources=OFFICIAL_SOURCES) -> list[dict]:
        return [self.sync_source(source) for source in sources]

    def list(self) -> list[dict]:
        return self.repository.list_opportunities()

    def show(self, opportunity_id: str) -> dict | None:
        return self.repository.get_opportunity(opportunity_id)

    def workshops(self) -> list[dict]:
        return self.repository.list_opportunities(kind="WORKSHOP_CFP")

    def upcoming(self, *, now: datetime | None = None) -> list[dict]:
        current = now or datetime.now(timezone.utc)
        return [item for item in self.repository.list_opportunities() if item["status"] in {"OPEN", "UPCOMING"} and item["submission_deadline_utc"] and item["submission_deadline_utc"] >= current]

    def generate_signals(self, *, domain: str) -> list[dict]:
        output = []
        for opportunity in self.repository.list_opportunities():
            fingerprint = hashlib.sha256(f"opportunity:{opportunity['opportunity_id']}:{domain}".encode()).hexdigest()
            with self.repository.engine.connect() as connection:
                existing = connection.execute(select(models.research_signals).where(models.research_signals.c.fingerprint == fingerprint)).first()
            if existing:
                output.append(dict(existing._mapping))
                continue
            output.append(self.repository.insert(
                models.research_signals, signal_id=new_id(), signal_type="COMMUNITY_INTEREST_SIGNAL",
                source_type="OPPORTUNITY", source_id=opportunity["opportunity_id"], title=opportunity["title"],
                description=f"Official opportunity mentions themes relevant to {domain}; this is interest evidence, not novelty evidence.",
                evidence_refs=[{"opportunity_id": opportunity["opportunity_id"], "url": opportunity["official_url"], "content_hash": opportunity["content_hash"]}],
                domain=domain, topic_tags=[opportunity["venue_name"], opportunity["opportunity_type"]],
                novelty_hint="REQUIRES_LITERATURE_AUDIT", fingerprint=fingerprint,
            ))
        return output
