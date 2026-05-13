// Backend'den gelen veriler
const USER_SAVED_PIPELINE = window.USER_SAVED_PIPELINE || [];
const DEFAULT_PIPELINE = window.BACKEND_DEFAULT_PROMPTS || [];

document.addEventListener('DOMContentLoaded', () => {
    const moduleToggles = ['enableDetection', 'enableGeneration', 'enableUpscale', 'enableBgRemoval', 'enableVision', 'enableSeo'];
    
    moduleToggles.forEach(id => {
        const checkbox = document.getElementById(id);
        if (checkbox && checkbox.checked) {
            // Checkbox işaretliyse altındaki içeriği (Content) görünür yap
            const contentId = id.replace('enable', '').toLowerCase() + 'Content';
            const contentDiv = document.getElementById(contentId);
            if(contentDiv) {
                contentDiv.classList.remove('hidden');
            }
        }
    });
});

// ==========================================
// ARAYÜZ ETKİLEŞİMLERİ
// ==========================================
function togglePasswordVisibility(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
}

function toggleSection(sectionId) {
    const content = document.getElementById(sectionId.replace('Section', 'Content'));
    const icon = document.getElementById(sectionId + 'Icon');
    if (content.classList.contains('hidden')) {
        content.classList.remove('hidden');
        if(icon) icon.style.transform = 'rotate(180deg)';
    } else {
        content.classList.add('hidden');
        if(icon) icon.style.transform = 'rotate(0deg)';
    }
}

function handleModuleToggle(checkboxId, contentId) {
    const checkbox = document.getElementById(checkboxId);
    const content = document.getElementById(contentId);
    // toggleSection zaten açık/kapalı işini yapıyor, sadece checkbox state ile css senkronize edilir.
}

// Varsayılana Dön Butonları
// Varsayılana Dön Butonları (Backend'deki Sütun İsimlerine Göre Eşleştirildi)
function resetPrompt(module, type, domId = null) {
    const defaults = window.BACKEND_DEFAULT_PROMPTS || {};
    
    if (module === 'detection' && type === 'user') {
        document.getElementById('detectionUserPrompt').value = defaults.detection_prompt || "";
    } 
    else if (module === 'generation' && type === 'user' && domId) {
        document.getElementById(`genModel${domId}_prompt`).value = defaults[`gen_model_${domId}_prompt`] || "";
    }
    else if (module === 'vision' && type === 'system') {
        document.getElementById('visionSystemPrompt').value = defaults.vision_system_prompt || "";
    }
    else if (module === 'vision' && type === 'user') {
        document.getElementById('visionUserPrompt').value = defaults.vision_user_prompt || "";
    }
    else if (module === 'seo' && type === 'title_system') {
        document.getElementById('seoTitleSystemPrompt').value = defaults.seo_title_system_prompt || "";
    }
    else if (module === 'seo' && type === 'tags_system') {
        document.getElementById('seoTagsSystemPrompt').value = defaults.seo_tags_system_prompt || "";
    }
    else if (module === 'seo' && type === 'user') {
        document.getElementById('seoUserPrompt').value = defaults.seo_user_prompt || "";
    }
}

// ==========================================
// KAYDETME İŞLEMİ (POST)
// ==========================================
async function saveConfiguration() {
    const apiKey = document.getElementById('apiKey').value;
    
    // Verileri TAM OLARAK veritabanındaki sütun adlarıyla topluyoruz
    const config = {
        api: { platform: 'replicate', key: apiKey },
        pipeline: {
            enable_detection: document.getElementById('enableDetection').checked,
            detection_model: document.getElementById('detectionModel').value,
            detection_prompt: document.getElementById('detectionUserPrompt').value,

            enable_generation: document.getElementById('enableGeneration').checked,
            gen_model_1_id: document.getElementById('genModel1_id').value,
            gen_model_1_enabled: document.getElementById('genModel1_enable').checked,
            gen_model_1_prompt: document.getElementById('genModel1_prompt').value,
            
            gen_model_2_id: document.getElementById('genModel2_id').value,
            gen_model_2_enabled: document.getElementById('genModel2_enable').checked,
            gen_model_2_prompt: document.getElementById('genModel2_prompt').value,
            
            gen_model_3_id: document.getElementById('genModel3_id').value,
            gen_model_3_enabled: document.getElementById('genModel3_enable').checked,
            gen_model_3_prompt: document.getElementById('genModel3_prompt').value,

            enable_upscale: document.getElementById('enableUpscale').checked,
            upscale_model: document.getElementById('upscaleModel').value,

            enable_bg_removal: document.getElementById('enableBgRemoval').checked,
            bg_removal_model: document.getElementById('bgRemovalModel').value,

            enable_vision: document.getElementById('enableVision').checked,
            vision_model: document.getElementById('visionModel').value,
            vision_system_prompt: document.getElementById('visionSystemPrompt').value,
            vision_user_prompt: document.getElementById('visionUserPrompt').value,

            enable_seo: document.getElementById('enableSeo').checked,
            seo_model: document.getElementById('seoModel').value,
            seo_title_system_prompt: document.getElementById('seoTitleSystemPrompt').value,
            seo_tags_system_prompt: document.getElementById('seoTagsSystemPrompt').value,
            seo_user_prompt: document.getElementById('seoUserPrompt').value,
        }
    };

    try {
        const response = await fetch('/accounts/api/save-config/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            const toast = document.getElementById('toast');
            toast.classList.remove('translate-y-20', 'opacity-0');
            setTimeout(() => toast.classList.add('translate-y-20', 'opacity-0'), 3000);
        } else {
            alert("Hata: " + data.message);
        }
    } catch (err) {
        alert("Bağlantı Hatası: " + err.message);
    }
}