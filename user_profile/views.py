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
        request.user.first_name = request.POST.get('first_name', request.user.first_name).strip()
        request.user.last_name = request.POST.get('last_name', request.user.last_name).strip()
        request.user.save()
        profile.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('user_profile:profile')

    total = DelegationTask.objects.filter(assigned_by=request.user).count()
    completed = DelegationTask.objects.filter(assigned_by=request.user, status='COMPLETED').count()
    received = DelegationTask.objects.filter(assigned_to=request.user).count()
    completion_rate = int((completed / total * 100) if total > 0 else 0)

    return render(request, 'user_profile/profile.html', {
        'profile': profile,
        'stats': {
            'total': total,
            'completed': completed,
            'received': received,
            'completion_rate': completion_rate,
        }
    })
