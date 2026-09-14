from django.urls import path
from .views import home_view, logout_view

urlpatterns = [
    path('', home_view, name='home'),
    path('logout/', logout_view, name='logout'),
]