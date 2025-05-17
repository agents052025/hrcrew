from typing import Optional, Dict, Any
from pydantic import BaseModel
import yaml
import os

class LLMConfig(BaseModel):
    """Configuration for Language Model settings"""
    provider: str = "openai"  # or "ollama"
    api_key: Optional[str] = None
    model_name: str = "gpt-3.5-turbo"  # or "llama2" for Ollama
    temperature: float = 0.7
    max_tokens: int = 2000
    server_url: Optional[str] = "http://localhost:11434"  # Only for Ollama
    agent_specific: Optional[Dict[str, Dict[str, Any]]] = None

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "LLMConfig":
        """Load configuration from a YAML file."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"YAML config file not found: {path}")
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        llm_data = data.get("llm", data)  # support both root or 'llm' key
        # Flatten OpenAI/Ollama keys if present
        provider = llm_data.get("provider", "openai")
        if provider == "openai" and "openai" in llm_data:
            llm_data.update(llm_data["openai"])
        elif provider == "ollama" and "ollama" in llm_data:
            llm_data.update(llm_data["ollama"])
        
        # Determine model name and prefix if necessary for ollama
        default_model_for_provider = "gpt-3.5-turbo" if provider == "openai" else "llama2"
        model_name_val = llm_data.get("model_name", default_model_for_provider)
        if provider == "ollama" and not str(model_name_val).startswith("ollama/"):
            model_name_val = f"ollama/{model_name_val}"

        agent_specific = llm_data.get("agent_specific", None)
        return cls(
            provider=provider,
            api_key=llm_data.get("api_key"),
            model_name=model_name_val,  # Use the potentially prefixed name
            temperature=llm_data.get("temperature", 0.7),
            max_tokens=llm_data.get("max_tokens", 2000),
            server_url=llm_data.get("server_url", "http://localhost:11434"),
            agent_specific=agent_specific
        )

    def for_agent(self, agent_name: str) -> "LLMConfig":
        """Return agent-specific config if available, else default."""
        config_data = self.model_dump()  # Start with current config as a dictionary

        agent_specific_configs = self.agent_specific
        if agent_specific_configs is not None: # Explicit None check
            if agent_name in agent_specific_configs: # Now agent_specific_configs is known to be a Dict
                overrides = agent_specific_configs[agent_name]
                config_data.update(overrides) # Apply overrides to the dictionary

        # Determine provider and model_name from the potentially updated config_data
        # Use .get() with fallback to original self attributes if keys are somehow missing after update (defensive)
        provider = config_data.get("provider", self.provider)
        model_name = config_data.get("model_name", self.model_name)

        if provider == "ollama" and not str(model_name).startswith("ollama/"):
            config_data["model_name"] = f"ollama/{model_name}" # Update the dictionary
            
        return LLMConfig(**config_data) # Create a new instance from the (potentially) modified dictionary

    def fallback(self, fallback_provider: str = "openai") -> "LLMConfig":
        """Return a fallback config (e.g., switch to OpenAI if Ollama fails)."""
        config_dict = self.model_dump()
        config_dict["provider"] = fallback_provider
        if fallback_provider == "openai":
            config_dict["model_name"] = "gpt-3.5-turbo"
            config_dict["server_url"] = None
        elif fallback_provider == "ollama":
            config_dict["model_name"] = "llama2"
            config_dict["server_url"] = "http://localhost:11434"
        return LLMConfig(**config_dict)

    class Config:
        env_file = ".env"
        env_prefix = "LLM_" 