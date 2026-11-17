from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import UserSettings
from user_profile.models import Profile
from user_profile.routing import VALID_ROLES

PRIORITIES = {value for value, _ in UserSettings.PRIORITY_CHOICES}
THEMES = {value for value, _ in UserSettings.THEME_CHOICES}


@login_required
@require_POST
def set_theme(request):
    """Instant-save endpoint for the theme switcher (no page reload)."""
    theme = request.POST.get('theme', '')
    if theme not in THEMES:
        return JsonResponse({'ok': False, 'error': 'Unknown theme.'}, status=400)
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
    settings_obj.theme = theme
    settings_obj.save(update_fields=['theme'])
    return JsonResponse({'ok': True, 'theme': theme})


@login_required
def settings_view(request):
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'preferences':
            priority = request.POST.get('default_priority', 'MED')
            dashboard = request.POST.get('default_dashboard', 'CLAIMANT')
            settings_obj.default_priority = priority if priority in PRIORITIES else 'MED'
            settings_obj.default_dashboard = dashboard if dashboard in VALID_ROLES else settings_obj.default_dashboard
            settings_obj.compact_view = 'compact_view' in request.POST
            settings_obj.email_notifications = 'email_notifications' in request.POST
            settings_obj.weekly_digest = 'weekly_digest' in request.POST
            settings_obj.save()

            # Keep profile preferred role in sync
            profile.preferred_role = settings_obj.default_dashboard
            profile.save()

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
        'theme_choices': settings_obj.THEME_CHOICES,
        'toggles': [
            ('compact_view', 'Compact rows', 'Tighter spacing in task lists', settings_obj.compact_view),
            ('email_notifications', 'Email notifications', 'Get an email when a task is assigned to you', settings_obj.email_notifications),
            ('weekly_digest', 'Weekly digest', 'A Monday summary of your delegation activity', settings_obj.weekly_digest),
        ],
    })
