from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def debug_headers(request):
    """Debug endpoint to check request headers"""
    return JsonResponse({
        'method': request.method,
        'headers': dict(request.headers),
        'x_request_id': request.headers.get('X-Request-Id', 'NOT_FOUND'),
        'meta_x_request_id': request.META.get('HTTP_X_REQUEST_ID', 'NOT_FOUND'),
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('movies.api.urls')),
    path('debug-headers/', debug_headers),
]
