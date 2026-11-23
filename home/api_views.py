import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Subquery
from django.utils import timezone

from .models import DelegationTask, StageGate, Project


def _get_api_user(request):
    """
    Resolve user for API requests:
    1. Authenticated session user
    2. 'X-User' header matching a username
    3. Default to the first active user
    """
    if request.user.is_authenticated:
        return request.user
    cli_user = request.headers.get('X-User')
    if cli_user:
        u = User.objects.filter(username=cli_user).first()
        if u:
            return u
    return User.objects.filter(is_active=True).first()


@require_http_methods(["GET"])
def api_pool_tasks(request):
    """
    GET /home/api/pool/
    Returns all open pool tasks in unlocked gates.
    Uses SQL Subquery and select_related across StageGate, Project, and User.
    """
    project_id = request.GET.get('project')
    if project_id:
        project = Project.objects.filter(pk=project_id).first()
    else:
        project = Project.objects.filter(tasks__isnull=False).distinct().first() or Project.objects.first()

    # Subquery for unlocked gates
    gate_filter = {'is_unlocked': True}
    if project:
        gate_filter['project'] = project
    unlocked_gates_subquery = StageGate.objects.filter(**gate_filter).values('id')

    # Query tasks using Subquery and select_related
    tasks_qs = DelegationTask.objects.filter(
        gate_id__in=Subquery(unlocked_gates_subquery),
        status='OPEN',
        claimed_by__isnull=True,
    )
    if project:
        tasks_qs = tasks_qs.filter(project=project)

    tasks_qs = tasks_qs.select_related('gate', 'project', 'created_by', 'claimed_by').order_by('-priority', 'created_at')

    tasks_data = []
    for t in tasks_qs:
        tasks_data.append({
            'id': t.id,
            'title': t.title,
            'description': t.description,
            'effort_points': t.effort_points,
            'priority': t.priority,
            'status': t.status,
            'is_multiclaimable': t.is_multiclaimable,
            'gate': {
                'id': t.gate.id if t.gate else None,
                'order': t.gate.order if t.gate else None,
                'name': t.gate.name if t.gate else None,
            },
            'project': {
                'id': t.project.id if t.project else None,
                'name': t.project.name if t.project else None,
            },
            'created_by': t.created_by.username if t.created_by else 'system',
            'claimed_by': t.claimed_by.username if t.claimed_by else None,
            'due_date': t.due_date.isoformat() if t.due_date else None,
        })

    return JsonResponse({
        'status': 'ok',
        'count': len(tasks_data),
        'project': project.name if project else None,
        'tasks': tasks_data,
    })


@csrf_exempt
@require_POST
def api_mine_task(request, task_id):
    """
    POST /home/api/tasks/<int:task_id>/mine/
    Atomic task claim endpoint enforcing single-task governance and is_multiclaimable.
    """
    user = _get_api_user(request)
    if not user:
        return JsonResponse({
            'status': 'error',
            'message': 'Authentication required. No user context available.',
        }, status=401)

    with transaction.atomic():
        try:
            task = DelegationTask.objects.select_for_update().get(pk=task_id)
        except DelegationTask.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'Task #{task_id} not found.',
            }, status=404)

        if task.status != 'OPEN' or task.claimed_by is not None:
            return JsonResponse({
                'status': 'error',
                'message': f'Task "{task.title}" is no longer open for mining.',
            }, status=400)

        if task.gate and not task.gate.is_unlocked:
            return JsonResponse({
                'status': 'error',
                'message': f'Task belongs to locked Gate {task.gate.order} ({task.gate.name}).',
            }, status=400)

        # Enforce single active task rule
        user_has_active = DelegationTask.objects.filter(
            claimed_by=user,
            status__in=['CLAIMED', 'IN_PROGRESS', 'IN_REVIEW'],
        ).exists()

        if user_has_active and not task.is_multiclaimable:
            return JsonResponse({
                'status': 'error',
                'message': 'Finish or submit your active task first (only Multi-Claim tasks can be stacked).',
            }, status=400)

        task.status = 'CLAIMED'
        task.claimed_by = user
        task.claimed_at = timezone.now()
        task.save()

    return JsonResponse({
        'status': 'ok',
        'message': f'Successfully mined task #{task.id}: "{task.title}".',
        'task': {
            'id': task.id,
            'title': task.title,
            'status': task.status,
            'claimed_by': user.username,
            'effort_points': task.effort_points,
            'gate_order': task.gate.order if task.gate else None,
        }
    })


@csrf_exempt
@require_POST
def api_pass_gate(request, gate_id):
    """
    POST /home/api/gates/<int:gate_id>/pass/
    Stage-Gate approval endpoint enforcing 100% completion rule.
    """
    user = _get_api_user(request)
    if not user:
        return JsonResponse({
            'status': 'error',
            'message': 'Authentication required.',
        }, status=401)

    with transaction.atomic():
        try:
            gate = StageGate.objects.select_for_update().get(pk=gate_id)
        except StageGate.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'StageGate #{gate_id} not found.',
            }, status=404)

        if not gate.is_unlocked:
            return JsonResponse({
                'status': 'error',
                'message': f'{gate.name} is still locked behind previous gates.',
            }, status=400)

        tot_tasks = gate.tasks.count()
        comp_tasks = gate.tasks.filter(status='COMPLETED').count()

        if tot_tasks == 0:
            return JsonResponse({
                'status': 'error',
                'message': f'Cannot pass {gate.name}: gate has 0 tasks dispatched.',
            }, status=400)

        if comp_tasks < tot_tasks:
            return JsonResponse({
                'status': 'error',
                'message': f'Locked: Complete all tasks in this gate first ({comp_tasks}/{tot_tasks} completed).',
            }, status=400)

        gate.is_passed = True
        gate.save()

        # Cascade unlock the next gate
        next_gate = StageGate.objects.filter(
            project=gate.project,
            order__gt=gate.order,
        ).order_by('order').first()

        next_gate_info = None
        if next_gate and not next_gate.is_unlocked:
            next_gate.is_unlocked = True
            next_gate.unlocked_at = timezone.now()
            next_gate.save()
            next_gate_info = {
                'id': next_gate.id,
                'order': next_gate.order,
                'name': next_gate.name,
            }

    return JsonResponse({
        'status': 'ok',
        'message': f'Successfully approved and passed {gate.name}.',
        'gate': {
            'id': gate.id,
            'order': gate.order,
            'name': gate.name,
            'is_passed': gate.is_passed,
        },
        'next_gate_unlocked': next_gate_info,
    })
