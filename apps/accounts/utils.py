from apps.ai.services.config.system_prompts import DEFAULT_SYSTEM_PROMPTS
from apps.ai.services.config.user_prompts import DEFAULT_USER_PROMPTS

def get_default_pipeline_defaults():
    """Yeni kullanıcıya veya sıfırlamada verilecek varsayılan değerler sözlüğü"""
    return {
        'enable_detection': True,
        'detection_model': 'grounding-dino',
        'detection_prompt': DEFAULT_USER_PROMPTS["grounding-dino"],
        
        'enable_generation': True,
        'gen_model_1_id': 'flux-2-pro',
        'gen_model_1_enabled': True,
        'gen_model_1_prompt': DEFAULT_USER_PROMPTS["flux-2-pro"],
        
        'gen_model_2_id': 'seedream-4.5',
        'gen_model_2_enabled': True,
        'gen_model_2_prompt': DEFAULT_USER_PROMPTS["seedream-4.5"],
        
        'gen_model_3_id': 'nano-banana',
        'gen_model_3_enabled': True,
        'gen_model_3_prompt': DEFAULT_USER_PROMPTS["nano-banana"],
        
        'enable_upscale': True,
        'upscale_model': 'recraft-crisp',
        
        'enable_bg_removal': True,
        'bg_removal_model': 'bria-rmbg',
        
        'enable_vision': True,
        'vision_model': 'gpt-4o-vision',
        'vision_system_prompt': DEFAULT_SYSTEM_PROMPTS["gpt-4o-vision"],
        'vision_user_prompt': DEFAULT_USER_PROMPTS["gpt-4o-vision"],
        
        'enable_seo': True,
        'seo_model': 'gpt-4o',
        'seo_title_system_prompt': DEFAULT_SYSTEM_PROMPTS["gpt-4o_title"],
        'seo_tags_system_prompt': DEFAULT_SYSTEM_PROMPTS["gpt-4o_tag"],
        'seo_user_prompt': DEFAULT_USER_PROMPTS["gpt-4o"],
    }