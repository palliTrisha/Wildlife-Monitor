import os
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv()


class AIBackend(ABC):
    @abstractmethod
    def complete(self, prompt: str, system: str = "") -> str:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        ...


class AnthropicBackend(AIBackend):
    MODEL = "claude-sonnet-4-6"
    MAX_TOKENS = 1024

    def __init__(self):
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY not found in environment.")
        self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def name(self) -> str:
        return "Anthropic (Claude)"

    @property
    def is_available(self) -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY"))

    def complete(self, prompt: str, system: str = "") -> str:
        kwargs = {
            "model": self.MODEL,
            "max_tokens": self.MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        message = self._client.messages.create(**kwargs)
        return message.content[0].text


class OllamaBackend(AIBackend):
    DEFAULT_MODEL = "llama3"
    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(self):
        self._model = os.getenv("OLLAMA_MODEL", self.DEFAULT_MODEL)
        self._base_url = os.getenv("OLLAMA_BASE_URL", self.DEFAULT_BASE_URL)

    @property
    def name(self) -> str:
        return f"Ollama ({self._model})"

    @property
    def is_available(self) -> bool:
        try:
            import urllib.request
            urllib.request.urlopen(f"{self._base_url}/api/tags", timeout=2)
            return True
        except Exception:
            return False

    def complete(self, prompt: str, system: str = "") -> str:
        import json
        import urllib.request

        payload = {
            "model": self._model,
            "prompt": f"{system}\n\n{prompt}" if system else prompt,
            "stream": False,
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result.get("response", "")


class MockBackend(AIBackend):
    @property
    def name(self) -> str:
        return "Mock (no AI key)"

    @property
    def is_available(self) -> bool:
        return True

    def complete(self, prompt: str, system: str = "") -> str:
        return (
            "⚠️ **AI backend not configured.** "
            "Add `ANTHROPIC_API_KEY` to your `.env` file or start Ollama locally.\n\n"
            "_This is a placeholder response from MockBackend._"
        )


def get_backend(prefer: str | None = None) -> AIBackend:
    choice = prefer or os.getenv("AI_BACKEND", "auto")

    if choice == "anthropic":
        return AnthropicBackend()
    if choice == "ollama":
        return OllamaBackend()
    if choice == "mock":
        return MockBackend()

    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return AnthropicBackend()
        except Exception:
            pass

    ollama = OllamaBackend()
    if ollama.is_available:
        return ollama

    return MockBackend()