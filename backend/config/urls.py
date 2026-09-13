from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    return JsonResponse({
        'service': '知行书院图书馆 API',
        'status': 'ok',
        'api': '/api/',
        'admin': '/admin/',
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('library.urls')),
    path('', health_check),
]
