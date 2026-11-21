import time
from typing import List, Dict, Any, Optional, Tuple
import litellm
from litellm.caching.caching import Cache, LiteLLMCacheType
from app.config import settings

# Disable remote model cost map lookup when network/sandbox is restricted
litellm.suppress_debug_info = True
litellm.set_verbose = False

# Initialize LiteLLM built-in cache
# max_messages=None ensures conversations with any number of turns are cached
_cache_instance = Cache(type="local", max_messages=None)
litellm.cache = _cache_instance


class CacheService:
    def __init__(self):
        self.cache = _cache_instance

    def is_enabled(self) -> bool:
        return self.cache is not None

    def get(self, model: str, messages: List[Dict[str, str]]) -> Optional[Tuple[str, int, int]]:
        """
        Check LiteLLM built-in cache for a previously stored response.
        Returns (reply_content, input_tokens, output_tokens) if found, else None.
        """
        try:
            cached = self.cache.get_cache(model=model, messages=messages)
            if cached is None:
                return None

            # Parse cached model response or dict
            reply_text = None
            input_tokens = 0
            output_tokens = 0

            # LiteLLM cache returns ModelResponse or dict
            if hasattr(cached, "choices") and cached.choices:
                reply_text = cached.choices[0].message.content
                if hasattr(cached, "usage") and cached.usage:
                    input_tokens = getattr(cached.usage, "prompt_tokens", 0) or 0
                    output_tokens = getattr(cached.usage, "completion_tokens", 0) or 0
            elif isinstance(cached, dict):
                choices = cached.get("choices", [])
                if choices:
                    first_choice = choices[0]
                    if isinstance(first_choice, dict):
                        reply_text = first_choice.get("message", {}).get("content", "")
                usage = cached.get("usage", {})
                if isinstance(usage, dict):
                    input_tokens = usage.get("prompt_tokens", 0) or 0
                    output_tokens = usage.get("completion_tokens", 0) or 0

            if reply_text is not None:
                return reply_text, int(input_tokens), int(output_tokens)
            return None
        except Exception:
            return None

    def set(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response_obj: Any
    ) -> None:
        """Store the response object in LiteLLM cache."""
        try:
            self.cache.add_cache(response_obj, model=model, messages=messages)
        except Exception:
            pass


cache_service = CacheService()

