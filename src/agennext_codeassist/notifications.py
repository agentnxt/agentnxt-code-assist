"""Unified notifications: Calendar, Slack, WhatsApp, Email, Push.

Supports:
- Email (SMTP)
- Slack webhooks
- WhatsApp (Twilio)
- Push (Web Push API)
- Calendar (Google Calendar API)
"""

from __future__ import annotations

import json
import os
import smtplib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.message import EmailMessage
from enum import Enum
from pathlib import Path
from typing import Any

import urllib.request
import urllib.parse


# === Notification Types ===

class NotificationType(Enum):
    EMAIL = "email"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    PUSH = "push"
    CALENDAR = "calendar"


@dataclass
class NotificationChannel:
    """A notification channel configuration."""
    type: NotificationType
    name: str
    
    # Config
    enabled: bool = False
    webhook_url: str | None = None
    api_key: str | None = None
    
    # Channel-specific
    channel_id: str | None = None  # Slack channel, WhatsApp to, etc.
    from_address: str | None = None  # Email from, calendar from
    
    def is_configured(self) -> bool:
        return self.enabled and (
            self.webhook_url or 
            self.api_key or 
            self.channel_id
        )


@dataclass
class NotificationMessage:
    """A notification message."""
    title: str
    body: str
    
    # Metadata
    priority: str = "normal"  # "low", "normal", "high", "urgent"
    tags: list[str] = field(default_factory=list)
    
    # Action
    action_url: str | None = None
    action_text: str = "View"
    
    # Fields for formatted messages
    fields: dict[str, str] = field(default_factory=dict)
    
    def to_slack_block(self) -> dict[str, Any]:
        """Convert to Slack block."""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": self.title}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": self.body}
            }
        ]
        
        if self.fields:
            fields = [
                {"type": "mrkdwn", "text": f"*{k}: {v}"}
                for k, v in self.fields.items()
            ]
            blocks.append({
                "type": "section",
                "fields": fields[:10]  # Max 10 fields
            })
        
        if self.action_url:
            blocks.append({
                "type": "actions",
                "elements": [{
                    "type": "button",
                    "text": {"type": "plain_text", "text": self.action_text},
                    "url": self.action_url,
                    "style": "primary" if self.priority == "urgent" else "default"
                }]
            })
        
        return {"blocks": blocks}
    
    def to_email(self) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = self.title
        msg["Body"] = self.body
        return msg
    
    def to_whatsapp(self) -> str:
        return f"*{self.title}*\n\n{self.body}"


# === Notification Manager ===

class NotificationManager:
    """Manages all notification channels."""
    
    def __init__(self):
        self.channels: dict[NotificationType, NotificationChannel] = {
            NotificationType.EMAIL: NotificationChannel(
                type=NotificationType.EMAIL,
                name="Email",
                enabled=bool(os.getenv("SMTP_URL")),
                webhook_url=os.getenv("SMTP_URL"),
            ),
            NotificationType.SLACK: NotificationChannel(
                type=NotificationType.SLACK,
                name="Slack",
                enabled=bool(os.getenv("SLACK_WEBHOOK_URL")),
                webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
                channel_id=os.getenv("SLACK_CHANNEL"),
            ),
            NotificationType.WHATSAPP: NotificationChannel(
                type=NotificationType.WHATSAPP,
                name="WhatsApp",
                enabled=bool(os.getenv("TWILIO_ACCOUNT_SID")),
                api_key=os.getenv("TWILIO_ACCOUNT_SID"),
                channel_id=os.getenv("TWILIO_TO_PHONE"),
            ),
            NotificationType.PUSH: NotificationChannel(
                type=NotificationType.PUSH,
                name="Push",
                enabled=bool(os.getenv("PUSH_VAPID_KEY")),
                api_key=os.getenv("PUSH_VAPID_KEY"),
            ),
            NotificationType.CALENDAR: NotificationChannel(
                type=NotificationType.CALENDAR,
                name="Calendar",
                enabled=bool(os.getenv("GOOGLE_CALENDAR_API_KEY")),
                api_key=os.getenv("GOOGLE_CALENDAR_API_KEY"),
            ),
        }
    
    def send(
        self,
        message: NotificationMessage,
        types: list[NotificationType] | None = None,
    ) -> dict[NotificationType, bool]:
        """Send notification to specified channels.
        
        Returns: {type: success}
        """
        if types is None:
            types = [t for t in NotificationType if self.channels[t].is_configured()]
        
        results = {}
        for ntype in types:
            success = self._send(ntype, message)
            results[ntype] = success
        
        return results
    
    def _send(self, ntype: NotificationType, message: NotificationMessage) -> bool:
        channel = self.channels.get(ntype)
        if not channel or not channel.enabled:
            return False
        
        try:
            if ntype == NotificationType.EMAIL:
                return self._send_email(channel, message)
            elif ntype == NotificationType.SLACK:
                return self._send_slack(channel, message)
            elif ntype == NotificationType.WHATSAPP:
                return self._send_whatsapp(channel, message)
            elif ntype == NotificationType.PUSH:
                return self._send_push(channel, message)
            elif ntype == NotificationType.CALENDAR:
                return self._send_calendar(channel, message)
        except Exception as e:
            print(f"Failed to send {ntype.value}: {e}")
            return False
        
        return False
    
    def _send_email(self, channel: NotificationChannel, message: NotificationMessage) -> bool:
        if not channel.webhook_url:
            return False
        
        msg = message.to_email()
        msg["From"] = channel.from_address or "agent@localhost"
        
        # Parse SMTP URL
        from urllib.parse import urlparse
        parsed = urlparse(channel.webhook_url)
        
        smtp = smtplib.SMTP(parsed.hostname, parsed.port or 587)
        smtp.starttls()
        
        # Auth if credentials provided
        if parsed.username and parsed.password:
            smtp.login(parsed.username, parsed.password)
        
        smtp.send_message(msg)
        smtp.quit()
        return True
    
    def _send_slack(self, channel: NotificationChannel, message: NotificationMessage) -> bool:
        if not channel.webhook_url:
            return False
        
        payload = message.to_slack_block()
        
        # Add channel if specified
        if channel.channel_id:
            payload["channel"] = channel.channel_id
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            channel.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req)
        return True
    
    def _send_whatsapp(self, channel: NotificationChannel, message: NotificationMessage) -> bool:
        if not channel.api_key or not channel.channel_id:
            return False
        
        # Twilio API
        account_sid = channel.api_key
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        
        body = urllib.parse.urlencode({
            "To": channel.channel_id,
            "From": os.getenv("TWILIO_FROM_PHONE"),
            "Body": message.to_whatsapp(),
        })
        
        auth = (account_sid, os.getenv("TWILIO_AUTH_TOKEN"))
        req = urllib.request.Request(
            url,
            data=body.encode("utf-8"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    
    def _send_push(self, channel: NotificationChannel, message: NotificationMessage) -> bool:
        # Web Push requires subscription handling
        # This is a simplified implementation
        if not channel.api_key:
            return False
        
        # Would need push subscription endpoint
        # Placeholder for implementation
        return False
    
    def _send_calendar(self, channel: NotificationChannel, message: NotificationMessage) -> bool:
        if not channel.api_key:
            return False
        
        # Google Calendar API
        calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
        
        event = {
            "summary": message.title,
            "description": message.body,
            "start": {"dateTime": datetime.now().isoformat()},
            "end": {"dateTime": (datetime.now() + timedelta(hours=1)).isoformat()},
        }
        
        data = json.dumps(event).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {channel.api_key}",
            },
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception:
            return False
    
    def get_configured_channels(self) -> list[NotificationType]:
        return [
            t for t in NotificationType 
            if self.channels[t].is_configured()
        ]


# === Convenience Functions ===

def notify(
    title: str,
    body: str,
    *,
    priority: str = "normal",
    channels: list[NotificationType] | None = None,
    **kwargs,
) -> dict[NotificationType, bool]:
    """Send notification to configured channels.
    
    Usage:
        notify(
            "Build Complete",
            "Successfully built production artifact",
            priority="normal",
        )
        
        notify(
            "Error",
            "Build failed: check logs",
            priority="urgent",
            channels=[NotificationType.SLACK, NotificationType.EMAIL],
        )
    """
    msg = NotificationMessage(
        title=title,
        body=body,
        priority=priority,
        **kwargs,
    )
    
    manager = NotificationManager()
    return manager.send(msg, channels)


def notify_run_start(objective: str, run_id: str) -> dict[NotificationType, bool]:
    """Notify that a run has started."""
    return notify(
        f"🚀 Run Started: {run_id[:8]}",
        f"Objective: {objective[:100]}",
        fields={"Run ID": run_id[:8], "Status": "Started"},
    )


def notify_run_complete(
    result: str,
    run_id: str,
    files_modified: int = 0,
) -> dict[NotificationType, bool]:
    """Notify that a run completed."""
    priority = "urgent" if result == "failed" else "normal"
    
    return notify(
        f"{'✅' if result == 'success' else '❌'} Run Complete: {run_id[:8]}",
        f"Result: {result}\nFiles modified: {files_modified}",
        priority=priority,
        fields={
            "Run ID": run_id[:8],
            "Result": result,
            "Files": str(files_modified),
        },
    )


def notify_decision_blocked(decision: str, reason: str) -> dict[NotificationType, bool]:
    """Notify that a decision was blocked by constraints."""
    return notify(
        "🚫 Decision Blocked",
        f"{decision}\nReason: {reason}",
        priority="high",
        fields={"Decision": decision, "Reason": reason},
    )


def notify_budget_warning(
    remaining_usd: float,
    run_id: str,
) -> dict[NotificationType, bool]:
    """Notify of budget warning."""
    return notify(
        "⚠️ Budget Warning",
        f"${remaining_usd:.2f} remaining for run {run_id[:8]}",
        priority="high",
        fields={"Remaining": f"${remaining_usd:.2f}"},
    )


# === Singleton ===

_manager: NotificationManager | None = None


def get_notification_manager() -> NotificationManager:
    global _manager
    if _manager is None:
        _manager = NotificationManager()
    return _manager