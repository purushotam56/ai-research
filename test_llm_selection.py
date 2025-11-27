#!/usr/bin/env python
"""Test LLM selection and Perplexity integration."""

import sys
import os

# Add app-1 to path
sys.path.insert(0, '/Users/pc/dev/techbubble/ai-bot/app-1')

from llm import create_chatbot

def test_llm_selection():
    print("=" * 60)
    print("Testing LLM Selection and Perplexity Integration")
    print("=" * 60)
    
    # Create chatbot
    print("\n1. Creating chatbot...")
    try:
        chatbot = create_chatbot()
        print(f"   ✓ Chatbot created")
        print(f"   - Provider: {chatbot.llm_provider}")
        print(f"   - LLM Available: {chatbot.llm_available}")
    except Exception as e:
        print(f"   ✗ Failed to create chatbot: {e}")
        return False
    
    # Test with Perplexity model selection
    print("\n2. Testing Perplexity model selection...")
    try:
        test_docs = [
            "Dhruv Bhatt is a Delivery Manager at TechBubble, Australia",
            "He leads the delivery team in Australia",
            "Contact: dhruv@techbubble.com"
        ]
        
        result = chatbot.generate_answer(
            question="Who is Dhruv Bhatt?",
            documents=test_docs,
            user_id=1,
            llm_model="perplexity-sonar"
        )
        
        print(f"   ✓ LLM generation completed")
        print(f"   - Provider: {result.get('provider')}")
        print(f"   - Status: {result.get('status')}")
        print(f"   - Model: {result.get('model')}")
        print(f"   - Answer preview: {result.get('answer', '')[:100]}...")
        
        if result.get('status') == 'success':
            print("\n   ✓ SUCCESS: Perplexity LLM working correctly!")
            return True
        elif result.get('status') == 'error':
            print(f"\n   ⚠ Error status returned: {result.get('answer')}")
            return False
        else:
            print(f"\n   ? Unknown status: {result.get('status')}")
            return False
            
    except Exception as e:
        print(f"   ✗ Failed to test Perplexity: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_llm_selection()
    sys.exit(0 if success else 1)
