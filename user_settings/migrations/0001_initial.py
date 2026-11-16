import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='UserSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('default_priority', models.CharField(choices=[('LOW','Low'),('MED','Medium'),('HIGH','High'),('CRIT','Critical')], default='MED', max_length=4)),
                ('compact_view', models.BooleanField(default=False)),
                ('email_notifications', models.BooleanField(default=True)),
                ('weekly_digest', models.BooleanField(default=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='settings', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
