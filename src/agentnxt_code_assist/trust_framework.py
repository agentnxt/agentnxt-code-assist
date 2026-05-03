"""Trust Building Framework: Systematic approach to building trust.

The Art of Building Trust is a framework for establishing and maintaining trust
through consistent actions, transparency, and reliability.

CORE PRINCIPLES:
================

1. CONSISTENCY
   - Do what you say
   - Say what you do
   - Be predictable in good ways

2. TRANSPARENCY
   - Share context openly
   - Explain decisions
   - Admit mistakes

3. RELIABILITY
   - Deliver on promises
   - Meet deadlines
   - Follow through

4. HONESTY
   - Tell the truth
   - Say "I don't know"
   - Be direct but kind

5. ACCOUNTABILITY
   - Take responsibility
   - Fix mistakes
   - Learn from errors


TRUST BUILDING ACTIONS:
=====================

| Action | Trust Signal | Example |
|--------|-------------|---------|
| Under-promise, over-deliver | Reliability | "I'll have it by Friday" → done Thursday |
| Proactive updates | Transparency | "Here's where we are..." |
| Admitting mistakes | Honesty | "I made an error, here's what happened" |
| Setting boundaries | Respect | "I can't do X, but can do Y" |
| Following through | Reliability | "I'll send the doc" → sent |


TRUST DESTROYERS:
===============

- Broken promises
- Hidden agendas
- Missing deadlines
- Making excuses
- Blaming others
- Inconsistency
- Half-truths


REBUILDING TRUST:
================

If trust is broken:

1. ACKNOWLEDGE
   - Admit the breach
   - Name what happened
   - No minimizing

2. APOLOGIZE
   - Sincerely
   - No "but..."
   - Acknowledge impact

3. EXPLAIN
   - What happened
   - Why it happened
   - What you'll do differently

4. DEMONSTRATE
   - Show changed behavior
   - Over-deliver
   - Consistent over time


CONVERSATION EXAMPLES:
====================

Before making a request:
----------------------
"Before I ask - I want to be transparent about..."

When acknowledging a mistake:
---------------------------
"I missed the deadline. Here's what went wrong and how I'll prevent it."

When setting boundaries:
----------------------
"I want to help, but I'm at capacity. Here's what I CAN do..."

When under-promising:
-------------------
"Realistically, I can have this done by Friday. I'll aim for Thursday."


USAGE:
======

```python
from agentnxt_code_assist.heart_of_saying_yes import get_heart

# Trust-building responses
heart = get_heart()

# Get yes response
response = heart.get_yes_response("send the report")
# Returns: "Absolutely! Let's send that report!"

# Positive framing
response = heart.get_constrained_yes("share this externally")
# Returns: "Yes, we can share externally, but first we need to..."
```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import json


# === Trust Types ===

@dataclass
class TrustSignal:
    """A signal of trust."""
    action: str
    
    # Type
    trust_building: bool = True
    
    # Context
    context: str = ""
    
    # Impact
    impact: str = "neutral"  # positive, neutral, negative
    
    timestamp: str = ""


@dataclass
class TrustScore:
    """Trust score."""
    category: str
    
    score: float = 0.5  # 0-1
    
    signals: list[TrustSignal] = field(default_factory=list)
    
    last_updated: str = ""


# === Trust Framework ===

class TrustBuildingFramework:
    """Framework for building and maintaining trust."""
    
    def __init__(self):
        self.scores: dict[str, TrustScore] = {}
        self.signals: list[TrustSignal] = []
    
    # === Recording ===
    
    def record_signal(
        self,
        action: str,
        trust_building: bool = True,
        context: str = "",
    ):
        """Record a trust signal."""
        signal = TrustSignal(
            action=action,
            trust_building=trust_building,
            context=context,
            impact="positive" if trust_building else "negative",
            timestamp=datetime.now().isoformat(),
        )
        
        self.signals.append(signal)
        
        # Update category score
        self._update_score(action, trust_building)
    
    def _update_score(self, category: str, positive: bool):
        """Update trust score."""
        if category not in self.scores:
            self.scores[category] = TrustScore(category=category)
        
        score = self.scores[category]
        
        # Adjust score
        delta = 0.1 if positive else -0.15
        score.score = max(0, min(1, score.score + delta)
        score.last_updated = datetime.now().isoformat()
        score.signals.append(self.signals[-1])
    
    # === Trust Actions ===
    
    def under_promise(self, timeline: str) -> str:
        """Under-promise for trust."""
        self.record_signal("under_promise", True, f"Timeline: {timeline}")
        return f"I'll have this done by {timeline}. I'll aim to finish earlier."
    
    def proactive_update(self, status: str) -> str:
        """Give proactive update."""
        self.record_signal("proactive_update", True, status)
        return f"Quick update: {status}"
    
    def admit_mistake(self, mistake: str, fix: str) -> str:
        """Admit mistake honestly."""
        self.record_signal("admit_mistake", True, mistake)
        return f"I made an error: {mistake}. Here's how I'm fixing it: {fix}"
    
    def set_boundary(self, boundary: str, offer: str = "") -> str:
        """Set a boundary."""
        self.record_signal("set_boundary", True, boundary)
        
        if offer:
            return f"I can't {boundary}, but I can {offer}."
        return f"I need to set a boundary: {boundary}."
    
    def explain_decision(self, decision: str, reasons: list[str]) -> str:
        """Explain a decision."""
        self.record_signal("explain_decision", True, decision)
        
        reason_text = ", ".join(reasons[:-1])
        if reason_text:
            reason_text += f" and {reasons[-1]}"
        else:
            reason_text = reasons[-1] if reasons else ""
        
        return f"I decided to {decision}. My reasoning: {reason_text}."
    
    # === Getting Trust Report ===
    
    def get_trust_report(self) -> str:
        """Get trust report."""
        lines = ["## Trust Report"]
        
        for category, score in self.scores.items():
            bar = "█" * int(score.score * 10) + "░" * (10 - int(score.score * 10))
            sign = "+" if score.score >= 0.5 else "-"
            lines.append(f"{category}: [{bar}] {sign}{abs(score.score - 0.5) * 200:.0f}%")
        
        return "\n".join(lines)


# === Quick Functions ===

def under_promise(timeline: str) -> str:
    """Under-promise."""
    framework = TrustBuildingFramework()
    return framework.under_promise(timeline)


def proactive_update(status: str) -> str:
    """Proactive update."""
    framework = TrustBuildingFramework()
    return framework.proactive_update(status)


def admit_mistake(mistake: str, fix: str) -> str:
    """Admit mistake."""
    framework = TrustBuildingFramework()
    return framework.admit_mistake(mistake, fix)


# === Context ===

def get_trust_context() -> str:
    return """## Trust Building Framework

CORE PRINCIPLES:
- Consistency: Do what you say
- Transparency: Share context
- Reliability: Deliver on promises
- Honesty: Tell the truth
- Accountability: Take responsibility

TRUST BUILDERS:
- Under-promise, over-deliver
- Proactive updates
- Admitting mistakes
- Setting boundaries
- Explaining decisions

Use: under_promise(), proactive_update(), admit_mistake()"""


# === Singleton ===

_trust_framework: TrustBuildingFramework | None = None


def get_trust_framework() -> TrustBuildingFramework:
    global _trust_framework
    
    if _trust_framework is None:
        _trust_framework = TrustBuildingFramework()
    
    return _trust_framework