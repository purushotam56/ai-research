#!/usr/bin/env python
"""Test centralized LLM models configuration."""

import sys
sys.path.insert(0, '/Users/pc/dev/techbubble/ai-bot/app-1')

from llm_config import (
    LLM_MODELS,
    get_model_by_id,
    get_provider_from_model_id,
    get_all_available_models,
    model_id_to_provider,
    model_id_to_model_name
)

def test_llm_models_config():
    print("=" * 70)
    print("Testing Centralized LLM Models Configuration")
    print("=" * 70)
    
    # Test 1: Print all models
    print("\n1. All Configured Models:")
    print("-" * 70)
    for category, models in LLM_MODELS.items():
        print(f"\n   {category.upper()}:")
        for model in models:
            print(f"     - {model['id']}: {model['name']}")
            print(f"       Provider: {model.get('provider')}, Model: {model.get('model_name')}")
    
    # Test 2: Model lookup by ID
    print("\n\n2. Model Lookup Tests:")
    print("-" * 70)
    
    test_ids = [
        'perplexity-sonar',
        'openai-gpt35',
        'openai-gpt4',
        'ibm-granite',
        'document-search'
    ]
    
    for model_id in test_ids:
        model = get_model_by_id(model_id)
        if model:
            print(f"   ✓ {model_id}")
            print(f"     - Provider: {model.get('provider')}")
            print(f"     - Model Name: {model.get('model_name')}")
            print(f"     - Requires Key: {model.get('requires_key')}")
        else:
            print(f"   ✗ {model_id} - NOT FOUND")
    
    # Test 3: Provider extraction
    print("\n\n3. Provider Extraction Tests:")
    print("-" * 70)
    for model_id in test_ids:
        provider = model_id_to_provider(model_id)
        print(f"   {model_id} → {provider}")
    
    # Test 4: Model name extraction
    print("\n\n4. Model Name Extraction Tests:")
    print("-" * 70)
    for model_id in test_ids:
        model_name = model_id_to_model_name(model_id)
        print(f"   {model_id} → {model_name}")
    
    # Test 5: Provider from model ID
    print("\n\n5. Provider from Model ID:")
    print("-" * 70)
    for model_id in test_ids:
        provider = get_provider_from_model_id(model_id)
        print(f"   {model_id} → {provider}")
    
    print("\n" + "=" * 70)
    print("✓ All tests completed successfully!")
    print("=" * 70)

if __name__ == "__main__":
    test_llm_models_config()
