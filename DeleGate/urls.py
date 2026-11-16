from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('login')),
    path('login/', include('login.urls')),
    path('register/', include('register.urls')),
    path('home/', include('home.urls')),
    path('profile/', include('user_profile.urls')),
    path('settings/', include('user_settings.urls')),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
