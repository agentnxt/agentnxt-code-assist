"""User authentication via OAuth - providers handle API key creation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GATEWAY = "gateway"


# OAuth configuration for each provider
OAUTH_CONFIGS = {
    Provider.OPENAI: {
        "auth_url": "https://chat.openai.com/auth",
        "token_url": "https://api.openai.com/v1/organizations",  # Will use client credentials
        "scopes": [],
        "id": "openai",
        "name": "OpenAI",
    },
    Provider.ANTHROPIC: {
        "auth_url": "https://auth.anthropic.com/",
        "token_url": "https://api.anthropic.com/v1/organizations",
        "scopes": [],
        "id": "anthropic", 
        "name": "Anthropic",
    },
    Provider.GOOGLE: {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/generative-language.retriever", "https://www.googleapis.com/auth/generative-language.tuning"],
        "id": "google",
        "name": "Google",
    },
}


@dataclass
class UserSession:
    """User authenticated with a provider via OAuth."""
    user_id: str
    provider: Provider
    access_token: str | None = None
    refresh_token: str | None = None
    api_key: str | None = None  # Provider-created API key
    expires_at: int | None = None


def get_oauth_config(provider: Provider) -> dict[str, Any]:
    """Get OAuth configuration for a provider."""
    return OAUTH_CONFIGS.get(provider, {})


def get_provider_login_url(provider: Provider, redirect_uri: str) -> str:
    """Get the login URL for a provider.
    
    In production, this would initiate OAuth flow. For now, returns the provider's auth page.
    """
    if provider == Provider.OPENAI:
        return f"https://chat.openai.com/?oauth_callback={redirect_uri}"
    elif provider == Provider.ANTHROPIC:
        return f"https://auth.anthropic.com/?oauth_callback={redirect_uri}"
    elif provider == Provider.GOOGLE:
        scope = OAUTH_CONFIGS[Provider.GOOGLE]["scopes"]
        return f"https://accounts.google.com/o/oauth2/v2/auth?redirect_uri={redirect_uri}&scope={'+'.join(scope)}&response_type=code&client_id="
    elif provider == Provider.GATEWAY:
        return "/auth/gateway"
    return "#"


DEFAULT_MODELS = {
    Provider.OPENAI: ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
    Provider.ANTHROPIC: ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    Provider.GOOGLE: ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"],
    Provider.GATEWAY: ["gpt-4o", "gpt-4", "claude-3-opus"],
}


def get_available_models(provider: Provider) -> list[str]:
    """Get available models for a provider."""
    return DEFAULT_MODELS.get(provider, [])


def parse_provider(provider: str) -> Provider:
    """Parse provider string to Provider enum."""
    normalized = provider.lower().strip().replace("_", "-")
    try:
        return Provider(normalized)
    except ValueError:
        valid = [p.value for p in Provider]
        raise ValueError(f"Invalid provider: {provider}. Valid: {valid}")