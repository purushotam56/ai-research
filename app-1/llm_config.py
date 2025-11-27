"""
Centralized LLM Models Configuration
This file defines all available LLM models and their configurations.
"""

import os

# ============================================================================
# LLM Models Dictionary - Central source of truth for all available models
# ============================================================================

LLM_MODELS = {
    'cloud_models': [
        {
            'id': 'openai-gpt35',
            'name': 'OpenAI - GPT-3.5 Turbo',
            'desc': 'Fast, High Quality',
            'provider': 'openai',
            'model_name': 'gpt-3.5-turbo',
            'requires_key': 'OPENAI_API_KEY'
        },
        {
            'id': 'openai-gpt4',
            'name': 'OpenAI - GPT-4',
            'desc': 'Advanced, Slower',
            'provider': 'openai',
            'model_name': 'gpt-4',
            'requires_key': 'OPENAI_API_KEY'
        },
        {
            'id': 'perplexity-sonar',
            'name': 'Perplexity - Sonar',
            'desc': 'Fast, Accurate',
            'provider': 'perplexity',
            'model_name': 'sonar',
            'requires_key': 'PERPLEXITY_API_KEY'
        },
        {
            'id': 'perplexity-sonar-pro',
            'name': 'Perplexity - Sonar Pro',
            'desc': 'Advanced reasoning',
            'provider': 'perplexity',
            'model_name': 'sonar-pro',
            'requires_key': 'PERPLEXITY_API_KEY'
        },
        {
            'id': 'ibm-granite',
            'name': 'IBM Watson - Granite',
            'desc': 'Good, Reliable',
            'provider': 'ibm',
            'model_name': 'ibm/granite-3-3-8b-instruct',
            'requires_key': 'IBM_API_KEY'
        },
    ],
    'offline_models': [],  # Dynamically populated
    'other_models': [
        {
            'id': 'document-search',
            'name': 'Document Search Only',
            'desc': 'No AI - Pure RAG',
            'provider': 'document-search',
            'model_name': 'none',
            'requires_key': None
        }
    ]
}


def get_model_by_id(model_id: str) -> dict:
    """
    Get a model configuration by its ID.
    
    Args:
        model_id: The model ID (e.g., 'perplexity-sonar')
        
    Returns:
        Model configuration dict or None if not found
    """
    for category in ['cloud_models', 'offline_models', 'other_models']:
        for model in LLM_MODELS.get(category, []):
            if model.get('id') == model_id:
                return model
    return None


def get_provider_from_model_id(model_id: str) -> str:
    """
    Extract provider name from model ID.
    
    Args:
        model_id: The model ID (e.g., 'perplexity-sonar')
        
    Returns:
        Provider name (e.g., 'perplexity') or None
    """
    model = get_model_by_id(model_id)
    return model.get('provider') if model else None


def get_all_models() -> dict:
    """
    Get all available models organized by category.
    
    Returns:
        Dictionary with cloud_models, offline_models, other_models
    """
    return LLM_MODELS.copy()


def get_available_cloud_models() -> list:
    """Get only cloud-based models that have valid API keys configured."""
    available = []
    for model in LLM_MODELS['cloud_models']:
        api_key_env = model.get('requires_key')
        if api_key_env and os.getenv(api_key_env):
            available.append(model)
    return available


def get_available_offline_models() -> list:
    """Get available offline models."""
    return LLM_MODELS['offline_models']


def get_all_available_models() -> dict:
    """
    Get all available models, filtering based on configured API keys.
    
    Returns:
        Dictionary with available models by category
    """
    return {
        'cloud_models': get_available_cloud_models(),
        'offline_models': get_available_offline_models(),
        'other_models': LLM_MODELS['other_models']
    }


def add_offline_model(model_id: str, name: str, desc: str, size: int = 0) -> None:
    """
    Add a dynamically discovered offline model to the list.
    
    Args:
        model_id: Unique model ID
        name: Human-readable name
        desc: Description
        size: Optional model size in bytes
    """
    model_config = {
        'id': model_id,
        'name': name,
        'desc': desc,
        'provider': model_id.split('-')[0],  # Extract provider from ID
        'model_name': model_id,
        'requires_key': None
    }
    if size:
        model_config['size'] = size
    
    LLM_MODELS['offline_models'].append(model_config)


def model_id_to_provider(model_id: str) -> str:
    """
    Convert model ID to provider name.
    E.g., 'perplexity-sonar' -> 'perplexity'
    
    Args:
        model_id: The model ID
        
    Returns:
        Provider name
    """
    # Try to get from config first
    model = get_model_by_id(model_id)
    if model:
        return model.get('provider')
    
    # Fallback: extract from ID prefix
    if '-' in model_id:
        return model_id.split('-')[0]
    
    return model_id


def model_id_to_model_name(model_id: str) -> str:
    """
    Convert model ID to actual model name for API calls.
    E.g., 'perplexity-sonar' -> 'sonar'
    
    Args:
        model_id: The model ID
        
    Returns:
        Model name for API calls
    """
    # Try to get from config first
    model = get_model_by_id(model_id)
    if model:
        return model.get('model_name')
    
    # Fallback: extract from ID suffix
    if '-' in model_id:
        parts = model_id.split('-', 1)
        return parts[1]
    
    return model_id
