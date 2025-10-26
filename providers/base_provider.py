"""
Base Provider Interface

Abstract base class for AI providers (OpenAI, Claude, Gemini, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class CompletionRequest:
    """Request for AI completion"""
    prompt: str
    max_tokens: int = 2000
    temperature: float = 0.2
    system_prompt: Optional[str] = None


@dataclass
class CompletionResponse:
    """Response from AI completion"""
    content: str
    input_tokens: int
    output_tokens: int
    cost: float
    model: str
    provider: str


class BaseAIProvider(ABC):
    """
    Abstract base class for AI providers

    Implementations must provide:
    - generate_completion(): Core completion functionality
    - get_name(): Provider display name
    - get_cost_per_1k_input(): Input token pricing
    - get_cost_per_1k_output(): Output token pricing
    """

    def __init__(self, api_key: str, model: Optional[str] = None):
        """
        Initialize provider

        Args:
            api_key: API key for the provider
            model: Optional model override (uses default if not specified)
        """
        self.api_key = api_key
        self.model = model or self.get_default_model()

    @abstractmethod
    def generate_completion(self, request: CompletionRequest) -> CompletionResponse:
        """
        Generate completion from prompt

        Args:
            request: Completion request with prompt and parameters

        Returns:
            CompletionResponse with generated content and metadata

        Raises:
            ProviderError: If completion fails
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Return provider display name

        Returns:
            Provider name (e.g., 'OpenAI GPT-4 Turbo')
        """
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """
        Return default model name

        Returns:
            Model identifier (e.g., 'gpt-4-turbo-preview')
        """
        pass

    @abstractmethod
    def get_cost_per_1k_input(self) -> float:
        """
        Return cost per 1K input tokens

        Returns:
            Cost in USD (e.g., 0.01 for $0.01/1K tokens)
        """
        pass

    @abstractmethod
    def get_cost_per_1k_output(self) -> float:
        """
        Return cost per 1K output tokens

        Returns:
            Cost in USD (e.g., 0.03 for $0.03/1K tokens)
        """
        pass

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for token counts

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        input_cost = (input_tokens / 1000) * self.get_cost_per_1k_input()
        output_cost = (output_tokens / 1000) * self.get_cost_per_1k_output()
        return input_cost + output_cost

    def get_cost_summary(self) -> str:
        """
        Get human-readable cost summary

        Returns:
            Formatted cost string (e.g., "$0.01/$0.03 per 1K tokens")
        """
        input_cost = self.get_cost_per_1k_input()
        output_cost = self.get_cost_per_1k_output()
        return f"${input_cost:.4f}/${output_cost:.4f} per 1K tokens"


class ProviderError(Exception):
    """Base exception for provider errors"""
    pass


class ProviderAuthError(ProviderError):
    """Authentication/API key error"""
    pass


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded"""
    pass


class ProviderTimeoutError(ProviderError):
    """Request timeout"""
    pass
