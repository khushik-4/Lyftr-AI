import time
import re
from typing import List, Dict, Any, Optional, Tuple
import litellm
from litellm.exceptions import (
    RateLimitError,
    BudgetExceededError,
    APIError,
    APIConnectionError,
    Timeout,
    ServiceUnavailableError,
    InternalServerError,
    BadGatewayError,
)
from app.config import settings
from app.cache_service import cache_service
from app.exceptions import AllProvidersUnavailableException
from app.schemas import AssistantMetadata


class LLMService:
    def __init__(self):
        self.settings = settings

    def _parse_simulate_failure_header(self, header_value: Optional[str]) -> Dict[str, int]:
        """
        Parse X-Simulate-Failure header value.
        Supported formats: 'key_1=429', 'key_1=429,key_2=500', '*=429'
        Supported statuses: 429, 500, 502, 503
        """
        if not header_value or not self.settings.ENABLE_FAILURE_SIMULATION:
            return {}

        simulations: Dict[str, int] = {}
        valid_statuses = {429, 500, 502, 503}

        pairs = header_value.split(",")
        for pair in pairs:
            pair = pair.strip()
            if not pair or "=" not in pair:
                continue
            key_id, status_str = pair.split("=", 1)
            key_id = key_id.strip()
            status_str = status_str.strip()
            if status_str.isdigit():
                code = int(status_str)
                if code in valid_statuses:
                    simulations[key_id] = code
        return simulations

    def _count_fallback_tokens(self, model: str, messages: List[Dict[str, str]], reply: str) -> Tuple[int, int]:
        """Documented fallback token counter using litellm.token_counter or character approximation."""
        try:
            input_tokens = litellm.token_counter(model=model, messages=messages)
        except Exception:
            prompt_text = " ".join([m.get("content", "") for m in messages])
            input_tokens = max(1, len(prompt_text) // 4)

        try:
            output_tokens = litellm.token_counter(model=model, text=reply)
        except Exception:
            output_tokens = max(1, len(reply) // 4)

        return int(input_tokens), int(output_tokens)

    def _is_retryable_error(self, err: Exception) -> bool:
        """Determine if an exception is an eligible transient error for key failover."""
        # Check standard LiteLLM error types
        if isinstance(
            err,
            (
                RateLimitError,
                BudgetExceededError,
                ServiceUnavailableError,
                InternalServerError,
                BadGatewayError,
                APIConnectionError,
                Timeout,
            ),
        ):
            return True

        if isinstance(err, APIError):
            status_code = getattr(err, "status_code", None)
            if status_code in (429, 500, 502, 503):
                return True

        # Check status_code attribute on any exception
        status_code = getattr(err, "status_code", None)
        if status_code in (429, 500, 502, 503):
            return True

        # Check error message keywords
        err_str = str(err).lower()
        if any(keyword in err_str for keyword in ("429", "rate limit", "quota", "500", "502", "503", "overloaded")):
            return True

        return False

    async def execute_chat(
        self,
        messages: List[Dict[str, str]],
        simulate_failure_header: Optional[str] = None
    ) -> Tuple[str, AssistantMetadata]:
        """
        Execute chat completion with caching and sequential failover.
        Returns (reply_text, metadata).
        """
        model = self.settings.LLM_MODEL
        parsed_simulations = self._parse_simulate_failure_header(simulate_failure_header)
        has_simulated_failure = len(parsed_simulations) > 0

        # Step 1: Check cache only if NO failure simulation is requested
        if not has_simulated_failure and cache_service.is_enabled():
            start_lookup = time.perf_counter()
            cached_result = cache_service.get(model=model, messages=messages)
            if cached_result is not None:
                lookup_latency_ms = max(1, int((time.perf_counter() - start_lookup) * 1000))
                reply_text, input_tokens, output_tokens = cached_result
                metadata = AssistantMetadata(
                    resolution_source="LLM_CACHE",
                    model=model,
                    latency_ms=lookup_latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    key_id=None,
                    fallback_attempts=0
                )
                return reply_text, metadata

        # Step 2: Sequential failover across key pool
        key_pool = self.settings.get_parsed_keys()
        fallback_attempts = 0
        last_exception = None

        start_inference = time.perf_counter()

        for key_info in key_pool:
            key_id = key_info["id"]
            api_key = key_info["key"]

            # Check simulated failure for this key or wildcard '*'
            simulated_code = parsed_simulations.get(key_id) or parsed_simulations.get("*")
            if simulated_code is not None:
                # Simulate the error without modifying keys
                fallback_attempts += 1
                last_exception = Exception(f"Simulated error {simulated_code}")
                continue

            # Live provider call using LiteLLM
            try:
                # Call litellm.completion
                response = litellm.completion(
                    model=model,
                    messages=messages,
                    api_key=api_key,
                    timeout=30.0
                )

                latency_ms = max(1, int((time.perf_counter() - start_inference) * 1000))
                reply_text = response.choices[0].message.content or ""

                # Extract token usage
                input_tokens = None
                output_tokens = None
                if hasattr(response, "usage") and response.usage:
                    input_tokens = getattr(response.usage, "prompt_tokens", None)
                    output_tokens = getattr(response.usage, "completion_tokens", None)

                if input_tokens is None or output_tokens is None:
                    calc_in, calc_out = self._count_fallback_tokens(model, messages, reply_text)
                    input_tokens = input_tokens if input_tokens is not None else calc_in
                    output_tokens = output_tokens if output_tokens is not None else calc_out

                # Save response to LiteLLM cache for subsequent identical requests
                cache_service.set(model=model, messages=messages, response_obj=response)

                metadata = AssistantMetadata(
                    resolution_source="LIVE_INFERENCE",
                    model=model,
                    latency_ms=latency_ms,
                    input_tokens=int(input_tokens),
                    output_tokens=int(output_tokens),
                    key_id=key_id,
                    fallback_attempts=fallback_attempts
                )
                return reply_text, metadata

            except Exception as e:
                last_exception = e
                if self._is_retryable_error(e):
                    fallback_attempts += 1
                    continue
                else:
                    # Non-retryable error, check next key as well or break
                    fallback_attempts += 1
                    continue

        # If all keys exhausted
        raise AllProvidersUnavailableException("all providers unavailable")


llm_service = LLMService()
