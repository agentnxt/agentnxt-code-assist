"""Empathy system: understands user emotions and adapts communication.

Tracks and responds to:
- User emotional state
- Communication preferences
- Frustration/satisfaction signals
- Help-seeking behavior
- Task completion patterns
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from pathlib import Path
from typing import Any

import json


# === Emotional State ===

class EmotionalState(Enum):
    NEUTRAL = "neutral"
    SATISFIED = "satisfied"
    FRUSTRATED = "frustrated"
    CONFUSED = "confused"
    EXCITED = "excited"
    WORRIED = "worried"
    PATIENT = "patient"
    HURRIED = "hurried"


class Tone(Enum):
    FORMAL = "formal"
    CASUAL = "casual"
    DIRECT = "direct"
    EMPATHETIC = "empathetic"
    ENCOURAGING = "encouraging"
    SYMPATHETIC = "sympathetic"


@dataclass
class UserEmotionProfile:
    """Profile of user's emotional patterns."""
    user_id: str
    
    # Observed states
    state_history: list[dict[str, Any]] = field(default_factory=list)
    tone_preference: Tone = Tone.DIRECT
    
    # Signals
    frustration_signals: int = 0
    satisfaction_signals: int = 0
    confusion_signals: int = 0
    
    # Patterns
    successful_tasks: int = 0
    failed_tasks: int = 0
    abandoned_tasks: int = 0
    
    # Average sentiment per session
    avg_sentiment: float = 0.0
    
    def detect_state(self, messages: list[dict]) -> EmotionalState:
        """Detect current emotional state from messages."""
        if not messages:
            return EmotionalState.NEUTRAL
        
        # Look at recent messages
        recent = messages[-5:]
        
        frustration_keywords = [
            "frustrated", "annoying", "this is taking too long",
            "why isn't it working", "seriously", "ugh", "give up",
            "never mind", "forget it", "stupid", "waste of time",
        ]
        
        confusion_keywords = [
            "confused", "don't understand", "what do you mean",
            "how does this work", "lost", "unsure", "which one",
            "help me understand", "explain", "unclear",
        ]
        
        satisfaction_keywords = [
            "great", "perfect", "exactly", "thanks", "wonderful",
            "love it", "awesome", "worked", "love you", "amazing",
        ]
        
        excitement_keywords = [
            "cool", "awesome", "can't wait", "excited",
            "interesting", "love this", "wow", "neat",
        ]
        
        # Count signals
        text = " ".join(
            m.get("content", "").lower() 
            for m in recent
        )
        
        frus_count = sum(1 for kw in frustration_keywords if kw in text)
        conf_count = sum(1 for kw in confusion_keywords if kw in text)
        sat_count = sum(1 for kw in satisfaction_keywords if kw in text)
        exc_count = sum(1 for kw in excitement_keywords if kw in text)
        
        # Determine state
        if frus_count >= 2:
            return EmotionalState.FRUSTRATED
        elif conf_count >= 2:
            return EmotionalState.CONFUSED
        elif exc_count >= 2:
            return EmotionalState.EXCITED
        elif sat_count >= 2:
            return EmotionalState.SATISFIED
        
        # Fall back to patterns
        if self.frustration_signals > self.satisfaction_signals * 2:
            return EmotionalState.FRUSTRATED
        elif self.satisfaction_signals > 5:
            return EmotionalState.SATISFIED
        
        return EmotionalState.NEUTRAL
    
    def get_recommended_tone(self) -> Tone:
        """Get recommended tone based on user profile."""
        # High frustration = more empathetic
        if self.frustration_signals > 3:
            return Tone.EMPATHETIC
        
        # Many successes = can be more casual
        if self.successful_tasks > 10:
            return Tone.CASUAL
        
        return self.tone_preference


# === Empathy Response Generator ===

@dataclass
class EmpathyResponse:
    """Response adapted to user's emotional state."""
    message: str
    
    # Adaptations
    tone: Tone = Tone.DIRECT
    should_acknowledge_frustration: bool = False
    should_explain_more: bool = False
    should_encourage: bool = False
    should_simplify: bool = False
    should_confirm_understanding: bool = False
    
    urgency_level: str = "normal"  # "low", "normal", "high"


class EmpathyEngine:
    """Generates empathetic responses based on user state."""
    
    # Response templates
    TEMPLATES = {
        EmotionalState.FRUSTRATED: {
            "start": [
                "I understand this is frustrating. Let me help.",
                "I hear your frustration. Let's get this working.",
                "I can see this isn't going smoothly. Here's what I'll do:",
            ],
            "simplify": [
                "Let me simplify the approach.",
                "I'll break this into smaller steps.",
                "Let me make this more straightforward.",
            ],
            "acknowledge": [
                "This should be faster.",
                "I apologize for the complexity.",
            ],
        },
        EmotionalState.CONFUSED: {
            "start": [
                "Let me explain more clearly.",
                "I want to make sure I understand - can you tell me more?",
                "Let me break this down for you:",
            ],
            "explain": [
                "Here's what's happening:",
                "Think of it this way:",
                "The key point is:",
            ],
            "confirm": [
                "Does that make sense?",
                "Would it help to summarize?",
                "Want me to clarify any part?",
            ],
        },
        EmotionalState.SATISFIED: {
            "congratulate": [
                "Great that it's working!",
                "Glad we got this working!",
                "Excellent!",
            ],
            "encourage": [
                "Ready for the next step whenever you are.",
                "Let me know what else needs doing.",
            ],
        },
        EmotionalState.EXCITED: {
            "match_excitement": [
                "I share your enthusiasm!",
                "That's great energy!",
                "Love the excitement!",
            ],
            "build": [
                "Exciting possibilities here:",
                "More we could do:",
                "If you want to explore further:",
            ],
        },
        EmotionalState.WORRIED: {
            "reassure": [
                "Don't worry, I'll make sure this works.",
                "I've got you covered.",
                "Let's take this one step at a time.",
            ],
            "clarify": [
                "What would help you feel more confident?",
                "What specific concern should I address?",
            ],
        },
        EmotionalState.HURRIED: {
            "speed_up": [
                "Let me be quick about this.",
                "I'll streamline this.",
                "Getting you the fastest result:",
            ],
            "prioritize": [
                "Here's the minimum you need to know:",
                "The key takeaway:",
            ],
        },
    }
    
    def __init__(self):
        self.user_profiles: dict[str, UserEmotionProfile] = {}
    
    def get_response(
        self,
        user_id: str,
        messages: list[dict],
        response_intent: str | None = None,
    ) -> EmpathyResponse:
        """Generate empathetic response."""
        profile = self.user_profiles.get(user_id)
        
        if not profile:
            profile = UserEmotionProfile(user_id=user_id)
            self.user_profiles[user_id] = profile
        
        # Detect state
        state = profile.detect_state(messages)
        
        # Get templates for state
        templates = self.TEMPLATES.get(state, self.TEMPLATES[EmotionalState.NEUTRAL])
        
        # Build response
        message_parts = []
        tone = profile.get_recommended_tone()
        
        # Start with state-appropriate message
        if state in [EmotionalState.FRUSTRATED, EmotionalState.WORRIED]:
            message_parts.append(templates["start"][0])
            should_ack = True
        elif state == EmotionalState.CONFUSED:
            message_parts.append(templates["start"][0])
            should_confirm = True
        elif state == EmotionalState.EXCITED:
            message_parts.append(templates["match_excitement"][0])
            should_encourage = True
        elif state == EmotionalState.SATISFIED:
            should_encourage = True
        else:
            should_ack = False
            should_confirm = False
        
        # Adapt based on state
        if state == EmotionalState.FRUSTRATED:
            message_parts.append(templates["simplify"][0])
            should_simplify = True
            urgency = "high"
        elif state == EmotionalState.CONFUSED:
            message_parts.append(templates["explain"][0])
            should_explain = True
            urgency = "normal"
        elif state == EmotionalState.HURRIED:
            message_parts.append(templates["speed_up"][0])
            urgency = "high"
        else:
            urgency = "normal"
        
        return EmpathyResponse(
            message="\n".join(message_parts),
            tone=tone,
            should_acknowledge_frustration=should_ack,
            should_confirm_understanding=should_confirm,
            should_explain_more=should_explain,
            should_encourage=should_encourage,
            should_simplify=should_simplify,
            urgency_level=urgency,
        )
    
    def adapt_to_state(
        self,
        base_message: str,
        user_id: str,
        messages: list[dict],
    ) -> str:
        """Adapt a base message to user's emotional state."""
        resp = self.get_response(user_id, messages)
        
        adaptations = []
        
        if resp.should_acknowledge_frustration:
            adaptations.append("I understand this is frustrating.")
        
        if resp.should_confirm_understanding:
            adaptations.append("\n\nDoes this make sense?")
        
        if resp.should_simplify:
            if "Here's a simpler approach:" not in base_message:
                adaptations.append("\n\nLet me simplify:")
        
        if resp.should_encourage and not base_message.endswith("?"):
            adaptations.append("\n\nYou're doing great!")
        
        if resp.urgency_level == "high":
            # Make more direct
            base_message = base_message.replace("Would you like", "Try")
        
        return base_message + "\n".join(adaptations)
    
    def record_signal(
        self,
        user_id: str,
        signal_type: str,  # "frustration", "satisfaction", "confusion"
    ):
        """Record emotional signal."""
        profile = self.user_profiles.get(user_id)
        
        if not profile:
            profile = UserEmotionProfile(user_id=user_id)
            self.user_profiles[user_id] = profile
        
        # Update signal counts
        if signal_type == "frustration":
            profile.frustration_signals += 1
        elif signal_type == "satisfaction":
            profile.satisfaction_signals += 1
        elif signal_type == "confusion":
            profile.confusion_signals += 1
    
    def record_task_outcome(
        self,
        user_id: str,
        success: bool,
    ):
        """Record task outcome."""
        profile = self.user_profiles.get(user_id)
        
        if not profile:
            profile = UserEmotionProfile(user_id=user_id)
            self.user_profiles[user_id] = profile
        
        if success:
            profile.successful_tasks += 1
            profile.satisfaction_signals += 1
        else:
            profile.failed_tasks += 1
            profile.frustration_signals += 1
    
    def get_user_report(self, user_id: str) -> str:
        """Get empathy report for user."""
        profile = self.user_profiles.get(user_id)
        
        if not profile:
            return "No data yet for this user."
        
        lines = ["## User Empathy Profile"]
        
        # Detect current state
        state = EmotionalState.NEUTRAL
        if profile.frustration_signals > profile.satisfaction_signals:
            state = EmotionalState.FRUSTRATED
        elif profile.satisfaction_signals > 3:
            state = EmotionalState.SATISFIED
        
        lines.append(f"**Detected State**: {state.value}")
        lines.append(f"**Recommended Tone**: {profile.get_recommended_tone().value}")
        
        lines.append("\n### Signals")
        lines.append(f"- Frustration signals: {profile.frustration_signals}")
        lines.append(f"- Satisfaction signals: {profile.satisfaction_signals}")
        lines.append(f"- Confusion signals: {profile.confusion_signals}")
        
        lines.append("\n### Task History")
        lines.append(f"- Successful: {profile.successful_tasks}")
        lines.append(f"- Failed: {profile.failed_tasks}")
        
        return "\n".join(lines)


# === Singleton ===

_engine: EmpathyEngine | None = None


def get_empathy_engine() -> EmpathyEngine:
    global _engine
    if _engine is None:
        _engine = EmpathyEngine()
    return _engine


# === Convenience ===

def adapt_response(
    message: str,
    user_id: str,
    messages: list[dict],
) -> str:
    """Adapt message to user's emotional state."""
    return get_empathy_engine().adapt_to_state(message, user_id, messages)


def detect_emotion(messages: list[dict]) -> EmotionalState:
    """Quick emotion detection from messages."""
    profile = UserEmotionProfile(user_id="temp")
    return profile.detect_state(messages)


def get_supportive_message(
    state: EmotionalState,
    base_message: str,
) -> str:
    """Get state-adaptive message."""
    engine = get_empathy_engine()
    
    # Get context
    messages = [{"content": base_message}]
    
    # Add state-aware prefix
    if state == EmotionalState.FRUSTRATED:
        prefix = engine.TEMPLATES[EmotionalState.FRUSTRATED]["start"][0]
    elif state == EmotionalState.CONFUSED:
        prefix = engine.TEMPLATES[EmotionalState.CONFUSED]["start"][0]
    elif state == EmotionalState.WORRIED:
        prefix = engine.TEMPLATES[EmotionalState.WORRIED]["reassure"][0]
    else:
        prefix = ""
    
    if prefix:
        return f"{prefix}\n\n{base_message}"
    
    return base_message