from django.http import JsonResponse

class APIResponse:
    """
    Görünümler (Views) için standart JSON yanıt oluşturucu.
    """

    @staticmethod
    def success(data=None, message="İşlem başarılı.", status_code=200):
        """Başarılı bir işlemi standart formatta döndürür."""
        response = {
            "status": "success",
            "message": message
        }
        if data is not None:
            response["data"] = data
            
        return JsonResponse(response, status=status_code)

    @staticmethod
    def error(message="Bir hata oluştu.", status_code=400, details=None):
        """Hatalı bir işlemi standart formatta döndürür."""
        response = {
            "status": "error",
            "message": message
        }
        if details:
            response["details"] = details
            
        return JsonResponse(response, status=status_code)
        
    @staticmethod
    def method_not_allowed(allowed_methods=["POST"]):
        """Yanlış HTTP metodlarında standart bir hata döndürür."""
        return JsonResponse({
            "status": "error",
            "message": f"Yanlış istek tipi. İzin verilenler: {', '.join(allowed_methods)}"
        }, status=405)