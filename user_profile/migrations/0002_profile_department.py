from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('user_profile', '0001_initial'),
    ]
    operations = [
        migrations.AddField(
            model_name='profile',
            name='department',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
