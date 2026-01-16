import os
from typing import List, Dict
from pydantic import BaseModel, Field



class MoAConfigModel(BaseModel):
    """Configuration model for MoA plugin settings."""
    moa_models: List[str] = Field(..., description="List of models to use for MoA")
    timeout: int = Field(default=3, ge=1, description="Timeout for individual model queries")
    max_models: int = Field(default=3, ge=1, description="Maximum number of models to use")
    prompts: Dict[str, str] = Field(default_factory=dict, description="Prompt templates")

    @classmethod
    def from_env_and_json(cls, json_data: Dict) -> 'MoAConfigModel':
        """Create MoAConfigModel from JSON data with environment variable overrides.

        Environment variables will override JSON values if they exist.
        Supported environment variables:
        - OLLAMA_MOA_MODELS
        - OLLAMA_MOA_TIMEOUT
        - OLLAMA_MOA_MAX_MODELS
        """
        # Start with JSON data
        config_data = json_data.copy()

        # Override with environment variables if they exist
        env_mappings = {
            'OLLAMA_MOA_MODELS': 'moa_models',
            'OLLAMA_MOA_TIMEOUT': 'timeout',
            'OLLAMA_MOA_MAX_MODELS': 'max_models',
        }

        for env_var, config_key in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convert string values to appropriate types
                if config_key in ['timeout', 'max_models']:
                    try:
                        config_data[config_key] = int(env_value)
                    except ValueError:
                        pass
                elif config_key == 'moa_models':
                    config_data[config_key] = [m.strip() for m in env_value.split(',') if m.strip()]
                else:
                    config_data[config_key] = env_value

        return cls(**config_data)

