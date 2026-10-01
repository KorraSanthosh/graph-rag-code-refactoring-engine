import logging
from typing import Optional
from openai import APIConnectionError, APIStatusError, OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Senior Software Engineer specializing in Python code refactoring.

Rules you MUST follow:
1. Preserve the EXACT function signatures (name, parameters, return type)
2. Preserve the EXACT return values and semantics
3. Do NOT add new imports that are not in the original code
4. Do NOT rename functions or change public interfaces
5. Focus on: reducing complexity, improving readability, removing redundancy
6. Return ONLY the complete refactored code inside a ```python block. No explanations."""


def build_refactor_prompt(
    original_code: str,
    graph_context: str,
    target_function: str,
    error_log: Optional[str] = None,
    complexity_before: Optional[float] = None,
) -> list[dict]:
    """Builds a structured, versioned prompt for LLM refactoring."""
    complexity_hint = (
        f"Current cyclomatic complexity: {complexity_before:.1f} (lower is better)."
        if complexity_before
        else ""
    )

    user_content = f"""Refactor the function `{target_function}` in the code below.

### Dependency Graph Context:
{graph_context}

### {complexity_hint}

### Original Code:
```python
{original_code}
```
"""
    if error_log:
        user_content += f"\n### ⚠️ Previous Attempt Failed — Fix This Error:\n```\n{error_log}\n```"

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


class LLMEngine:
    """Handles communication with the LLM for code refactoring."""

    def __init__(
        self,
        client: OpenAI,
        model: str = "gpt-4o",
        temperature: float = 0.2,
        fallback_models: Optional[list[str]] = None,
    ):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.fallback_models = fallback_models or []

    def get_refactored_code(
        self,
        original_code: str,
        graph_context: str,
        target_function: str,
        error_log: Optional[str] = None,
        complexity_before: Optional[float] = None,
    ) -> str:
        """
        Sends code + graph context to the LLM.
        Returns extracted Python code string, or raises on failure.
        """
        messages = build_refactor_prompt(
            original_code, graph_context, target_function, error_log, complexity_before
        )
        last_error: Exception | None = None
        for model in [self.model, *self.fallback_models]:
            logger.info(f"Sending refactor request to {model} (temp={self.temperature})")
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=self.temperature,
                )
            except (APIStatusError, APIConnectionError) as e:
                # Overload / rate-limit / outage: try the next model instead of failing.
                status = getattr(e, "status_code", None)
                if status is not None and status not in (408, 409, 429) and status < 500:
                    raise
                logger.warning(f"Model {model} unavailable ({status}); trying next fallback.")
                last_error = e
                continue
            content = response.choices[0].message.content or ""
            return self._extract_code(content)
        raise last_error  # type: ignore[misc]

    def _extract_code(self, content: str) -> str:
        """Extracts Python code from a markdown code block."""
        if "```python" in content:
            return content.split("```python")[1].split("```")[0].strip()
        if "```" in content:
            return content.split("```")[1].split("```")[0].strip()
        return content.strip()
