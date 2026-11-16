from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Profile
from home.models import DelegationTask

@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        profile.role_title = request.POST.get('role_title', profile.role_title).strip()
        profile.department = request.POST.get('department', profile.department).strip()
        profile.bio = request.POST.get('bio', profile.bio).strip()
        profile.preferred_role = request.POST.get('preferred_role', profile.preferred_role)
        request.user.first_name = request.POST.get('first_name', request.user.first_name).strip()
        request.user.last_name = request.POST.get('last_name', request.user.last_name).strip()
        request.user.save()
        profile.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('user_profile:profile')

    total_dispatched = DelegationTask.objects.filter(created_by=request.user).count()
    total_mined = DelegationTask.objects.filter(claimed_by=request.user).count()
    completed_mined = DelegationTask.objects.filter(claimed_by=request.user, status='COMPLETED').count()
    active_mined = DelegationTask.objects.filter(claimed_by=request.user).exclude(status='COMPLETED').count()
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
