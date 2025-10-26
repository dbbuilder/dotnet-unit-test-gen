"""
Provider Factory

Simplifies creation and selection of AI providers
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path

from .base_provider import BaseAIProvider
from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider
from .gemini_provider import GeminiProvider


class ProviderFactory:
    """
    Factory for creating AI providers

    Supports:
    - Provider selection by name
    - Environment variable configuration
    - Cost comparison
    - Default provider fallback
    """

    PROVIDER_CLASSES = {
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "gemini": GeminiProvider,
    }

    @staticmethod
    def create_provider(
        provider_name: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseAIProvider:
        """
        Create AI provider by name

        Args:
            provider_name: Provider name (openai, claude, gemini)
            api_key: API key (if None, loads from environment)
            model: Optional model override
            **kwargs: Additional provider-specific arguments

        Returns:
            Initialized provider instance

        Raises:
            ValueError: If provider not found
            ImportError: If provider SDK not installed
        """
        provider_name = provider_name.lower()

        if provider_name not in ProviderFactory.PROVIDER_CLASSES:
            available = ", ".join(ProviderFactory.PROVIDER_CLASSES.keys())
            raise ValueError(
                f"Unknown provider '{provider_name}'. "
                f"Available providers: {available}"
            )

        # Get API key from environment if not provided
        if api_key is None:
            api_key = ProviderFactory._get_api_key_from_env(provider_name)

        # Get provider class
        provider_class = ProviderFactory.PROVIDER_CLASSES[provider_name]

        # Create provider instance
        return provider_class(api_key=api_key, model=model, **kwargs)

    @staticmethod
    def create_default_provider(model: Optional[str] = None) -> BaseAIProvider:
        """
        Create default provider from environment

        Checks DEFAULT_PROVIDER env var, falls back to OpenAI

        Args:
            model: Optional model override

        Returns:
            Initialized provider instance
        """
        provider_name = os.getenv("DEFAULT_PROVIDER", "openai")
        return ProviderFactory.create_provider(provider_name, model=model)

    @staticmethod
    def _get_api_key_from_env(provider_name: str) -> str:
        """
        Get API key from environment

        Args:
            provider_name: Provider name

        Returns:
            API key

        Raises:
            ValueError: If API key not found
        """
        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "gemini": "GOOGLE_API_KEY",
        }

        env_var = env_var_map.get(provider_name)
        if not env_var:
            raise ValueError(f"Unknown provider '{provider_name}'")

        api_key = os.getenv(env_var)
        if not api_key:
            raise ValueError(
                f"API key not found. Please set {env_var} environment variable."
            )

        return api_key

    @staticmethod
    def get_available_providers() -> list[str]:
        """
        Get list of available provider names

        Returns:
            List of provider names
        """
        return list(ProviderFactory.PROVIDER_CLASSES.keys())

    @staticmethod
    def get_cost_comparison(
        input_tokens: int = 100000,
        output_tokens: int = 50000
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare costs across all providers

        Args:
            input_tokens: Number of input tokens (default: 100K)
            output_tokens: Number of output tokens (default: 50K)

        Returns:
            Dict with provider costs and savings
        """
        results = {}

        for provider_name in ProviderFactory.get_available_providers():
            try:
                # Create provider with dummy key (just for cost calculation)
                provider = ProviderFactory.PROVIDER_CLASSES[provider_name](
                    api_key="dummy",
                    model=None  # Use default
                )

                cost = provider.estimate_cost(input_tokens, output_tokens)
                input_cost_per_1k = provider.get_cost_per_1k_input()
                output_cost_per_1k = provider.get_cost_per_1k_output()

                results[provider_name] = {
                    "name": provider.get_name(),
                    "model": provider.model,
                    "total_cost": cost,
                    "input_cost_per_1k": input_cost_per_1k,
                    "output_cost_per_1k": output_cost_per_1k,
                    "cost_summary": provider.get_cost_summary()
                }
            except ImportError:
                # Provider SDK not installed
                results[provider_name] = {
                    "name": provider_name.title(),
                    "error": "SDK not installed"
                }

        # Calculate savings vs OpenAI (baseline)
        if "openai" in results and "total_cost" in results["openai"]:
            baseline_cost = results["openai"]["total_cost"]

            for provider_name, data in results.items():
                if "total_cost" in data and provider_name != "openai":
                    savings = baseline_cost - data["total_cost"]
                    savings_pct = (savings / baseline_cost) * 100
                    data["savings_vs_openai"] = savings
                    data["savings_pct"] = savings_pct

        return results

    @staticmethod
    def print_cost_comparison(
        input_tokens: int = 100000,
        output_tokens: int = 50000
    ):
        """
        Print formatted cost comparison table

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        from rich.console import Console
        from rich.table import Table

        console = Console()
        comparison = ProviderFactory.get_cost_comparison(input_tokens, output_tokens)

        table = Table(title=f"Cost Comparison ({input_tokens/1000:.0f}K input, {output_tokens/1000:.0f}K output tokens)")

        table.add_column("Provider", style="cyan")
        table.add_column("Model", style="blue")
        table.add_column("Total Cost", justify="right", style="green")
        table.add_column("Input/1K", justify="right")
        table.add_column("Output/1K", justify="right")
        table.add_column("Savings", justify="right", style="yellow")

        for provider_name, data in comparison.items():
            if "error" in data:
                table.add_row(
                    data["name"],
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    data["error"]
                )
            else:
                savings = ""
                if "savings_pct" in data:
                    savings = f"{data['savings_pct']:.0f}% 💰"

                table.add_row(
                    data["name"],
                    data["model"],
                    f"${data['total_cost']:.4f}",
                    f"${data['input_cost_per_1k']:.4f}",
                    f"${data['output_cost_per_1k']:.4f}",
                    savings
                )

        console.print(table)

    @staticmethod
    def get_cheapest_provider() -> str:
        """
        Get name of cheapest provider

        Returns:
            Provider name with lowest cost
        """
        comparison = ProviderFactory.get_cost_comparison()

        cheapest = None
        lowest_cost = float('inf')

        for provider_name, data in comparison.items():
            if "total_cost" in data and data["total_cost"] < lowest_cost:
                lowest_cost = data["total_cost"]
                cheapest = provider_name

        return cheapest or "openai"
