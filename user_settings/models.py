from django.db import models
from django.contrib.auth.models import User

class UserSettings(models.Model):
    PRIORITY_CHOICES = [('LOW','Low'),('MED','Medium'),('HIGH','High'),('CRIT','Critical')]
    DASHBOARD_CHOICES = [('CLAIMANT', 'Claimant Pool (Mine!)'), ('ASSIGNER', 'Assigner Gate Hub')]
    THEME_CHOICES = [
        ('kyoto', 'Kyoto Moss'),
        ('shiroi', 'Shiroi Stone'),
        ('hinoki', 'Hinoki Sand'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    default_priority = models.CharField(max_length=4, choices=PRIORITY_CHOICES, default='MED')
    default_dashboard = models.CharField(max_length=10, choices=DASHBOARD_CHOICES, default='CLAIMANT')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='kyoto')
    compact_view = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    weekly_digest = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.username} settings'
