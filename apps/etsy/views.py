import json
import re
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

# Servislerimizi içe aktarıyoruz
from apps.etsy.services.scraper import EtsyScraperService # Sen adını ne koyduysan

@csrf_exempt
@login_required(login_url='/accounts/login/')
def analyze_url_action(request):
    """UI'dan gelen URL dizisini (list) analiz eder ve TÜM SONUÇLARI DÖNER."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            raw_urls = data.get('urls', [])
            force_rescrape = data.get('force_rescrape', False) # YENİ BAYRAK
            
            clean_urls = [u.strip() for u in raw_urls if 'etsy.com' in u.strip().lower()]
            if not clean_urls:
                 return JsonResponse({"status": "error", "message": "Geçerli bir Etsy URL'si bulunamadı."}, status=400)

            results = [] # Çekilen tüm ürünleri burada toplayacağız
            
            for single_url in clean_urls:
                try:
                    product = EtsyScraperService.get_or_scrape_product(single_url, request.user, force_rescrape=force_rescrape)
                    if product:
                        results.append({
                            "id": product.id,
                            "title": product.title,
                            "price": product.price,
                            "image_url": product.image_url,
                            "description": product.description,
                            "tags": product.tags.split(',') if product.tags else [],
                            "views": product.views or 0,
                            "favorited": product.favorites_count or 0,
                            "url": product.url # Yeniden kazıma için URL de gerekli
                        })
                except Exception as inner_e:
                    print(f"Hata: {single_url} işlenirken hata oluştu: {str(inner_e)}")
                    continue
            
            # Artık tek bir ürün değil, 'results' listesini dönüyoruz
            if results:
                return JsonResponse({"status": "success", "results": results, "total_urls_processed": len(results)})
            else:
                return JsonResponse({"status": "error", "message": "Veri çekilemedi."}, status=500)
        
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Sadece POST metodu desteklenir."}, status=405)