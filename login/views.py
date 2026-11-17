from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from user_profile.routing import workspace_url_name


def _safe_next(request):
    """A ?next= target, only if it stays on this site and isn't the /home/ router."""
    target = request.POST.get('next') or request.GET.get('next') or ''
    if not target:
        return ''
    allowed = url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )
    if not allowed or target.rstrip('/') == reverse('home').rstrip('/'):
        return ''
    return target


def login_view(request):
    if request.user.is_authenticated:
        return redirect(workspace_url_name(request.user))
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Signed in as {user.get_full_name() or user.username}.')
            # Straight into the user's own workspace (Profile.preferred_role),
            # unless they were sent here from a specific page.
            return redirect(_safe_next(request) or workspace_url_name(user))
        else:
            messages.error(request, 'That username and password don\'t match. Check both and try again.')
    else:
        form = AuthenticationForm()
    return render(request, 'login/login.html', {'form': form, 'next': _safe_next(request)})
