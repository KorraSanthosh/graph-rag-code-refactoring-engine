import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMEngine:
    """Handles communication with the LLM for code refactoring."""
    def __init__(self):
        # Assumes OPENAI_API_KEY is in environment
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "your_key_here"))
        self.model = "gpt-4o" # Using a high-capability model for refactoring

    def get_refactored_code(self, original_code: str, context: str, error_log: str = None) -> str:
        """Sends code and graph context to LLM and retrieves refactored version."""
        
        prompt = f"""
You are a Senior Software Engineer. Refactor the following Python code.
### Context from Dependency Graph:
{context}

### Original Code:
{original_code}
"""
        if error_log:
            prompt += f"\n\n### Previous Error (Fix this):\n{error_log}"

        prompt += "\n\nReturn ONLY the refactored code inside a markdown code block. Do not explain anything."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.choices[0].message.content
            # Extract code from markdown block
            if "```python" in content:
                return content.split("```python")[1].split("```")[0].strip()
            elif "```" in content:
                return content.split("```")[1].split("```")[0].strip()
            return content.strip()
        except Exception as e:
            return f"Error calling LLM: {str(e)}"
