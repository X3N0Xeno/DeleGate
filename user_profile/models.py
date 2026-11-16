from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = [
        ('CLAIMANT', 'Claimant (Mine!)'),
        ('ASSIGNER', 'Assigner (Gate Hub)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    preferred_role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='CLAIMANT')
    role_title = models.CharField(max_length=100, default='Team Member')
    department = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.preferred_role})"
