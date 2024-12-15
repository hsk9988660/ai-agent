from django.urls import path
from . import views
# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import KnowledgeBaseFileView

urlpatterns = [
    path('upload/', views.KnowledgeBaseUploadView.as_view(), name='upload'),
    path('query/', views.QueryView.as_view(), name='query'),
    path('admin-login/', views.AdminLoginView.as_view(), name='admin-login'),
    path('admin-logout/', views.AdminLogoutView.as_view(), name='admin-logout'),
    path('file/', KnowledgeBaseFileView.as_view(), name='file-list'),  # GET all files
    path('file/<int:pk>/', KnowledgeBaseFileView.as_view(), name='file-detail'),  # DELETE/PUT for specific files
    # path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

]
