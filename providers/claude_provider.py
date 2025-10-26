"""
Anthropic Claude Provider Implementation

Provides access to Claude models (Claude 3.5 Haiku, Sonnet, Opus)
"""

from typing import Optional
try:
    import anthropic
except ImportError:
    anthropic = None

from .base_provider import (
    BaseAIProvider,
    CompletionRequest,
    CompletionResponse,
    ProviderError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError
)


class ClaudeProvider(BaseAIProvider):
    """
    Anthropic Claude provider

    Supports:
    - Claude 3.5 Haiku (claude-3-5-haiku-20241022) - RECOMMENDED for cost savings
    - Claude 3.5 Sonnet (claude-3-5-sonnet-20241022)
    - Claude 3 Opus (claude-3-opus-20240229)

    Pricing (October 2025, per 1M tokens):
    - Haiku: $0.80 input / $4.00 output (74% cheaper than GPT-4 Turbo)
    - Sonnet: $3.00 input / $15.00 output
    - Opus: $15.00 input / $75.00 output

    Features:
    - Extremely cost-effective (Haiku)
    - High quality outputs
    - Fast response times
    """

    # Pricing as of October 2025 (per 1K tokens)
    PRICING = {
        "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    }

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        max_tokens: int = 4096
    ):
        """
        Initialize Claude provider

        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-3-5-haiku-20241022)
            max_tokens: Maximum tokens in response (default: 4096)
        """
        if anthropic is None:
            raise ImportError(
                "The 'anthropic' package is required for Claude provider. "
                "Install it with: pip install anthropic"
            )

        super().__init__(api_key, model)
        self.client = anthropic.Anthropic(api_key=api_key)
        self.default_max_tokens = max_tokens

    def generate_completion(self, request: CompletionRequest) -> CompletionResponse:
        """
        Generate completion using Claude API

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
        try:
            # Build message
            message_content = request.prompt
            if request.system_prompt:
                # Claude uses system parameter separately
                system = request.system_prompt
            else:
                system = None

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=min(request.max_tokens, self.default_max_tokens),
                temperature=request.temperature,
                system=system,
                messages=[
                    {"role": "user", "content": message_content}
                ]
            )

            # Extract response
            content = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            # Calculate cost
            cost = self._calculate_cost(input_tokens, output_tokens)

            return CompletionResponse(
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                model=self.model,
                provider=self.get_name()
            )

        except anthropic.AuthenticationError as e:
            raise ProviderAuthError(f"Authentication failed: {e}")
        except anthropic.RateLimitError as e:
            raise ProviderRateLimitError(f"Rate limit exceeded: {e}")
        except anthropic.APITimeoutError as e:
            raise ProviderTimeoutError(f"Request timeout: {e}")
        except Exception as e:
            raise ProviderError(f"Claude API error: {e}")

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for token counts

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        pricing = self.PRICING.get(self.model, self.PRICING["claude-3-5-haiku-20241022"])
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost

    def get_name(self) -> str:
        """Return provider display name"""
        model_name = self.model.replace("claude-3-5-", "").replace("claude-3-", "").split("-")[0].title()
        return f"Claude 3.5 {model_name}"

    def get_default_model(self) -> str:
        """Return default model (Claude 3.5 Haiku - most cost-effective)"""
        return "claude-3-5-haiku-20241022"

    def get_cost_per_1k_input(self) -> float:
        """Return cost per 1K input tokens for current model"""
        return self.PRICING.get(self.model, self.PRICING["claude-3-5-haiku-20241022"])["input"]

    def get_cost_per_1k_output(self) -> float:
        """Return cost per 1K output tokens for current model"""
        return self.PRICING.get(self.model, self.PRICING["claude-3-5-haiku-20241022"])["output"]

    @staticmethod
    def get_haiku_model() -> str:
        """Return Haiku model (cheapest, fastest)"""
        return "claude-3-5-haiku-20241022"

    @staticmethod
    def get_sonnet_model() -> str:
        """Return Sonnet model (balanced)"""
        return "claude-3-5-sonnet-20241022"

    @staticmethod
    def get_opus_model() -> str:
        """Return Opus model (most powerful)"""
        return "claude-3-opus-20240229"

    def get_cost_comparison_vs_gpt4(self) -> dict:
        """
        Get cost comparison vs GPT-4 Turbo

        Returns:
            Dict with comparison metrics
        """
        gpt4_input_cost = 0.01  # $0.01 per 1K tokens
        gpt4_output_cost = 0.03  # $0.03 per 1K tokens

        claude_input_cost = self.get_cost_per_1k_input()
        claude_output_cost = self.get_cost_per_1k_output()

        # Calculate savings percentage
        input_savings = ((gpt4_input_cost - claude_input_cost) / gpt4_input_cost) * 100
        output_savings = ((gpt4_output_cost - claude_output_cost) / gpt4_output_cost) * 100
        avg_savings = (input_savings + output_savings) / 2

        return {
            "gpt4_input": gpt4_input_cost,
            "gpt4_output": gpt4_output_cost,
            "claude_input": claude_input_cost,
            "claude_output": claude_output_cost,
            "input_savings_pct": input_savings,
            "output_savings_pct": output_savings,
            "avg_savings_pct": avg_savings,
        }
