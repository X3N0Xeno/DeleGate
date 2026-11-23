from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('claim/', views.claimant_dashboard, name='claimant_dashboard'),
    path('assign/', views.assigner_dashboard, name='assigner_dashboard'),
    path('mine/<int:pk>/', views.mine_task, name='mine_task'),
    path('task/<int:pk>/status/', views.task_status_action, name='task_status_action'),
    path('task/<int:pk>/notes/', views.task_update_notes, name='task_update_notes'),
    path('task/<int:pk>/review/', views.task_manager_review, name='task_manager_review'),
    path('task/<int:pk>/blocker/', views.task_toggle_blocker, name='task_toggle_blocker'),
    path('task/<int:pk>/comment/', views.task_add_comment, name='task_add_comment'),
    path('task/<int:pk>/link/add/', views.task_add_link, name='task_add_link'),
    path('task/link/<int:link_pk>/delete/', views.task_delete_link, name='task_delete_link'),
    path('task/<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('task/<int:pk>/sprint/', views.task_set_sprint, name='task_set_sprint'),
    path('task/<int:pk>/quick-status/', views.task_quick_status, name='task_quick_status'),
    path('gate/<int:pk>/pass/', views.gate_pass, name='gate_pass'),
    path('project/<int:pk>/add-gate/', views.add_gate, name='add_gate'),
    path('project/<int:pk>/add-sprint/', views.create_sprint, name='create_sprint'),
    path('project/create/', views.create_project, name='create_project'),

    # JSON API endpoints for Rune Rust companion client and external CLI runners
    path('api/pool/', api_views.api_pool_tasks, name='api_pool_tasks'),
    path('api/tasks/<int:task_id>/mine/', api_views.api_mine_task, name='api_mine_task'),
    path('api/gates/<int:gate_id>/pass/', api_views.api_pass_gate, name='api_pass_gate'),
]
