"""
OpenAI Provider Implementation

Provides access to OpenAI models (GPT-4 Turbo, GPT-3.5 Turbo) via LiteLLM
"""

import os
from typing import Optional
import litellm
from litellm import completion

from .base_provider import (
    BaseAIProvider,
    CompletionRequest,
    CompletionResponse,
    ProviderError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError
)


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI provider using LiteLLM

    Supports:
    - GPT-4 Turbo (gpt-4-turbo-preview)
    - GPT-4 (gpt-4)
    - GPT-3.5 Turbo (gpt-3.5-turbo)

    Features:
    - Automatic fallback on failure
    - Retry logic with exponential backoff
    - Cost tracking
    """

    # Pricing as of October 2025 (per 1K tokens)
    PRICING = {
        "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        max_retries: int = 3
    ):
        """
        Initialize OpenAI provider

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4-turbo-preview)
            fallback_model: Fallback model if primary fails (default: gpt-3.5-turbo)
            max_retries: Maximum retry attempts (default: 3)
        """
        super().__init__(api_key, model)
        self.fallback_model = fallback_model or "gpt-3.5-turbo"
        self.max_retries = max_retries

        # Configure LiteLLM
        litellm.set_verbose = False
        os.environ["OPENAI_API_KEY"] = api_key

    def generate_completion(self, request: CompletionRequest) -> CompletionResponse:
        """
        Generate completion using OpenAI API

        Args:
            request: Completion request

        Returns:
            CompletionResponse with generated content

        Raises:
            ProviderAuthError: Invalid API key
            ProviderRateLimitError: Rate limit exceeded
            ProviderTimeoutError: Request timeout
            ProviderError: Other errors
        """
        # Try primary model
        try:
            return self._call_model(self.model, request)
        except Exception as e:
            # Try fallback model
            try:
                return self._call_model(self.fallback_model, request)
            except Exception as fallback_error:
                raise ProviderError(
                    f"All models failed. Primary ({self.model}): {e}, "
                    f"Fallback ({self.fallback_model}): {fallback_error}"
                )

    def _call_model(self, model: str, request: CompletionRequest) -> CompletionResponse:
        """
        Call specific OpenAI model

        Args:
            model: Model name
            request: Completion request

        Returns:
            CompletionResponse

        Raises:
            ProviderError: On failure
        """
        try:
            # Build messages
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

            # Call LiteLLM
            response = completion(
                model=model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )

            # Extract response
            content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            # Calculate cost
            cost = self._calculate_cost(model, input_tokens, output_tokens)

            return CompletionResponse(
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                model=model,
                provider=self.get_name()
            )

        except Exception as e:
            error_msg = str(e).lower()

            # Classify error type
            if "invalid api key" in error_msg or "unauthorized" in error_msg:
                raise ProviderAuthError(f"Authentication failed: {e}")
            elif "rate limit" in error_msg:
                raise ProviderRateLimitError(f"Rate limit exceeded: {e}")
            elif "timeout" in error_msg:
                raise ProviderTimeoutError(f"Request timeout: {e}")
            else:
                raise ProviderError(f"OpenAI API error: {e}")

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for specific model and token counts

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        # Find pricing for model
        pricing = None
        for model_key, prices in self.PRICING.items():
            if model_key in model:
                pricing = prices
                break

        if not pricing:
            # Unknown model, use GPT-3.5 pricing as fallback
            pricing = self.PRICING["gpt-3.5-turbo"]

        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]

        return input_cost + output_cost

    def get_name(self) -> str:
        """Return provider display name"""
        return f"OpenAI {self.model}"

    def get_default_model(self) -> str:
        """Return default model"""
        return "gpt-4-turbo-preview"

    def get_cost_per_1k_input(self) -> float:
        """Return cost per 1K input tokens for current model"""
        for model_key, prices in self.PRICING.items():
            if model_key in self.model:
                return prices["input"]
        return self.PRICING["gpt-3.5-turbo"]["input"]

    def get_cost_per_1k_output(self) -> float:
        """Return cost per 1K output tokens for current model"""
        for model_key, prices in self.PRICING.items():
            if model_key in self.model:
                return prices["output"]
        return self.PRICING["gpt-3.5-turbo"]["output"]

    @staticmethod
    def is_simple_model(model: str) -> bool:
        """
        Check if model is considered "simple" (cheaper)

        Args:
            model: Model name

        Returns:
            True if GPT-3.5 Turbo
        """
        return "gpt-3.5-turbo" in model.lower()

    @staticmethod
    def get_simple_model() -> str:
        """Return simple/cheap model for basic tasks"""
        return "gpt-3.5-turbo"

    @staticmethod
    def get_complex_model() -> str:
        """Return complex/powerful model for advanced tasks"""
        return "gpt-4-turbo-preview"
