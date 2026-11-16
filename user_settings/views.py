from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from .models import UserSettings

@login_required
def settings_view(request):
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'preferences':
            settings_obj.default_priority = request.POST.get('default_priority', 'MED')
            settings_obj.compact_view = 'compact_view' in request.POST
            settings_obj.email_notifications = 'email_notifications' in request.POST
            settings_obj.weekly_digest = 'weekly_digest' in request.POST
            settings_obj.save()
            messages.success(request, 'Preferences saved.')

        elif action == 'password':
            current = request.POST.get('current_password')
            new_pw = request.POST.get('new_password')
            confirm = request.POST.get('confirm_password')
            if not request.user.check_password(current):
                messages.error(request, 'Current password is incorrect.')
            elif new_pw != confirm:
                messages.error(request, 'New passwords do not match.')
            elif len(new_pw) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
            else:
                request.user.set_password(new_pw)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password updated successfully.')

        return redirect('user_settings:settings')

    return render(request, 'user_settings/user_settings.html', {
        'settings': settings_obj,
        'toggles': [
            ('compact_view', 'Compact View', 'Show tasks in a denser layout', settings_obj.compact_view),
            ('email_notifications', 'Email Notifications', 'Get notified when tasks are assigned to you', settings_obj.email_notifications),
            ('weekly_digest', 'Weekly Digest', 'Receive a weekly summary of your delegation activity', settings_obj.weekly_digest),
        ],
    })
