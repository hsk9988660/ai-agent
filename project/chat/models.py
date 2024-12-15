from django.db import models

class KnowledgeBase(models.Model):
    content = models.TextField()

    def __str__(self):
        return f"Knowledge Base (ID: {self.id})"


# from django.db import models

# class CustomUser(models.Model):
#     username = models.CharField(max_length=255, unique=True)
#     password = models.CharField(max_length=255)

#     class Meta:
#         db_table = 'users'  # Map to the existing PostgreSQL table
