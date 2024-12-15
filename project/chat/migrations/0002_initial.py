from django.db import migrations
from django.contrib.auth.models import User

def create_admin_user(apps, schema_editor):
    if not User.objects.filter(username='Admin').exists():
        User.objects.create_superuser(
            username='Admin',
            password='Admin@1234',
            email='admin@example.com'
        )

class Migration(migrations.Migration):
    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_admin_user),
    ]
