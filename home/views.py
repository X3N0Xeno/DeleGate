from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import DelegationTask
from datetime import date

@login_required
def home_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if title:
            assigned_to_id = request.POST.get('assigned_to')
            assigned_to = None
            if assigned_to_id:
                try:
                    assigned_to = User.objects.get(pk=assigned_to_id)
                except User.DoesNotExist:
                    pass
            DelegationTask.objects.create(
                title=title,
                description=request.POST.get('description', '').strip(),
                assigned_by=request.user,
                assigned_to=assigned_to,
                priority=request.POST.get('priority', 'MED'),
                due_date=request.POST.get('due_date') or None,
            )
            messages.success(request, f'Task "{title}" delegated successfully.')
        return redirect('home')

    tab = request.GET.get('tab', 'all')
    all_tasks = DelegationTask.objects.select_related('assigned_by', 'assigned_to').order_by('-created_at')

    if tab == 'mine':
        tasks = all_tasks.filter(assigned_to=request.user)
    elif tab == 'delegated':
        tasks = all_tasks.filter(assigned_by=request.user)
    elif tab == 'completed':
        tasks = all_tasks.filter(status='COMPLETED')
    else:
        tasks = all_tasks

    today = date.today()
    total_active = all_tasks.exclude(status='COMPLETED').count()
    in_progress = all_tasks.filter(status='IN_PROGRESS').count()
    due_soon = all_tasks.exclude(status='COMPLETED').filter(due_date__lte=today).count()
    completed = all_tasks.filter(status='COMPLETED').count()

    users = User.objects.exclude(pk=request.user.pk).order_by('username')

    stats = {
        'active': total_active,
        'in_progress': in_progress,
        'due_soon': due_soon,
        'completed': completed,
    }

    tab_counts = {
        'all': all_tasks.count(),
        'mine': all_tasks.filter(assigned_to=request.user).count(),
        'delegated': all_tasks.filter(assigned_by=request.user).count(),
        'completed': all_tasks.filter(status='COMPLETED').count(),
    }

    tabs = [
        {'key': 'all', 'label': 'All', 'count': tab_counts['all'], 'active': (tab == 'all')},
        {'key': 'mine', 'label': 'Assigned to Me', 'count': tab_counts['mine'], 'active': (tab == 'mine')},
        {'key': 'delegated', 'label': 'Delegated by Me', 'count': tab_counts['delegated'], 'active': (tab == 'delegated')},
        {'key': 'completed', 'label': 'Completed', 'count': tab_counts['completed'], 'active': (tab == 'completed')},
    ]

    return render(request, 'home/home.html', {
        'tasks': tasks,
        'tab': tab,
        'tabs': tabs,
        'users': users,
        'stats': stats,
        'tab_counts': tab_counts,
        'today': today,
        'priority_choices': DelegationTask.PRIORITY_CHOICES,
        'tab_list': [
            ('all', 'All'),
            ('mine', 'Assigned to Me'),
            ('delegated', 'Delegated by Me'),
            ('completed', 'Completed'),
        ],
        'stats_list': [
            ('Active Tasks', stats['active'], 'var(--brand)'),
            ('In Progress', stats['in_progress'], 'var(--amber)'),
            ('Due Soon', stats['due_soon'], 'var(--critical)'),
            ('Completed', stats['completed'], 'var(--accent)'),
        ],
    })


@login_required
@require_POST
def task_status_update(request, pk):
    task = get_object_or_404(DelegationTask, pk=pk)
    current = task.status
    cycle = {'PENDING': 'IN_PROGRESS', 'IN_PROGRESS': 'COMPLETED', 'COMPLETED': 'PENDING'}
    task.status = cycle.get(current, 'PENDING')
    task.save()
    return JsonResponse({'status': task.status, 'display': task.get_status_display()})


@login_required
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(DelegationTask, pk=pk)
    title = task.title
    task.delete()
    messages.success(request, f'Task "{title}" deleted.')
    return redirect('home')
