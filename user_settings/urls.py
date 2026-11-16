from django.urls import path
from . import views

app_name = 'user_settings'

urlpatterns = [
    path('', views.settings_view, name='settings'),
]