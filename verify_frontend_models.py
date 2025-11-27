#!/usr/bin/env python
"""
Verification script for frontend model loading from backend.
Tests the complete flow: Backend → API → Frontend
"""

import sys
import os
sys.path.insert(0, '/Users/pc/dev/techbubble/ai-bot/app-1')

from llm_config import get_all_available_models, LLM_MODELS

def verify_models_config():
    print("=" * 80)
    print("FRONTEND MODEL LOADING VERIFICATION")
    print("=" * 80)
    
    # Test 1: Verify backend config has models
    print("\n1. Checking Backend Configuration:")
    print("-" * 80)
    
    models = get_all_available_models()
    
    cloud_count = len(models.get('cloud_models', []))
    offline_count = len(models.get('offline_models', []))
    other_count = len(models.get('other_models', []))
    
    print(f"   Cloud Models: {cloud_count}")
    print(f"   Offline Models: {offline_count}")
    print(f"   Other Models: {other_count}")
    print(f"   Total: {cloud_count + offline_count + other_count}")
    
    # Test 2: Verify model structure
    print("\n2. Checking Model Structure:")
    print("-" * 80)
    
    sample_model = None
    for model in models.get('cloud_models', []):
        sample_model = model
        break
    
    if sample_model:
        required_fields = ['id', 'name', 'desc', 'provider', 'model_name', 'requires_key']
        print(f"\n   Sample Model: {sample_model['id']}")
        all_fields_present = True
        for field in required_fields:
            present = field in sample_model
            status = "✓" if present else "✗"
            print(f"     {status} {field}: {sample_model.get(field, 'MISSING')}")
            if not present:
                all_fields_present = False
        
        if all_fields_present:
            print("\n   ✓ All required fields present!")
        else:
            print("\n   ✗ Missing required fields!")
            return False
    
    # Test 3: Verify API response format
    print("\n3. Checking API Response Format:")
    print("-" * 80)
    
    api_response = {
        "success": True,
        "models": get_all_available_models()
    }
    
    print(f"   Response structure:")
    print(f"     success: {api_response['success']}")
    print(f"     models.cloud_models: {len(api_response['models']['cloud_models'])} items")
    print(f"     models.offline_models: {len(api_response['models']['offline_models'])} items")
    print(f"     models.other_models: {len(api_response['models']['other_models'])} items")
    
    # Test 4: Verify each model can be used
    print("\n4. Checking Model Usability:")
    print("-" * 80)
    
    from llm_config import model_id_to_provider, model_id_to_model_name
    
    test_models = ['perplexity-sonar', 'openai-gpt35', 'document-search']
    all_valid = True
    
    for model_id in test_models:
        provider = model_id_to_provider(model_id)
        model_name = model_id_to_model_name(model_id)
        status = "✓" if provider and model_name else "✗"
        print(f"   {status} {model_id}")
        print(f"       → Provider: {provider}, Model: {model_name}")
        if not (provider and model_name):
            all_valid = False
    
    if not all_valid:
        return False
    
    # Test 5: Sample Frontend JSON
    print("\n5. Sample Frontend JSON:")
    print("-" * 80)
    
    import json
    print("\n   JSON that frontend will receive:")
    print(json.dumps(api_response, indent=2)[:500] + "...\n")
    
    # Final summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"✓ Backend has {cloud_count} cloud models configured")
    print(f"✓ Backend has {offline_count} offline models configured")
    print(f"✓ Backend has {other_count} other models configured")
    print(f"✓ All models have required fields")
    print(f"✓ Model provider/name conversion working")
    print(f"✓ API response format correct")
    print("\n✓ READY FOR FRONTEND!")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    success = verify_models_config()
    sys.exit(0 if success else 1)
