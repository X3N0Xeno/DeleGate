from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Profile
from .routing import VALID_ROLES
from home.models import DelegationTask
from user_settings.models import UserSettings

@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        profile.role_title = request.POST.get('role_title', profile.role_title).strip()
        profile.department = request.POST.get('department', profile.department).strip()
        profile.bio = request.POST.get('bio', profile.bio).strip()
        role = request.POST.get('preferred_role', profile.preferred_role)
        if role in VALID_ROLES:
            profile.preferred_role = role
            # Settings keeps its own copy of the default workspace; keep both
            # in step so saving Settings later can't silently undo this.
            settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
            settings_obj.default_dashboard = role
            settings_obj.save(update_fields=['default_dashboard'])
            request.session['dg_role'] = role
            request.session.modified = True
        request.user.first_name = request.POST.get('first_name', request.user.first_name).strip()
        request.user.last_name = request.POST.get('last_name', request.user.last_name).strip()
        request.user.save()
        profile.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('user_profile:profile')

    from django.db.models import Count, Q
    total_dispatched = DelegationTask.objects.filter(created_by=request.user).count()
    mined_stats = DelegationTask.objects.filter(claimed_by=request.user).aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='COMPLETED')),
        active=Count('id', filter=~Q(status='COMPLETED')),
    )
    total_mined = mined_stats['total'] or 0
    completed_mined = mined_stats['completed'] or 0
    active_mined = mined_stats['active'] or 0
    completion_rate = int((completed_mined / total_mined * 100) if total_mined > 0 else 0)

    return render(request, 'user_profile/profile.html', {
        'profile': profile,
        'stats': {
            'dispatched': total_dispatched,
            'total_mined': total_mined,
            'completed': completed_mined,
            'active_mined': active_mined,
            'completion_rate': completion_rate,
        }
    })
