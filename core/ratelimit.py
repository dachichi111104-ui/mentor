from django.core.cache import cache
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from functools import wraps

def ratelimit(key_prefix: str, limit: int, period: int):
    """
    Simple cache-based rate limiter decorator.
    key_prefix: str, limit: max requests, period: seconds
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                user_key = f"{key_prefix}:{request.user.id}"
            else:
                ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '127.0.0.1')).split(',')[0].strip()
                user_key = f"{key_prefix}:ip:{ip}"

            current = cache.get(user_key, 0)
            if current >= limit:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '') or request.path.startswith('/api/'):
                    return JsonResponse({'status': 'error', 'code': 'rate_limited', 'message': f'Thao tác quá nhanh. Giới hạn tối đa {limit} lần trong {period//60} phút.'}, status=429)
                return render(request, 'errors/429.html', {'message': f'Thao tác quá nhanh. Vui lòng thử lại sau {period//60} phút.'}, status=429)

            cache.set(user_key, current + 1, period)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
