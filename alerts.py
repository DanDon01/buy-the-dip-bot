"""
Alerts system - notifies you when a stock hits "perfect buy" conditions.

Channels (all optional, enabled by environment variables / .env):

Email (SMTP):
    ALERT_SMTP_HOST, ALERT_SMTP_PORT (default 587), ALERT_SMTP_USER,
    ALERT_SMTP_PASSWORD, ALERT_EMAIL_FROM, ALERT_EMAIL_TO (comma separated)

SMS (Twilio REST API - no extra dependency, plain HTTPS):
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, ALERT_SMS_TO

Webhook (Discord / Slack / anything accepting JSON POST):
    ALERT_WEBHOOK_URL

Usage:
    python cli.py --check-alerts [--threshold 75]

Alerts are deduplicated: a ticker only re-alerts after ALERT_COOLDOWN_HOURS
(default 24) or if its score improves by 5+ points. State is stored in
cache/alerts_state.json and every alert is appended to alerts_log.csv.
"""

from __future__ import annotations

import csv
import json
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

STATE_FILE = os.path.join("cache", "alerts_state.json")
LOG_FILE = "alerts_log.csv"
DEFAULT_COOLDOWN_HOURS = float(os.getenv("ALERT_COOLDOWN_HOURS", "24"))


class AlertManager:
    """Finds buy-condition candidates and dispatches notifications."""

    def __init__(self, threshold: float = 75.0,
                 cooldown_hours: float = DEFAULT_COOLDOWN_HOURS):
        self.threshold = threshold
        self.cooldown = timedelta(hours=cooldown_hours)
        self.state = self._load_state()

    # ------------------------------------------------------------------
    # Candidate detection
    # ------------------------------------------------------------------
    def find_candidates(self, scores_data: Optional[Dict] = None) -> List[Dict]:
        """Return alert-worthy stocks from cache/daily_scores.json."""
        if scores_data is None:
            try:
                with open(os.path.join("cache", "daily_scores.json")) as f:
                    scores_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                print("⚠️  No daily_scores.json - run scoring first.")
                return []

        candidates = []
        for ticker, info in (scores_data.get("scores") or {}).items():
            score = info.get("score", 0) or 0
            details = info.get("score_details", {}) or {}
            rec = details.get("investment_recommendation", {}) or {}
            action = rec.get("action", "")

            if score >= self.threshold or action == "STRONG_BUY":
                candidates.append({
                    "ticker": ticker,
                    "score": round(float(score), 1),
                    "price": info.get("price"),
                    "action": action or "SCORE_ALERT",
                    "grade": details.get("overall_grade", ""),
                    "reason": rec.get("reason", ""),
                })
        candidates.sort(key=lambda c: c["score"], reverse=True)
        return candidates

    def filter_new(self, candidates: List[Dict]) -> List[Dict]:
        """Drop candidates alerted recently (unless score improved 5+ pts)."""
        fresh = []
        now = datetime.now()
        for cand in candidates:
            prev = self.state.get(cand["ticker"])
            if prev:
                try:
                    last_time = datetime.fromisoformat(prev["time"])
                except (ValueError, KeyError):
                    last_time = now - self.cooldown * 2
                improved = cand["score"] >= prev.get("score", 0) + 5
                if now - last_time < self.cooldown and not improved:
                    continue
            fresh.append(cand)
        return fresh

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    def check_and_send(self, dry_run: bool = False) -> List[Dict]:
        """Full pass: find candidates, dedupe, send, record. Returns sent list."""
        candidates = self.filter_new(self.find_candidates())
        if not candidates:
            print("✅ No new buy-condition alerts.")
            return []

        subject, body = format_alert_message(candidates, self.threshold)
        print(body)

        if not dry_run:
            sent_channels = dispatch_all(subject, body, candidates)
            if sent_channels:
                print(f"📨 Sent via: {', '.join(sent_channels)}")
            else:
                print("ℹ️  No alert channels configured - printed to console only.\n"
                      "   Set ALERT_SMTP_*, TWILIO_*, or ALERT_WEBHOOK_URL to enable delivery.")
            self._record(candidates)
        return candidates

    def _record(self, candidates: List[Dict]):
        now = datetime.now().isoformat()
        for cand in candidates:
            self.state[cand["ticker"]] = {"time": now, "score": cand["score"]}
        self._save_state()
        self._append_log(candidates, now)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load_state(self) -> Dict:
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_state(self):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def _append_log(self, candidates: List[Dict], timestamp: str):
        exists = os.path.exists(LOG_FILE)
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(["timestamp", "ticker", "score", "price", "action", "grade"])
            for c in candidates:
                writer.writerow([timestamp, c["ticker"], c["score"],
                                 c.get("price"), c["action"], c.get("grade")])


# ----------------------------------------------------------------------
# Message formatting
# ----------------------------------------------------------------------
def format_alert_message(candidates: List[Dict], threshold: float) -> tuple[str, str]:
    """Build (subject, body) for the alert notification."""
    top = candidates[0]
    subject = (f"🎯 Buy-the-Dip alert: {top['ticker']} scored {top['score']}"
               + (f" (+{len(candidates) - 1} more)" if len(candidates) > 1 else ""))
    lines = [
        f"Buy-the-Dip Bot - {len(candidates)} stock(s) hit buy conditions "
        f"(threshold {threshold}):",
        "",
    ]
    for c in candidates:
        price = f"${c['price']:.2f}" if isinstance(c.get("price"), (int, float)) else "n/a"
        lines.append(f"  {c['ticker']:<6} score {c['score']:>5.1f}  {price:>9}  "
                     f"{c['action']:<11} grade {c.get('grade') or '-'}")
        if c.get("reason"):
            lines.append(f"         ↳ {c['reason']}")
    lines += ["", f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
    return subject, "\n".join(lines)


# ----------------------------------------------------------------------
# Channels
# ----------------------------------------------------------------------
def dispatch_all(subject: str, body: str, candidates: List[Dict]) -> List[str]:
    """Send through every configured channel. Returns names of channels used."""
    sent = []
    if send_email(subject, body):
        sent.append("email")
    if send_sms(subject):
        sent.append("sms")
    if send_webhook(subject, body, candidates):
        sent.append("webhook")
    return sent


def send_email(subject: str, body: str) -> bool:
    host = os.getenv("ALERT_SMTP_HOST")
    to_addrs = [a.strip() for a in os.getenv("ALERT_EMAIL_TO", "").split(",") if a.strip()]
    if not host or not to_addrs:
        return False
    try:
        port = int(os.getenv("ALERT_SMTP_PORT", "587"))
        user = os.getenv("ALERT_SMTP_USER")
        password = os.getenv("ALERT_SMTP_PASSWORD")
        from_addr = os.getenv("ALERT_EMAIL_FROM", user or "buy-the-dip-bot@localhost")

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_addrs)

        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            if port != 25:
                try:
                    server.starttls()
                    server.ehlo()
                except smtplib.SMTPNotSupportedError:
                    pass
            if user and password:
                server.login(user, password)
            server.sendmail(from_addr, to_addrs, msg.as_string())
        return True
    except Exception as e:
        print(f"⚠️  Email alert failed: {e}")
        return False


def send_sms(message: str) -> bool:
    """Send an SMS via the Twilio REST API (plain HTTPS, no SDK needed)."""
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_num = os.getenv("TWILIO_FROM_NUMBER")
    to_num = os.getenv("ALERT_SMS_TO")
    if not all([sid, token, from_num, to_num]):
        return False
    try:
        resp = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={"From": from_num, "To": to_num, "Body": message[:1500]},
            timeout=15,
        )
        if resp.status_code >= 300:
            print(f"⚠️  SMS alert failed: HTTP {resp.status_code} {resp.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"⚠️  SMS alert failed: {e}")
        return False


def send_webhook(subject: str, body: str, candidates: List[Dict]) -> bool:
    """POST to a generic webhook. Discord ('content') and Slack ('text')
    payload keys are both included, so either works out of the box."""
    url = os.getenv("ALERT_WEBHOOK_URL")
    if not url:
        return False
    try:
        text = f"**{subject}**\n```{body}```"
        resp = requests.post(url, json={
            "content": text[:1990],   # Discord limit
            "text": text,             # Slack
            "candidates": candidates,
        }, timeout=15)
        if resp.status_code >= 300:
            print(f"⚠️  Webhook alert failed: HTTP {resp.status_code}")
            return False
        return True
    except Exception as e:
        print(f"⚠️  Webhook alert failed: {e}")
        return False
