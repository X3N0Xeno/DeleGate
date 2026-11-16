from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction, models
from django.utils import timezone
from datetime import date, timedelta

from .models import Project, StageGate, DelegationTask, TaskComment
from user_profile.models import Profile


def ensure_starter_project(user):
    """
    Auto-seed helper: If no Project exists in the database, automatically creates
    a realistic starter project ('DeleGate Core Platform v1.0') owned by the current user
    with 3 sequential Stage Gates and realistic starter tasks.
    """
    if Project.objects.count() == 0:
        proj = Project.objects.create(
            name="DeleGate Core Platform v1.0",
            description="Mission-critical cloud delegation engine featuring Stage-Gate governance and collaborative claimant mining.",
            owner=user,
        )

        # Gate 1: Unlocked
        g1 = StageGate.objects.create(
            project=proj,
            order=1,
            name="Gate 1: Discovery & System Architecture",
            exit_criteria="System architecture signed off & baseline specs approved",
            is_unlocked=True,
            is_passed=False,
            unlocked_at=timezone.now(),
        )
        DelegationTask.objects.create(
            project=proj,
            gate=g1,
            title="Design Stage-Gate Data Schema & Locking Invariants",
            description="Specify database constraints, gate readiness triggers, and atomic claim transactions.",
            created_by=user,
            priority="HIGH",
            effort_points=5,
            status="OPEN",
            due_date=date.today() + timedelta(days=3),
        )
        DelegationTask.objects.create(
            project=proj,
            gate=g1,
            title="Wireframe Claimant Acquisition Pool & Visual Stepper",
            description="Create high-fidelity zen component mockups for live mining cards and stepper indicators.",
            created_by=user,
            priority="MED",
            effort_points=3,
            status="OPEN",
            due_date=date.today() + timedelta(days=4),
        )
        DelegationTask.objects.create(
            project=proj,
            gate=g1,
            title="Product Requirements & Scope Alignment",
            description="Synthesize stakeholder objectives into verifiable exit criteria.",
            created_by=user,
            claimed_by=user,
            priority="LOW",
            effort_points=2,
            status="COMPLETED",
            due_date=date.today() - timedelta(days=1),
            claimed_at=timezone.now(),
        )

        # Gate 2: Locked behind Gate 1
        g2 = StageGate.objects.create(
            project=proj,
            order=2,
            name="Gate 2: Engine & API Execution",
            exit_criteria="All core endpoints tested with 100% contract compliance",
            is_unlocked=False,
            is_passed=False,
        )
        DelegationTask.objects.create(
            project=proj,
            gate=g2,
            title="Build Concurrency-Safe Mining & Unlock Controller",
            description="Implement atomic status transitions to prevent race conditions during peak mining.",
            created_by=user,
            priority="CRIT",
            effort_points=8,
            status="OPEN",
            due_date=date.today() + timedelta(days=7),
        )
        DelegationTask.objects.create(
            project=proj,
            gate=g2,
            title="Integrate Gate Sign-off Workflow & Cascade Unlocks",
            description="Automate sequential unlocking of Gate N+1 upon approval of Gate N.",
            created_by=user,
            priority="HIGH",
            effort_points=5,
            status="OPEN",
            due_date=date.today() + timedelta(days=9),
        )

        # Gate 3: Locked behind Gate 2
        g3 = StageGate.objects.create(
            project=proj,
            order=3,
            name="Gate 3: Security Audit & Production Launch",
            exit_criteria="Penetration testing cleared & monitoring alerts configured",
            is_unlocked=False,
            is_passed=False,
        )
        DelegationTask.objects.create(
            project=proj,
            gate=g3,
            title="Execute Role-Based Access Boundary & Secret Audits",
            description="Verify permissions isolation between claimants, assigners, and system administrators.",
            created_by=user,
            priority="HIGH",
            effort_points=5,
            status="OPEN",
            due_date=date.today() + timedelta(days=14),
        )
        DelegationTask.objects.create(
            project=proj,
            gate=g3,
            title="Deploy Production Topology & Health Checks",
            description="Configure telemetry dashboards, error rate alerting, and load-balancer probes.",
            created_by=user,
            priority="MED",
            effort_points=3,
            status="OPEN",
            due_date=date.today() + timedelta(days=16),
        )
        return proj

    return Project.objects.first()


@login_required
def home_view(request):
    """
    Smart hub router: routes user to Claimant or Assigner dashboard
    based on their Profile preferred_role.
    """
    ensure_starter_project(request.user)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if profile.preferred_role == 'ASSIGNER':
        return redirect('assigner_dashboard')
    return redirect('claimant_dashboard')


@login_required
def claimant_dashboard(request):
    """
    Claimant Dashboard:
    - Top Stage-Gate Stepper
    - KPI Strip
    - Live 'Mine!' Pool (unlocked OPEN tasks)
    - Dimmed locked preview
    - Claimant's personal execution queue with 1-click status transitions & blocker toggles
    """
    ensure_starter_project(request.user)
    projects = Project.objects.all().order_by('-created_at')

    project_id = request.GET.get('project')
    project = projects.filter(pk=project_id).first() if project_id else projects.first()

    if not project:
        return render(request, 'home/claimant_dashboard.html', {
            'projects': [],
            'project': None,
        })

    gates = project.gates.all().prefetch_related('tasks')

    # Live open tasks in unlocked gates (waiting to be mined)
    open_pool_tasks = DelegationTask.objects.filter(
        project=project,
        gate__is_unlocked=True,
        status='OPEN',
        claimed_by__isnull=True,
    ).select_related('gate', 'created_by').order_by('-priority', 'created_at')

    # Locked upcoming tasks
    locked_preview_tasks = DelegationTask.objects.filter(
        project=project,
        gate__is_unlocked=False,
    ).select_related('gate', 'created_by').order_by('gate__order', 'created_at')

    # Claimant's own mined tasks
    my_tasks_qs = DelegationTask.objects.filter(
        project=project,
        claimed_by=request.user,
    ).select_related('gate', 'created_by').prefetch_related('comments__author').order_by('-created_at')

    my_tab = request.GET.get('my_tab', 'all')
    if my_tab == 'claimed':
        my_tasks = my_tasks_qs.filter(status='CLAIMED')
    elif my_tab == 'in_progress':
        my_tasks = my_tasks_qs.filter(status='IN_PROGRESS')
    elif my_tab == 'in_review':
        my_tasks = my_tasks_qs.filter(status='IN_REVIEW')
    elif my_tab == 'completed':
        my_tasks = my_tasks_qs.filter(status='COMPLETED')
    else:
        my_tasks = my_tasks_qs

    # KPI counts
    kpi_open = open_pool_tasks.count()
    kpi_my_active = my_tasks_qs.exclude(status='COMPLETED').count()
    kpi_points = sum(my_tasks_qs.exclude(status='COMPLETED').values_list('effort_points', flat=True))
    kpi_completed = my_tasks_qs.filter(status='COMPLETED').count()

    # Mined tab counts
    my_counts = {
        'all': my_tasks_qs.count(),
        'claimed': my_tasks_qs.filter(status='CLAIMED').count(),
        'in_progress': my_tasks_qs.filter(status='IN_PROGRESS').count(),
        'in_review': my_tasks_qs.filter(status='IN_REVIEW').count(),
        'completed': my_tasks_qs.filter(status='COMPLETED').count(),
    }

    my_tabs_list = [
        {'key': 'all', 'label': 'All Mined', 'count': my_counts['all'], 'active': (my_tab == 'all')},
        {'key': 'claimed', 'label': 'Claimed', 'count': my_counts['claimed'], 'active': (my_tab == 'claimed')},
        {'key': 'in_progress', 'label': 'In Progress', 'count': my_counts['in_progress'], 'active': (my_tab == 'in_progress')},
        {'key': 'in_review', 'label': 'In Review', 'count': my_counts['in_review'], 'active': (my_tab == 'in_review')},
        {'key': 'completed', 'label': 'Completed', 'count': my_counts['completed'], 'active': (my_tab == 'completed')},
    ]

    return render(request, 'home/claimant_dashboard.html', {
        'projects': projects,
        'project': project,
        'gates': gates,
        'open_pool_tasks': open_pool_tasks,
        'locked_preview_tasks': locked_preview_tasks,
        'my_tasks': my_tasks,
        'my_tab': my_tab,
        'my_tabs_list': my_tabs_list,
        'kpi': {
            'open_to_mine': kpi_open,
            'my_mined': kpi_my_active,
            'story_points': kpi_points,
            'completed_by_me': kpi_completed,
        },
        'today': date.today(),
    })


@login_required
def assigner_dashboard(request):
    """
    Assigner Gate Hub:
    - Stage-Gate Pipeline stepper with Gate Approval & Unlock actions
    - Task Dispatcher Composer (left column)
    - Gate-grouped task & claimant oversight board (right column)
    """
    ensure_starter_project(request.user)
    projects = Project.objects.all().order_by('-created_at')

    project_id = request.GET.get('project')
    project = projects.filter(pk=project_id).first() if project_id else projects.first()

    if not project:
        return render(request, 'home/assigner_dashboard.html', {
            'projects': [],
            'project': None,
        })

    # Handle Task Creation from Composer
    if request.method == 'POST' and request.POST.get('action') == 'dispatch_task':
        title = request.POST.get('title', '').strip()
        gate_id = request.POST.get('gate')
        gate = StageGate.objects.filter(pk=gate_id, project=project).first()
        if title and gate:
            effort = int(request.POST.get('effort_points', 3))
            priority = request.POST.get('priority', 'MED')
            due_date = request.POST.get('due_date') or None
            desc = request.POST.get('description', '').strip()

            task = DelegationTask.objects.create(
                project=project,
                gate=gate,
                title=title,
                description=desc,
                created_by=request.user,
                priority=priority,
                effort_points=effort,
                due_date=due_date,
                status='OPEN',
            )
            messages.success(request, f'Dispatched "{task.title}" ({task.effort_points} pts) into {gate.name}.')
            return redirect(f"/home/assign/?project={project.pk}")

    gates = project.gates.all().prefetch_related('tasks__claimed_by', 'tasks__created_by')

    # Task stream filters
    status_filter = request.GET.get('status', 'all')
    gate_filter = request.GET.get('gate', 'all')

    tasks_qs = DelegationTask.objects.filter(project=project).select_related('gate', 'claimed_by', 'created_by').prefetch_related('comments__author').order_by('-created_at')

    if gate_filter != 'all':
        tasks_qs = tasks_qs.filter(gate_id=gate_filter)

    counts = {
        'all': tasks_qs.count(),
        'open': tasks_qs.filter(status='OPEN').count(),
        'mined': tasks_qs.filter(status__in=['CLAIMED', 'IN_PROGRESS']).count(),
        'review': tasks_qs.filter(status='IN_REVIEW').count(),
        'blocked': tasks_qs.filter(is_blocked=True).count(),
        'completed': tasks_qs.filter(status='COMPLETED').count(),
    }

    if status_filter == 'open':
        filtered_tasks = tasks_qs.filter(status='OPEN')
    elif status_filter == 'mined':
        filtered_tasks = tasks_qs.filter(status__in=['CLAIMED', 'IN_PROGRESS'])
    elif status_filter == 'review':
        filtered_tasks = tasks_qs.filter(status='IN_REVIEW')
    elif status_filter == 'blocked':
        filtered_tasks = tasks_qs.filter(is_blocked=True)
    elif status_filter == 'completed':
        filtered_tasks = tasks_qs.filter(status='COMPLETED')
    else:
        filtered_tasks = tasks_qs

    filter_tabs = [
        {'key': 'all', 'label': 'All Tasks', 'count': counts['all'], 'active': (status_filter == 'all')},
        {'key': 'open', 'label': 'Open in Pool', 'count': counts['open'], 'active': (status_filter == 'open')},
        {'key': 'mined', 'label': 'Mined / In Progress', 'count': counts['mined'], 'active': (status_filter == 'mined')},
        {'key': 'review', 'label': 'In Review', 'count': counts['review'], 'active': (status_filter == 'review')},
        {'key': 'blocked', 'label': 'Blocked', 'count': counts['blocked'], 'active': (status_filter == 'blocked')},
        {'key': 'completed', 'label': 'Completed', 'count': counts['completed'], 'active': (status_filter == 'completed')},
    ]

    return render(request, 'home/assigner_dashboard.html', {
        'projects': projects,
        'project': project,
        'gates': gates,
        'tasks': filtered_tasks,
        'status_filter': status_filter,
        'gate_filter': gate_filter,
        'filter_tabs': filter_tabs,
        'priority_choices': DelegationTask.PRIORITY_CHOICES,
        'effort_choices': [1, 2, 3, 5, 8],
        'today': date.today(),
    })


@login_required
@require_POST
def mine_task(request, pk):
    """
    Atomic task-acquisition:
    Checks if gate is unlocked and task is unclaimed.
    Atomically updates claimed_by, status to CLAIMED, claimed_at.
    """
    with transaction.atomic():
        task = get_object_or_404(DelegationTask.objects.select_for_update(), pk=pk)

        if not task.gate or not task.gate.is_unlocked:
            messages.error(request, f'Cannot mine "{task.title}": Its gate is locked!')
        elif task.claimed_by is not None or task.status != 'OPEN':
            messages.warning(request, f'Task "{task.title}" was already mined by another claimant.')
        else:
            task.claimed_by = request.user
            task.status = 'CLAIMED'
            task.claimed_at = timezone.now()
            task.save()
            messages.success(request, f'⚡ Mined! "{task.title}" ({task.effort_points} pts) is now in your active queue!')

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'claimant_dashboard')


@login_required
@require_POST
def task_status_action(request, pk):
    """
    Claimant & Assigner status transitions:
    - start: CLAIMED -> IN_PROGRESS
    - review: IN_PROGRESS -> IN_REVIEW
    - complete: IN_REVIEW / IN_PROGRESS -> COMPLETED
    - release: claimed task -> OPEN, claimed_by=None
    """
    task = get_object_or_404(DelegationTask, pk=pk)
    action = request.POST.get('action')

    if action == 'start':
        task.status = 'IN_PROGRESS'
        task.save()
        messages.success(request, f'Started work on "{task.title}".')
    elif action == 'review':
        task.status = 'IN_REVIEW'
        task.save()
        messages.info(request, f'Submitted "{task.title}" for review.')
    elif action == 'complete':
        task.status = 'COMPLETED'
        task.save()
        messages.success(request, f'🎉 "{task.title}" marked as completed!')
    elif action == 'release':
        title = task.title
        task.status = 'OPEN'
        task.claimed_by = None
        task.claimed_at = None
        task.save()
        messages.info(request, f'Released "{title}" back to the open pool.')

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'home')


@login_required
@require_POST
def task_toggle_blocker(request, pk):
    """
    Flag or clear a blocker on a task.
    """
    task = get_object_or_404(DelegationTask, pk=pk)
    if task.is_blocked:
        task.is_blocked = False
        task.blocker_note = ''
        task.save()
        messages.success(request, f'Blocker cleared on "{task.title}".')
    else:
        note = request.POST.get('blocker_note', '').strip() or 'Blocked by dependency'
        task.is_blocked = True
        task.blocker_note = note
        task.save()
        messages.warning(request, f'Flagged blocker on "{task.title}": {note}')

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'home')


@login_required
@require_POST
def task_add_comment(request, pk):
    """
    Add a comment to a task activity thread.
    """
    task = get_object_or_404(DelegationTask, pk=pk)
    body = request.POST.get('body', '').strip()
    if body:
        TaskComment.objects.create(task=task, author=request.user, body=body)
        messages.success(request, 'Comment added.')

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'home')


@login_required
@require_POST
def task_delete(request, pk):
    """
    Delete a task (available to assigner/owner).
    """
    task = get_object_or_404(DelegationTask, pk=pk)
    title = task.title
    task.delete()
    messages.success(request, f'Task "{title}" removed.')

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'assigner_dashboard')


@login_required
@require_POST
def gate_pass(request, pk):
    """
    Stage-Gate sign-off:
    Marks current gate as passed (is_passed=True) and automatically
    unlocks the next sequential gate (is_unlocked=True).
    """
    gate = get_object_or_404(StageGate, pk=pk)
    gate.is_passed = True
    gate.save()

    next_gate = StageGate.objects.filter(
        project=gate.project,
        order__gt=gate.order,
    ).order_by('order').first()

    if next_gate:
        next_gate.is_unlocked = True
        next_gate.unlocked_at = timezone.now()
        next_gate.save()
        messages.success(
            request,
            f'🎉 Gate {gate.order} ({gate.name}) approved and passed! Gate {next_gate.order} ({next_gate.name}) is now unlocked for mining.'
        )
    else:
        messages.success(
            request,
            f'🎉 Gate {gate.order} ({gate.name}) passed! All gates in "{gate.project.name}" are successfully completed!'
        )

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'assigner_dashboard')


@login_required
@require_POST
def add_gate(request, pk):
    """
    Add a new Stage Gate to a project.
    """
    project = get_object_or_404(Project, pk=pk)
    name = request.POST.get('name', '').strip()
    exit_criteria = request.POST.get('exit_criteria', '').strip()

    if name:
        max_order = project.gates.aggregate(models.Max('order'))['order__max'] or 0
        new_gate = StageGate.objects.create(
            project=project,
            order=max_order + 1,
            name=name,
            exit_criteria=exit_criteria,
            is_unlocked=False,
            is_passed=False,
        )
        messages.success(request, f'Created Gate {new_gate.order}: "{name}".')

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or f"/home/assign/?project={project.pk}")


@login_required
@require_POST
def create_project(request):
    """
    Create a new Project with an initial unlocked Gate 1.
    """
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()

    if name:
        proj = Project.objects.create(
            name=name,
            description=description,
            owner=request.user,
        )
        StageGate.objects.create(
            project=proj,
            order=1,
            name="Gate 1: Initiation & Architecture",
            exit_criteria="Baseline specs approved",
            is_unlocked=True,
            is_passed=False,
            unlocked_at=timezone.now(),
        )
        messages.success(request, f'Project "{name}" created with Gate 1 unlocked.')
        return redirect(f"/home/assign/?project={proj.pk}")

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'assigner_dashboard')
