"""Role routing: one place that decides which workspace a user lands in."""
from django.urls import reverse

from .models import Profile

WORKSPACE_URL_NAMES = {
    'CLAIMANT': 'claimant_dashboard',
    'ASSIGNER': 'assigner_dashboard',
}
VALID_ROLES = tuple(WORKSPACE_URL_NAMES)


def workspace_url_name(user):
    """URL name of the dashboard for the user's preferred role."""
    profile, _ = Profile.objects.get_or_create(user=user)
    return WORKSPACE_URL_NAMES.get(profile.preferred_role, 'claimant_dashboard')


def workspace_url(user):
    return reverse(workspace_url_name(user))
