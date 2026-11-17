"""Template context shared by every page: saved theme, density and the user's workspace."""
from django.urls import reverse

from user_profile.models import Profile
from .models import UserSettings

DEFAULT_THEME = 'aether'
_WORKSPACES = {
    'CLAIMANT': ('claimant_dashboard', 'Open work'),
    'ASSIGNER': ('assigner_dashboard', 'Gate hub'),
}


def ui(request):
    user = getattr(request, 'user', None)
    ctx = {'ui_theme': DEFAULT_THEME, 'ui_compact': False, 'ui_workspace': None}
    if user is None or not user.is_authenticated:
        return ctx

    session = getattr(request, 'session', None)
    prefs = session.get('dg_prefs') if session else None
    if prefs is None:
        prefs = UserSettings.objects.filter(user=user).values('theme', 'compact_view').first() or {'theme': DEFAULT_THEME, 'compact_view': False}
        if session is not None:
            session['dg_prefs'] = prefs

    ctx['ui_theme'] = prefs.get('theme') or DEFAULT_THEME
    ctx['ui_compact'] = prefs.get('compact_view', False)

    role = session.get('dg_role') if session else None
    if role is None:
        role = Profile.objects.filter(user=user).values_list('preferred_role', flat=True).first() or 'CLAIMANT'
        if session is not None:
            session['dg_role'] = role
    # The workspace being viewed wins over the default, so the role switch
    # shows exactly one workspace entry at a time.
    match = getattr(request, 'resolver_match', None)
    viewing = match.url_name if match else ''
    for key, (url_name, _label) in _WORKSPACES.items():
        if viewing == url_name:
            role = key
    other = 'ASSIGNER' if role == 'CLAIMANT' else 'CLAIMANT'
    ctx['ui_workspace'] = {
        'role': role,
        'url_name': _WORKSPACES[role][0],
        'label': _WORKSPACES[role][1],
        'url': reverse(_WORKSPACES[role][0]),
        'other_url': reverse(_WORKSPACES[other][0]),
        'other_label': _WORKSPACES[other][1],
        'other_role': other,
    }
    return ctx
