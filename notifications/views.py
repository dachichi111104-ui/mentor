from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from notifications.models import Notification

@login_required
def notification_center_view(request):
    notifications = Notification.objects.filter(recipient=request.user)
    return render(request, 'notifications/notification_center.html', {'notifications': notifications})

@login_required
def notification_mark_read_view(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, recipient=request.user)
    notif.is_read = True
    notif.save()
    if notif.link:
        return redirect(notif.link)
    return redirect('notification_center')

@login_required
def notification_mark_all_read_view(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'Đã đánh dấu tất cả thông báo là đã đọc.')
    return redirect('notification_center')

@login_required
def unread_count_ajax(request):
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'status': 'success', 'unread_count': count})
