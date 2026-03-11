// ==========================================
// 1. DATA & DEFAULTS (SENİN ÖZEL PROMPTLARIN)
// ==========================================
// ==========================================
// 1. DATA (VERİLER ARTIK BACKEND'DEN GELİYOR)
// ==========================================
const DEFAULT_PROMPTS = window.BACKEND_DEFAULT_PROMPTS;
const GENERATION_MODELS = window.BACKEND_GENERATION_MODELS;

// ==========================================
// 2. BAŞLATMA (INITIALIZATION)
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    renderGenerationModels();
    
    // Eğer veritabanından gelen önceden kaydedilmiş bir ayar yoksa, varsayılanları yükle
    if (!window.USER_SAVED_PIPELINE || window.USER_SAVED_PIPELINE.length === 0) {
        loadDefaultPrompt('detection');
        loadDefaultPrompt('seo');
    } else {
        // EĞER KAYIT VARSA, KULLANICININ AYARLARINI GERİ YÜKLE!
        restoreUserConfig();
    }
});

function restoreUserConfig() {
    console.log("Kayıtlı ayarlar yükleniyor...", window.USER_SAVED_PIPELINE);
    
    let pipeline = window.USER_SAVED_PIPELINE;
    
    // Veri temizleme (String olarak geldiyse listeye çevir)
    if (typeof pipeline === 'string') {
        try { pipeline = JSON.parse(pipeline); } catch(e) {}
        if (typeof pipeline === 'string') {
            try { pipeline = JSON.parse(pipeline); } catch(e) {}
        }
    }
    
    if (!Array.isArray(pipeline)) return;

    // 1. GÜVENLİ TEMİZLİK: Büyük/küçük harf hatası yapmamak için tam ID'leri eşleştiriyoruz!
    const moduleMap = {
        'enableDetection': 'detectionContent',
        'enableGeneration': 'generationContent',
        'enableUpscale': 'upscaleContent',
        'enableBgRemoval': 'bgRemovalContent',
        'enableSeo': 'seoContent'
    };

    for (const [cbId, contentId] of Object.entries(moduleMap)) {
        const cb = document.getElementById(cbId);
        if (cb) {
            cb.checked = false;
            // ÇIKARILAN ÖZELLİK EKLENDİ: Arayüzün kilitlenmemesi için senin fonksiyonun kullanıldı
            if (typeof handleModuleToggle === 'function') {
                handleModuleToggle(cbId, contentId);
            }
        }
    }

    // 2. KAYITLARI YÜKLE (GÜVENLİ BLOK)
    pipeline.forEach(step => {
        try {
            if (step.step === 'detection') {
                const cb = document.getElementById('enableDetection');
                if (cb) { cb.checked = true; handleModuleToggle('enableDetection', 'detectionContent'); }
                if (step.prompt && document.getElementById('detectionPrompt')) {
                    document.getElementById('detectionPrompt').value = step.prompt;
                }
            }
            if (step.step === 'generation') {
                const cb = document.getElementById('enableGeneration');
                if (cb) { cb.checked = true; handleModuleToggle('enableGeneration', 'generationContent'); }
                
                // ÇIKARILAN ÖZELLİK EKLENDİ: Önce tüm alt AI modellerinin tikini kaldır ve arayüzü sıfırla
                if (typeof GENERATION_MODELS !== 'undefined') {
                    GENERATION_MODELS.forEach(m => {
                        const genCb = document.getElementById(`gen_model_${m.id}`);
                        if(genCb) {
                            genCb.checked = false;
                            if (typeof toggleGenPrompt === 'function') toggleGenPrompt(m.id);
                        }
                    });
                }

                if (step.models && Array.isArray(step.models)) {
                    step.models.forEach(m => {
                        const genCb = document.getElementById(`gen_model_${m.model}`);
                        if(genCb) {
                            genCb.checked = true;
                            if (typeof toggleGenPrompt === 'function') toggleGenPrompt(m.model);
                            const promptInput = document.getElementById(`gen_prompt_${m.model}`);
                            if (promptInput) promptInput.value = m.prompt;
                        }
                    });
                }
            }
            if (step.step === 'upscale') {
                const cb = document.getElementById('enableUpscale');
                if (cb) { cb.checked = true; handleModuleToggle('enableUpscale', 'upscaleContent'); }
            }
            if (step.step === 'bg_removal') {
                const cb = document.getElementById('enableBgRemoval');
                if (cb) { cb.checked = true; handleModuleToggle('enableBgRemoval', 'bgRemovalContent'); }
            }
            if (step.step === 'seo') {
                const cb = document.getElementById('enableSeo');
                if (cb) { cb.checked = true; handleModuleToggle('enableSeo', 'seoContent'); }
                
                if(step.prompt && document.getElementById('seoPrompt')) {
                    document.getElementById('seoPrompt').value = step.prompt;
                }
                if(step.system_prompt && document.getElementById('seoSystemPrompt')) {
                    document.getElementById('seoSystemPrompt').value = step.system_prompt;
                }
            }
        } catch (err) {
            console.error(`Adım yüklenirken hata (${step.step}):`, err);
        }
    });
}

// ==========================================
// 3. ARAYÜZ ETKİLEŞİMLERİ (UI TOGGLES)
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

function toggleSection(sectionPrefix) {
    // Sadece akordiyon başlıklarına tıklama efekti için ayrıldı.
    // Ana kontrol Checkbox'larda (handleModuleToggle)
}

function handleModuleToggle(checkboxId, contentId) {
    const checkbox = document.getElementById(checkboxId);
    const content = document.getElementById(contentId);
    const sectionId = checkboxId.replace('enable', '').toLowerCase() + 'SectionIcon';
    const icon = document.getElementById(sectionId);

    if (checkbox.checked) {
        content.classList.add('open');
        if(icon) icon.classList.add('rotate-180');
    } else {
        content.classList.remove('open');
        if(icon) icon.classList.remove('rotate-180');
    }
}

// ==========================================
// 4. DİNAMİK MODEL LİSTELEME
// ==========================================
function renderGenerationModels() {
    const container = document.getElementById('generationModelsContainer');
    if(!container) return;
    
    container.innerHTML = ''; 

    GENERATION_MODELS.forEach((model) => {
        const wrapper = document.createElement('div');
        wrapper.className = "border border-slate-200 rounded-lg p-4 bg-white shadow-sm hover:border-primary transition-colors";
        
        wrapper.innerHTML = `
            <div class="flex items-center justify-between mb-3">
                <label class="flex items-center gap-3 cursor-pointer group w-full">
                    <input type="checkbox" id="gen_model_${model.id}" class="w-5 h-5 rounded border-slate-300 text-primary focus:ring-primary" checked onchange="toggleGenPrompt('${model.id}')">
                    <div class="flex justify-between w-full pr-4">
                        <span class="font-medium text-slate-800 group-hover:text-primary transition-colors">${model.name}</span>
                        <span class="ml-2 text-xs font-semibold bg-slate-100 text-slate-600 px-2 py-0.5 rounded">${model.price}</span>
                    </div>
                </label>
            </div>
            
            <div id="gen_prompt_container_${model.id}" class="space-y-2 mt-3 pt-3 border-t border-slate-100">
                <div class="flex items-center justify-between">
                    <label class="text-xs font-medium text-slate-600">Bu Model İçin Prompt</label>
                    <button type="button" onclick="resetGenPrompt('${model.id}')" class="text-xs text-primary hover:underline"><i class="fa-solid fa-rotate-left"></i> Varsayılan</button>
                </div>
                <textarea id="gen_prompt_${model.id}" rows="2" class="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-primary outline-none font-mono">${model.defaultPrompt}</textarea>
            </div>
        `;
        container.appendChild(wrapper);
    });
}

function toggleGenPrompt(modelId) {
    const checkbox = document.getElementById(`gen_model_${modelId}`);
    const container = document.getElementById(`gen_prompt_container_${modelId}`);
    if (checkbox.checked) {
        container.classList.remove('hidden');
    } else {
        container.classList.add('hidden');
    }
}

function resetGenPrompt(modelId) {
    const model = GENERATION_MODELS.find(m => m.id === modelId);
    if (model) {
        document.getElementById(`gen_prompt_${modelId}`).value = model.defaultPrompt;
    }
}

function loadDefaultPrompt(section) {
    const select = document.getElementById(`${section}Model`);
    if(!select) return;
    const selectedModel = select.value;
    
    // SEO (GPT-4o) için özel çift kutu doldurma mantığı
    if (section === 'seo') {
        const userTextarea = document.getElementById('seoPrompt');
        const systemTextarea = document.getElementById('seoSystemPrompt');
        
        if (DEFAULT_PROMPTS[section] && DEFAULT_PROMPTS[section][selectedModel]) {
            userTextarea.value = DEFAULT_PROMPTS[section][selectedModel].user_prompt;
            systemTextarea.value = DEFAULT_PROMPTS[section][selectedModel].system_prompt;
        }
    } 
    // Diğer tek kutulu modeller (Dino vb.) için
    else {
        const textarea = document.getElementById(`${section}Prompt`);
        if (textarea && DEFAULT_PROMPTS[section] && DEFAULT_PROMPTS[section][selectedModel] !== undefined) {
            textarea.value = DEFAULT_PROMPTS[section][selectedModel];
        }
    }
}

function resetPrompt(section) {
    loadDefaultPrompt(section);
}

// ==========================================
// 5. VERİ TOPLAMA VE BACKEND'E GÖNDERME
// ==========================================
async function saveConfiguration() {
    const apiKey = document.getElementById('apiKey').value;
    if (!apiKey) {
        alert("Lütfen ilerlemeden önce Replicate API anahtarınızı girin.");
        document.getElementById('apiKey').focus();
        return;
    }

    // JSON Veri Paketi
    const config = {
        api: {
            platform: document.getElementById('apiPlatform').value,
            key: apiKey
        },
        pipeline: []
    };

    if (document.getElementById('enableDetection').checked) {
        config.pipeline.push({ step: "detection", model: document.getElementById('detectionModel').value, prompt: document.getElementById('detectionPrompt').value });
    }

    if (document.getElementById('enableGeneration').checked) {
        const selectedGenModels = [];
        GENERATION_MODELS.forEach(model => {
            if (document.getElementById(`gen_model_${model.id}`).checked) {
                selectedGenModels.push({ model: model.id, prompt: document.getElementById(`gen_prompt_${model.id}`).value });
            }
        });
        if (selectedGenModels.length > 0) {
            config.pipeline.push({ step: "generation", models: selectedGenModels });
        } else {
            alert("AI Üretimi aktif edildi fakat model seçilmedi.");
            return;
        }
    }

    if (document.getElementById('enableUpscale').checked) {
        config.pipeline.push({ step: "upscale", model: document.getElementById('upscaleModel').value });
    }

    if (document.getElementById('enableBgRemoval').checked) {
        config.pipeline.push({ step: "bg_removal", model: document.getElementById('bgRemovalModel').value });
    }

    if (document.getElementById('enableSeo').checked) {
        // BURASI DEĞİŞTİ: Artık hem User Prompt hem System Prompt kaydediliyor
        config.pipeline.push({ 
            step: "seo", 
            model: document.getElementById('seoModel').value, 
            prompt: document.getElementById('seoPrompt').value,
            system_prompt: document.getElementById('seoSystemPrompt').value
        });
    }

    if (config.pipeline.length === 0) {
        alert("Lütfen çalışacak en az bir adımı aktif edin.");
        return;
    }

    // Backend'e İstek At
    try {
        const btn = document.querySelector('button[onclick="saveConfiguration()"]');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Kaydediliyor...';
        btn.disabled = true;

        const response = await fetch('/save-config/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (data.status === 'success') {
            showToast();
            // Başarılı olursa Dashboard'a yönlendir!
            setTimeout(() => { 
                window.location.href = '/dashboard/'; 
            }, 1500);
        } else {
            alert("Hata: " + data.message);
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    } catch (err) {
        alert("Bağlantı Hatası: " + err.message);
    }
}

function showToast() {
    const toast = document.getElementById('toast');
    if(toast) {
        toast.classList.remove('translate-y-20', 'opacity-0');
        setTimeout(() => { toast.classList.add('translate-y-20', 'opacity-0'); }, 3000);
    }
}