"""Alerting rules: SAIDI/SAIFI threshold breaches (Slack optional)."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def breaches_saidi(daily: pd.DataFrame, threshold_min: float) -> pd.DataFrame:
    """Rows where daily SAIDI_min >= threshold."""
    return daily[daily["SAIDI_min"] >= threshold_min].copy()


def breaches_saifi(daily: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Rows where daily SAIFI_events_per_cust >= threshold."""
    return daily[daily["SAIFI_events_per_cust"] >= threshold].copy()


def post_slack(webhook_url: str, title: str, rows: Iterable[dict]) -> None:
    """Send Slack message for rule breaches (requires slack-sdk)."""
    try:
        from slack_sdk.webhook import WebhookClient
    except ImportError:
        raise ImportError("slack_sdk required for post_slack")
    client = WebhookClient(webhook_url)
    lines = [f"*{title}*"]
    for r in rows:
        parts = [f"{k}={v}" for k, v in r.items()]
    lines.append(" • " + ", ".join(parts))
    client.send(text="\n".join(lines))
