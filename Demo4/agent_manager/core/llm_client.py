"""
Async LLM client with structured JSON output enforcement.

This module provides a unified interface for LLM interactions with
strict Pydantic model enforcement, retry logic, and error handling
for reliable agent operations.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

import httpx
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)


class LLMConfig:
    """LLM client configuration with environment-based settings."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gpt-4")
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2000"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        self.base_url = "https://api.openai.com/v1"
        self.timeout = 60.0
        self.max_retries = 3
        self.retry_delay = 1.0
    
    def validate(self) -> bool:
        """Validate that all required configuration is present."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        return True


class LLMError(Exception):
    """Base exception for LLM client errors."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""
    pass


class LLMValidationError(LLMError):
    """Raised when LLM output fails Pydantic validation."""
    pass


class LLMClient:
    """
    Async LLM client with structured JSON output enforcement.
    
    Provides reliable LLM interactions with automatic retry logic,
    error handling, and strict Pydantic model validation for
    consistent agent operations.
    
    Go/No-Go Checkpoint: LLM calls reliably return structured Python objects
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM client with configuration."""
        self.config = config or LLMConfig()
        self.config.validate()
        
        # HTTP client for API requests
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    async def cleanup(self):
        """Clean up HTTP client resources."""
        await self.client.aclose()
    
    async def run_prompt_for_json(
        self,
        system_prompt: str,
        user_input: str,
        json_schema: Optional[Type[T]] = None,
        max_retries: Optional[int] = None,
    ) -> Union[str, T]:
        """
        Run a prompt and enforce JSON output with optional Pydantic validation.
        
        Args:
            system_prompt: System prompt defining agent behavior
            user_input: User input or task description
            json_schema: Optional Pydantic model for output validation
            max_retries: Override default retry count
            
        Returns:
            Union[str, T]: Raw JSON string or validated Pydantic model
            
        Raises:
            LLMError: If request fails after retries
            LLMValidationError: If output fails Pydantic validation
            LLMTimeoutError: If request times out
        """
        retries = max_retries or self.config.max_retries
        
        # Construct messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        # Add JSON format instruction to system prompt if schema provided
        if json_schema:
            json_instruction = f"\n\nIMPORTANT: You must respond with valid JSON that matches this schema: {json_schema.model_json_schema()}"
            messages[0]["content"] += json_instruction
        
        for attempt in range(retries + 1):
            try:
                # Make API request
                response = await self._make_api_request(messages)
                
                # Extract content
                content = response["choices"][0]["message"]["content"].strip()
                
                # If no schema validation required, return raw content
                if not json_schema:
                    return content
                
                # Parse and validate JSON
                try:
                    json_data = json.loads(content)
                    validated_model = json_schema.model_validate(json_data)
                    return validated_model
                    
                except (json.JSONDecodeError, ValidationError) as e:
                    if attempt < retries:
                        # Add clarification for retry
                        retry_message = f"The previous response was not valid JSON or did not match the required schema. Error: {str(e)}. Please provide a valid JSON response matching the schema."
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "user", "content": retry_message})
                        
                        await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                        continue
                    else:
                        raise LLMValidationError(f"Failed to parse/validate JSON after {retries} retries: {str(e)}")
            
            except httpx.TimeoutException:
                if attempt < retries:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                else:
                    raise LLMTimeoutError(f"Request timed out after {retries} retries")
            
            except httpx.HTTPStatusError as e:
                if attempt < retries and e.response.status_code >= 500:
                    # Retry on server errors
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                else:
                    raise LLMError(f"HTTP error {e.response.status_code}: {e.response.text}")
            
            except Exception as e:
                if attempt < retries:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                else:
                    raise LLMError(f"Unexpected error: {str(e)}")
        
        raise LLMError("Maximum retries exceeded")
    
    async def _make_api_request(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Make API request to OpenAI.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Dict: API response data
            
        Raises:
            httpx.HTTPStatusError: If API returns error status
            httpx.TimeoutException: If request times out
        """
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "response_format": {"type": "json_object"} if self._supports_json_mode() else None
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        response = await self.client.post(
            f"{self.config.base_url}/chat/completions",
            json=payload
        )
        
        response.raise_for_status()
        return response.json()
    
    def _supports_json_mode(self) -> bool:
        """Check if the current model supports JSON mode."""
        json_mode_models = ["gpt-4-1106-preview", "gpt-4-turbo-preview", "gpt-3.5-turbo-1106"]
        return any(model in self.config.model for model in json_mode_models)
    
    async def run_simple_prompt(self, prompt: str) -> str:
        """
        Run a simple prompt without JSON enforcement.
        
        Args:
            prompt: Simple text prompt
            
        Returns:
            str: LLM response text
        """
        messages = [{"role": "user", "content": prompt}]
        response = await self._make_api_request(messages)
        return response["choices"][0]["message"]["content"].strip()
    
    async def test_connection(self) -> bool:
        """
        Test LLM client connection.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            response = await self.run_simple_prompt("Hello, respond with 'OK' if you can hear me.")
            return "OK" in response.upper()
        except Exception as e:
            print(f"LLM connection test failed: {e}")
            return False


# Global LLM client instance
_llm_client: Optional[LLMClient] = None


async def get_llm_client() -> LLMClient:
    """Get the global LLM client instance, creating it if necessary."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


async def cleanup_llm_client():
    """Clean up the global LLM client instance."""
    global _llm_client
    if _llm_client is not None:
        await _llm_client.cleanup()
        _llm_client = None


# Convenience functions for common operations
async def run_agent_prompt(
    system_prompt: str,
    user_input: str,
    response_model: Type[T]
) -> T:
    """
    Convenience function for agent operations with Pydantic validation.
    
    Args:
        system_prompt: Agent system prompt
        user_input: User input or task
        response_model: Pydantic model for response validation
        
    Returns:
        T: Validated Pydantic model instance
    """
    client = await get_llm_client()
    return await client.run_prompt_for_json(
        system_prompt=system_prompt,
        user_input=user_input,
        json_schema=response_model
    )