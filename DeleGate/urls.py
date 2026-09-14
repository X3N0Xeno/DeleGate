from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('login')),
    path('login/', include('login.urls')),
    path('register/', include('register.urls')),
    path('home/', include('home.urls')),
]