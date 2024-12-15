from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'

    # def ready(self):
    #     from .models import CustomUser  # Import the model for the `users` table

    #     if not CustomUser.objects.filter(username='admin').exists():
    #         CustomUser.objects.create(username='admin', password='Admin@1234')
    #         print("Default admin user created in the custom `users` table.")
