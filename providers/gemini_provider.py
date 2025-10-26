"""
Google Gemini Provider Implementation

Provides access to Gemini models (Gemini 2.0 Flash, Gemini 1.5 Pro)
"""

from typing import Optional
try:
    import google.generativeai as genai
except ImportError:
    genai = None

from .base_provider import (
    BaseAIProvider,
    CompletionRequest,
    CompletionResponse,
    ProviderError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError
)


class GeminiProvider(BaseAIProvider):
    """
    Google Gemini provider

    Supports:
    - Gemini 2.0 Flash (gemini-2.0-flash-exp) - RECOMMENDED for cost savings
    - Gemini 1.5 Pro (gemini-1.5-pro)
    - Gemini 1.5 Flash (gemini-1.5-flash)

    Pricing (October 2025, per 1M tokens):
    - 2.0 Flash: $0.10 input / $0.40 output (97% cheaper than GPT-4 Turbo!)
    - 1.5 Pro: $1.25 input / $5.00 output
    - 1.5 Flash: $0.075 input / $0.30 output

    Features:
    - EXTREMELY cost-effective (2.0 Flash)
    - Fast response times
    - Large context window (1M tokens)
    - Free tier available
    """

    # Pricing as of October 2025 (per 1K tokens)
    PRICING = {
        "gemini-2.0-flash-exp": {"input": 0.0001, "output": 0.0004},
        "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    }

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None
    ):
        """
        Initialize Gemini provider

        Args:
            api_key: Google API key
            model: Model to use (default: gemini-2.0-flash-exp)
        """
        if genai is None:
            raise ImportError(
                "The 'google-generativeai' package is required for Gemini provider. "
                "Install it with: pip install google-generativeai"
            )

        super().__init__(api_key, model)
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(self.model)

    def generate_completion(self, request: CompletionRequest) -> CompletionResponse:
        """
        Generate completion using Gemini API

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
            # Build prompt
            prompt = request.prompt
            if request.system_prompt:
                # Gemini doesn't have explicit system role, prepend to prompt
                prompt = f"{request.system_prompt}\n\n{prompt}"

            # Configure generation
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=request.max_tokens,
                temperature=request.temperature,
            )

            # Call Gemini API
            response = self.client.generate_content(
                prompt,
                generation_config=generation_config
            )

            # Extract response
            content = response.text

            # Get token counts
            # Note: Gemini API provides token counts in usage_metadata
            input_tokens = response.usage_metadata.prompt_token_count
            output_tokens = response.usage_metadata.candidates_token_count

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

        except Exception as e:
            error_msg = str(e).lower()

            # Classify error type
            if "api key" in error_msg or "unauthorized" in error_msg:
                raise ProviderAuthError(f"Authentication failed: {e}")
            elif "quota" in error_msg or "rate limit" in error_msg:
                raise ProviderRateLimitError(f"Rate limit exceeded: {e}")
            elif "timeout" in error_msg:
                raise ProviderTimeoutError(f"Request timeout: {e}")
            else:
                raise ProviderError(f"Gemini API error: {e}")

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for token counts

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        pricing = self.PRICING.get(self.model, self.PRICING["gemini-2.0-flash-exp"])
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost

    def get_name(self) -> str:
        """Return provider display name"""
        if "2.0" in self.model:
            return "Gemini 2.0 Flash"
        elif "1.5-pro" in self.model:
            return "Gemini 1.5 Pro"
        elif "1.5-flash" in self.model:
            return "Gemini 1.5 Flash"
        return f"Gemini {self.model}"

    def get_default_model(self) -> str:
        """Return default model (Gemini 2.0 Flash - most cost-effective)"""
        return "gemini-2.0-flash-exp"

    def get_cost_per_1k_input(self) -> float:
        """Return cost per 1K input tokens for current model"""
        return self.PRICING.get(self.model, self.PRICING["gemini-2.0-flash-exp"])["input"]

    def get_cost_per_1k_output(self) -> float:
        """Return cost per 1K output tokens for current model"""
        return self.PRICING.get(self.model, self.PRICING["gemini-2.0-flash-exp"])["output"]

    @staticmethod
    def get_flash_2_model() -> str:
        """Return Gemini 2.0 Flash model (cheapest!)"""
        return "gemini-2.0-flash-exp"

    @staticmethod
    def get_pro_model() -> str:
        """Return Gemini 1.5 Pro model (most powerful)"""
        return "gemini-1.5-pro"

    @staticmethod
    def get_flash_1_5_model() -> str:
        """Return Gemini 1.5 Flash model (balanced)"""
        return "gemini-1.5-flash"

    def get_cost_comparison_vs_gpt4(self) -> dict:
        """
        Get cost comparison vs GPT-4 Turbo

        Returns:
            Dict with comparison metrics
        """
        gpt4_input_cost = 0.01  # $0.01 per 1K tokens
        gpt4_output_cost = 0.03  # $0.03 per 1K tokens

        gemini_input_cost = self.get_cost_per_1k_input()
        gemini_output_cost = self.get_cost_per_1k_output()

        # Calculate savings percentage
        input_savings = ((gpt4_input_cost - gemini_input_cost) / gpt4_input_cost) * 100
        output_savings = ((gpt4_output_cost - gemini_output_cost) / gpt4_output_cost) * 100
        avg_savings = (input_savings + output_savings) / 2

        return {
            "gpt4_input": gpt4_input_cost,
            "gpt4_output": gpt4_output_cost,
            "gemini_input": gemini_input_cost,
            "gemini_output": gemini_output_cost,
            "input_savings_pct": input_savings,
            "output_savings_pct": output_savings,
            "avg_savings_pct": avg_savings,
        }

    def get_cost_comparison_vs_claude(self) -> dict:
        """
        Get cost comparison vs Claude 3.5 Haiku

        Returns:
            Dict with comparison metrics
        """
        claude_input_cost = 0.0008  # $0.0008 per 1K tokens
        claude_output_cost = 0.004   # $0.004 per 1K tokens

        gemini_input_cost = self.get_cost_per_1k_input()
        gemini_output_cost = self.get_cost_per_1k_output()

        # Calculate savings percentage
        input_savings = ((claude_input_cost - gemini_input_cost) / claude_input_cost) * 100
        output_savings = ((claude_output_cost - gemini_output_cost) / claude_output_cost) * 100
        avg_savings = (input_savings + output_savings) / 2

        return {
            "claude_input": claude_input_cost,
            "claude_output": claude_output_cost,
            "gemini_input": gemini_input_cost,
            "gemini_output": gemini_output_cost,
            "input_savings_pct": input_savings,
            "output_savings_pct": output_savings,
            "avg_savings_pct": avg_savings,
        }
