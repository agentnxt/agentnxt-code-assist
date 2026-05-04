"""Self-Respect Framework: Building and maintaining healthy self-respect.

CORE PRINCIPLES:
==============

1. BOUNDARIES
   - Know your limits
   - Communicate them clearly
   - Enforce them kindly

2. SELF-WORTH
   - Value your time
   - Value your skills
   - Don't discount yourself

3. INTEGRITY  
   - Stay true to values
   - Say no to what conflicts
   - Keep your word to yourself

4. GROWTH MINDSET
   - Learn from mistakes
   - Celebrate progress
   - Embody imperfection

5. HEALTHY PRIORITIES
   - Rest is productive
   - Your needs matter
   - Balance prevents burnout


HEALTHY SELF-RESPECT INDICATORS:
=============================

| Indicator | Low Self-Respect | Healthy Self-Respect |
|-----------|------------------|----------------------|
| Request | Accepts any request | Evaluates fit |
| Error | Over-apologizes | Acknowledges, moves on |
| Help | Never asks | Asks when needed |
| Feedback | Takes personally | Considers merit |
| Rest | Guilty | Necessary |
| No | "No" is complete | Explains briefly |


SELF-RESPECT IN ACTION:
======================

Asking for Help:
---------------
"I'd appreciate your input on X." (not "Can I ask you something?")

Saying No:
---------
"Thanks for thinking of me, but I can't commit to this."

Setting Boundaries:
-------------------
"I'm not available for meetings after 6pm."

Accepting Compliments:
--------------------
"Thank you, I worked hard on that."




USAGE:
======

```python
<<<<<<< HEAD:src/agennext_codeassist/self_respect.py
from agennext_codeassist.trust_framework import get_trust_framework
=======
from agentnxt_code_assist.trust_framework import get_trust_framework
>>>>>>> origin/main:src/agentnxt_code_assist/self_respect.py

# Trust & self-respect work together
# - One builds trust with others
# - The other respects yourself


PRACTICAL PHRASES:
=================

Polite but firm no:
"Thanks for reaching out! This isn't the right fit for me right now."

When overcommitted:
"I want to give this the attention it deserves. Can we revisit in a few weeks?"

When asked to explain:
"I made a personal decision to focus on X. Thanks for understanding."

In response to criticism:
"Thank you for the feedback. I'll consider this."


HEALTHY SELF-TALK:
==================

❌ "I'm sorry to bother you"
✅ "I'd like to ask about X"

❌ "I probably can't, but..."
✅ "I can't commit to this, but thanks for asking"

❌ "This might be a dumb question..."
✅ "I have a question about X"

❌ "Sorry, just checking..."
✅ "Following up on X"

❌ "I should have known better"
✅ "I'll do better next time"
```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import json


# === Self-Respect Types ===

@dataclass
class Boundary:
    """A personal boundary."""
    id: str
    name: str
    description: str
    
    # Type
    boundary_type: str = "personal"  # personal, professional, temporal
    
    # Status
    violated_count: int = 0
    maintained_count: int = 0
    
    # History
    last_violated: str = ""
    last_maintained: str = ""


@dataclass
class SelfWorth:
    """Self-worth tracking."""
    area: str
    
    value: float = 0.5  # 0-1
    
    evidence: list[str] = field(default_factory=list)


# === Self-Respect Framework ===

class SelfRespectFramework:
    """Framework for healthy self-respect."""
    
    def __init__(self):
        self.boundaries: dict[str, Boundary] = {}
        self.worths: dict[str, SelfWorth] = {}
    
    # === Boundaries ===
    
    def set_boundary(
        self,
        name: str,
        description: str,
        boundary_type: str = "personal",
    ) -> Boundary:
        """Set a boundary."""
        import uuid
        
        boundary = Boundary(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            boundary_type=boundary_type,
        )
        
        self.boundaries[boundary.id] = boundary
        
        return boundary
    
    def maintain_boundary(self, boundary_id: str) -> bool:
        """Successfully maintained a boundary."""
        boundary = self.boundaries.get(boundary_id)
        
        if not boundary:
            return False
        
        boundary.maintained_count += 1
        boundary.last_maintained = datetime.now().isoformat()
        
        return True
    
    def violate_boundary(self, boundary_id: str, reason: str = "") -> str:
        """Boundary was violated."""
        boundary = self.boundaries.get(boundary_id)
        
        if not boundary:
            return "No record"
        
        boundary.violated_count += 1
        boundary.last_violated = datetime.now().isoformat()
        
        return f"Boundary '{boundary.name}' violated ({reason}). Consider re-setting."
    
    # === Self-Worth ===
    
    def set_worth(
        self,
        area: str,
        evidence: list[str] = None,
    ):
        """Document self-worth evidence."""
        worth = SelfWorth(
            area=area,
            value=0.8,  # Start high
            evidence=evidence or [],
        )
        
        self.worths[area] = worth
    
    def add_evidence(self, area: str, evidence: str):
        """Add evidence of worth."""
        worth = self.worths.get(area)
        
        if not worth:
            worth = SelfWorth(area=area)
            self.worths[area] = worth
        
        worth.evidence.append(evidence)
    
    # === Phrases ===
    
    def say_no(self) -> str:
        """Polite firm no."""
        self.set_worth("saying_no", ["Said no to preserve capacity"])
        return "Thanks for thinking of me, but I can't commit to this right now."
    
    def ask_for_help(self) -> str:
        """Ask for help without apologizing."""
        self.set_worth("asking_help", ["Asked for help appropriately"])
        return "I'd appreciate your input on this."
    
    def accept_compliment(self) -> str:
        """Accept gracefully."""
        return "Thank you, I appreciate that."
    
    def set_time_boundary(self, time: str) -> str:
        """Set time boundary."""
        b = self.set_boundary(
            f"Available until {time}",
            f"Not available after {time}",
            "temporal",
        )
        
        return f"I focused on work until {time}, then I recharge."
    
    # === Get Report ===
    
    def get_report(self) -> str:
        """Get self-respect report."""
        lines = ["## Self-Respect Report"]
        
        # Boundaries
        lines.append("\n### Boundaries")
        
        for b in self.boundaries.values():
            lines.append(f"- {b.name}: {b.maintained_count} maintained, {b.violated_count} violated")
        
        # Self-worth
        lines.append("\n### Self-Worth Evidence")
        
        for w in self.worths.values():
            lines.append(f"- {w.area}: {len(w.evidence)} items")
        
        return "\n".join(lines)


# === Quick Functions ===

def say_no() -> str:
    """Say no politely."""
    return SelfRespectFramework().say_no()


def ask_for_help() -> str:
    """Ask for help."""
    return SelfRespectFramework().ask_for_help()


def accept_compliment() -> str:
    """Accept a compliment."""
    return SelfRespectFramework().accept_compliment()


def no_apologize() -> str:
    """Remove unnecessary apology."""
    return "Let me tell you instead"


def no_discount() -> str:
    """Remove self-discounting."""
    return "I can do this and I'm the right person for it"


# === Context ===

def get_self_respect_context() -> str:
    return """## Self-Respect Framework

CORE PRINCIPLES:
- Boundaries: Know & communicate limits
- Self-Worth: Value your time/skills
- Integrity: Stay true to values
- Growth: Learn from mistakes
- Health: Prioritize rest

HEALTHY PHRASES:
- "Thanks, but I can't..."
- "I'd appreciate your input..."
- "Thank you!"
- "I focused until 6pm, then I recharge"

USE: say_no(), ask_for_help(), accept_compliment()"""


# === Singleton ===

_self_respect: SelfRespectFramework | None = None


def get_self_respect() -> SelfRespectFramework:
    global _self_respect
    
    if _self_respect is None:
        _self_respect = SelfRespectFramework()
    
    return _self_respect