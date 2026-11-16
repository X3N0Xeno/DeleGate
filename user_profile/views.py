from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Profile

@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        profile.role_title = request.POST.get('role_title', profile.role_title)
        profile.bio = request.POST.get('bio', profile.bio)
        profile.save()
        return redirect('user_profile:profile')

    return render(request, 'user_profile/profile.html', {'profile': profile})