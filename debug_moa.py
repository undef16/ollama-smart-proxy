#!/usr/bin/env python3
"""
Debug script to test the _build_scoring_prompt function in isolation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from plugins.moa.agent import MoAAgent
from src.shared.config_manager import ConfigurationManager
from plugins.moa.moa_config import MoAConfigModel

def test_build_scoring_prompt():
    print("Testing _build_scoring_prompt function...")
    
    # Create MoAAgent instance
    agent = MoAAgent()
    
    # Test the _build_scoring_prompt function directly
    query = "What is the capital of France?"
    previous_response = "Paris is the capital of France."
    
    print(f"Query: {query}")
    print(f"Previous response: {previous_response}")
    
    try:
        prompt = agent._build_scoring_prompt(query, previous_response)
        print(f"\nGenerated prompt:\n{prompt}")
        
        # Verify the prompt contains the expected placeholders filled
        if '{query}' in prompt or '{previous_response}' in prompt:
            print("\n❌ ERROR: Placeholders not properly replaced in prompt!")
            return False
        else:
            print("\n✅ SUCCESS: Placeholders properly replaced in prompt")
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR in _build_scoring_prompt: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_loading():
    print("\nTesting configuration loading...")
    
    try:
        config = ConfigurationManager.get_config(MoAConfigModel, config_path='src/plugins/moa/config.json')
        print(f"Configuration loaded successfully: {config}")
        
        # Check if prompts exist
        if hasattr(config, 'prompts') and 'ranking_prompt' in config.prompts:
            print(f"Ranking prompt template: {config.prompts['ranking_prompt'][:100]}...")
            return True
        else:
            print("❌ ERROR: Ranking prompt not found in configuration")
            return False
            
    except Exception as e:
        print(f"❌ ERROR loading configuration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting MOA Agent Debug Test")
    print("="*50)
    
    config_ok = test_config_loading()
    if config_ok:
        prompt_ok = test_build_scoring_prompt()
    
    print("="*50)
    print("Debug test completed.")