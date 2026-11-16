from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('task/<int:pk>/status/', views.task_status_update, name='task_status_update'),
    path('task/<int:pk>/delete/', views.task_delete, name='task_delete'),
]
