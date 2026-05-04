"""Local LLM fallback using llama.cpp - supports air-gapped/offline mode."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MODELS = {
    "llama3-8b": {
        "url": "https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama3-8b-instruct-q4_0.gguf",
        "filename": "llama3-8b-instruct-q4_0.gguf",
        "size": "4.9GB",
    },
    "mistral-7b": {
        "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-GGUF/resolve/main/mistral-7b-instruct-v0.2-q4_0.gguf",
        "filename": "mistral-7b-instruct-v0.2-q4_0.gguf",
        "size": "4.1GB",
    },
    "phi3-mini": {
        "url": "https://huggingface.co/TheBloke/Phi-3-mini-4k-instruct-GGUF/resolve/main/phi-3-mini-4k-instruct-q4_0.gguf",
        "filename": "phi-3-mini-4k-instruct-q4_0.gguf",
        "size": "2.3GB",
    },
}


def is_air_gapped() -> bool:
    """Check if we're in air-gapped (offline) mode.
    
    Looks for environment variable or tests network connectivity.
    """
    if os.getenv("AIR_GAPPED"):
        return True
    # Check if network is available
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=1)
        return False
    except (OSError, socket.timeout):
        return True


@dataclass
class LocalModel:
    name: str
    path: Path
    context_size: int = 4096
    threads: int = 4


def get_model_dir() -> Path:
    """Get the directory for storing local models."""
    model_dir = Path(os.getenv("AGENNEXT_MODEL_DIR", "/ srv/agennext/models"))
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir


def get_installed_models() -> list[str]:
    """List installed local models."""
    model_dir = get_model_dir()
    return [f.stem for f in model_dir.glob("*.gguf")]


async def download_model(model_id: str = "llama3-8b") -> Path:
    """Download a model from HuggingFace."""
    import httpx
    
    model_info = MODELS.get(model_id)
    if not model_info:
        raise ValueError(f"Unknown model: {model_id}. Available: {list(MODELS.keys())}")
    
    model_dir = get_model_dir()
    model_path = model_dir / model_info["filename"]
    
    if model_path.exists():
        return model_path
    
    print(f"Downloading {model_id} ({model_info['size']})...")
    print(f"This may take several minutes...")
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(model_info["url"], timeout=None)
        response.raise_for_status()
        
        with open(model_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)
    
    return model_path


def is_llama_cpp_installed() -> bool:
    """Check if llama.cpp is installed."""
    try:
        result = subprocess.run(
            ["llama-cli", "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Check common locations
    for path in ["/usr/local/bin", "/usr/bin", Path.home() / ".local/bin"]:
        if (path / "llama-cli").exists():
            return True
    return False


async def run_local_model(
    prompt: str,
    model: str = "llama3-8b",
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    """Run a local model using llama.cpp."""
    if not is_llama_cpp_installed():
        raise RuntimeError(
            "llama.cpp not installed. Install with: "
            "brew install llama.cpp  # macOS"
            "# or: sudo apt install llama.cpp  # Linux"
        )
    
    model_dir = get_model_dir()
    model_info = MODELS.get(model)
    model_path = model_dir / model_info["filename"]
    
    if not model_path.exists():
        print(f"Model not found. Downloading {model}...")
        model_path = await download_model(model)
    
    # Run llama.cpp
    result = subprocess.run(
        [
            "llama-cli",
            "-m", str(model_path),
            "-p", prompt,
            "-n", str(max_tokens),
            "--temp", str(temperature),
            "--no-mmap",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Local model error: {result.stderr}")
    
    return result.stdout


def get_fallback_instructions() -> str:
    """Get instructions for manual fallback setup."""
    return f"""To use local models when API limits are exhausted:

1. Install llama.cpp:
   # macOS
   brew install llama.cpp
   # Linux
   sudo apt install llama.cpp

2. Download a model:
   python -m agentnxt_code_assist download-model llama3-8b

3. The app will automatically use the local model when APIs are rate-limited."""


# Check and run fallback if needed
async def get_or_run_fallback(
    request: Any,
    primary_error: str | None = None,
) -> str | None:
    """Check if we should use fallback, and run if needed.
    
    Returns None if primary should be used, or the fallback output.
    """
    # Check for rate limit or quota errors
    rate_limit_indicators = [
        "rate_limit",
        "rate limit",
        "quota",
        "exceeded",
        "insufficient_quota",
        "billing",
        "429",
        "too many requests",
    ]
    
    if primary_error and any(ind in primary_error.lower() for ind in rate_limit_indicators):
        # Try to use local model
        try:
            return await run_local_model(
                request.instruction,
                max_tokens=2048,
            )
        except Exception as e:
            print(f"Fallback error: {e}")
            return None
    
    return None