from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction, models
from django.utils import timezone
from datetime import date, timedelta

from .models import Project, StageGate, DelegationTask, TaskComment, TaskLink
from user_profile.routing import workspace_url_name


_STARTER_SEEDED = False


def ensure_starter_project(user):
    """
    Auto-seed helper: If no Project exists in the database, automatically creates
    a realistic starter project ('DeleGate Core Platform v1.0') owned by the current user
    with 3 sequential Stage Gates and realistic starter tasks.
    """
    global _STARTER_SEEDED
    if _STARTER_SEEDED:
        return
    if Project.objects.exists():
        _STARTER_SEEDED = True
        return Project.objects.first()

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
        is_multiclaimable=False,
        due_date=timezone.localdate() + timedelta(days=3),
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
        is_multiclaimable=True,
        due_date=timezone.localdate() + timedelta(days=4),
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
        is_multiclaimable=False,
        due_date=timezone.localdate() - timedelta(days=1),
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
        is_multiclaimable=False,
        due_date=timezone.localdate() + timedelta(days=7),
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
        is_multiclaimable=True,
        due_date=timezone.localdate() + timedelta(days=9),
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
        is_multiclaimable=False,
        due_date=timezone.localdate() + timedelta(days=14),
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
        is_multiclaimable=False,
        due_date=timezone.localdate() + timedelta(days=16),
    )
    return proj


@login_required
def home_view(request):
    """
    Smart hub router: routes user to Claimant or Assigner dashboard
    based on their Profile preferred_role.
    """
    ensure_starter_project(request.user)
    return redirect(workspace_url_name(request.user))


@login_required
def claimant_dashboard(request):
    """
    Claimant Dashboard:
    - Top Stage-Gate Stepper
    - KPI Strip
    - Live 'Mine!' Pool (unlocked OPEN tasks, single-task mining limit unless Multi-Claim)
    - Dimmed locked preview
    - Claimant's personal execution queue with progress notes & submission for manager review
    """
    ensure_starter_project(request.user)
    projects = list(Project.objects.all().order_by('-created_at'))

    project_id = request.GET.get('project')
    project = next((p for p in projects if str(p.pk) == str(project_id)), projects[0]) if projects else None

    if not project:
        return render(request, 'home/claimant_dashboard.html', {
            'projects': [],
            'project': None,
        })

    gates = list(project.gates.annotate(
        total_tasks_count=models.Count('tasks'),
        completed_tasks_count=models.Count('tasks', filter=models.Q(tasks__status='COMPLETED')),
    ).prefetch_related('tasks'))

    tot_tasks = sum(g.total_tasks for g in gates)
    comp_tasks = sum(g.completed_tasks for g in gates)
    project._overall_progress = int(round((comp_tasks / tot_tasks) * 100)) if tot_tasks > 0 else 0

    # Check if user already has an active task (single query)
    user_active_count = DelegationTask.objects.filter(
        claimed_by=request.user,
        status__in=['CLAIMED', 'IN_PROGRESS', 'IN_REVIEW']
    ).count()
    user_has_active_task = user_active_count > 0

    # Live open tasks in unlocked gates (status=OPEN and unclaimed; never COMPLETED)
    open_pool_tasks = list(DelegationTask.objects.filter(
        project=project,
        gate__is_unlocked=True,
        status='OPEN',
        claimed_by__isnull=True,
    ).select_related('gate', 'created_by').prefetch_related('links').order_by('-priority', 'created_at'))

    # Locked upcoming tasks
    locked_preview_tasks = list(DelegationTask.objects.filter(
        project=project,
        gate__is_unlocked=False,
    ).select_related('gate', 'created_by').order_by('gate__order', 'created_at'))

    # Claimant's own mined tasks (evaluated once in memory for all tabs and KPIs)
    all_my_tasks = list(DelegationTask.objects.filter(
        project=project,
        claimed_by=request.user,
    ).select_related('gate', 'created_by').prefetch_related('comments__author', 'links').order_by('-created_at'))

    # In-memory tab counts & KPIs (0 extra database queries)
    my_counts = {
        'all': len(all_my_tasks),
        'claimed': sum(1 for t in all_my_tasks if t.status == 'CLAIMED'),
        'in_progress': sum(1 for t in all_my_tasks if t.status == 'IN_PROGRESS'),
        'in_review': sum(1 for t in all_my_tasks if t.status == 'IN_REVIEW'),
        'completed': sum(1 for t in all_my_tasks if t.status == 'COMPLETED'),
    }

    my_tab = request.GET.get('my_tab', 'all')
    if my_tab == 'claimed':
        my_tasks = [t for t in all_my_tasks if t.status == 'CLAIMED']
    elif my_tab == 'in_progress':
        my_tasks = [t for t in all_my_tasks if t.status == 'IN_PROGRESS']
    elif my_tab == 'in_review':
        my_tasks = [t for t in all_my_tasks if t.status == 'IN_REVIEW']
    elif my_tab == 'completed':
        my_tasks = [t for t in all_my_tasks if t.status == 'COMPLETED']
    else:
        my_tasks = all_my_tasks

    kpi_open = len(open_pool_tasks)
    kpi_my_active = sum(1 for t in all_my_tasks if t.status != 'COMPLETED')
    kpi_points = sum(t.effort_points for t in all_my_tasks if t.status != 'COMPLETED')
    kpi_completed = my_counts['completed']

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
        'all_my_tasks': all_my_tasks,
        'my_tab': my_tab,
        'my_tabs_list': my_tabs_list,
        'user_has_active_task': user_has_active_task,
        'user_active_count': user_active_count,
        'kpi': {
            'open_to_mine': kpi_open,
            'my_mined': kpi_my_active,
            'story_points': kpi_points,
            'completed_by_me': kpi_completed,
        },
        'today': timezone.localdate(),
    })


@login_required
def assigner_dashboard(request):
    """
    Assigner Gate Hub:
    - Stage-Gate Pipeline stepper with Gate Approval & Unlock actions (100% completion enforced)
    - Task Dispatcher Composer with is_multiclaimable flag
    - Gate-grouped task & claimant oversight board with Manager Review (Approve or Return/Dissolve)
    """
    ensure_starter_project(request.user)
    projects = list(Project.objects.all().order_by('-created_at'))

    project_id = request.GET.get('project')
    project = next((p for p in projects if str(p.pk) == str(project_id)), projects[0]) if projects else None

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
            is_multiclaimable = 'is_multiclaimable' in request.POST

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
                is_multiclaimable=is_multiclaimable,
            )
            initial_links = request.POST.get('initial_links', '').strip()
            if initial_links:
                for line in initial_links.splitlines():
                    raw = line.strip()
                    if raw:
                        if not raw.startswith(('http://', 'https://')):
                            raw = 'https://' + raw
                        TaskLink.objects.create(task=task, url=raw)
            multi_note = " [Multi-Claim]" if is_multiclaimable else ""
            messages.success(request, f'Dispatched "{task.title}" ({task.effort_points} pts){multi_note} into {gate.name}.')
            return redirect(f"/home/assign/?project={project.pk}")

    gates = list(project.gates.annotate(
        total_tasks_count=models.Count('tasks'),
        completed_tasks_count=models.Count('tasks', filter=models.Q(tasks__status='COMPLETED')),
    ).prefetch_related('tasks__claimed_by', 'tasks__created_by'))

    tot_tasks = sum(g.total_tasks for g in gates)
    comp_tasks = sum(g.completed_tasks for g in gates)
    project._overall_progress = int(round((comp_tasks / tot_tasks) * 100)) if tot_tasks > 0 else 0

    # Task stream filters
    status_filter = request.GET.get('status', 'all')
    gate_filter = request.GET.get('gate', 'all')

    # Ordered by gate first so the template can group the board under each gate.
    all_tasks = list(DelegationTask.objects.filter(project=project).select_related('gate', 'claimed_by', 'created_by').prefetch_related('comments__author', 'links').order_by('gate__order', '-created_at'))

    if gate_filter != 'all':
        tasks_for_counts = [t for t in all_tasks if str(t.gate_id) == str(gate_filter)]
    else:
        tasks_for_counts = all_tasks

    counts = {
        'all': len(tasks_for_counts),
        'open': sum(1 for t in tasks_for_counts if t.status == 'OPEN'),
        'mined': sum(1 for t in tasks_for_counts if t.status in ('CLAIMED', 'IN_PROGRESS')),
        'review': sum(1 for t in tasks_for_counts if t.status == 'IN_REVIEW'),
        'blocked': sum(1 for t in tasks_for_counts if t.is_blocked),
        'completed': sum(1 for t in tasks_for_counts if t.status == 'COMPLETED'),
    }

    filtered_tasks = tasks_for_counts
    if status_filter == 'open':
        filtered_tasks = [t for t in filtered_tasks if t.status == 'OPEN']
    elif status_filter == 'mined':
        filtered_tasks = [t for t in filtered_tasks if t.status in ('CLAIMED', 'IN_PROGRESS')]
    elif status_filter == 'review':
        filtered_tasks = [t for t in filtered_tasks if t.status == 'IN_REVIEW']
    elif status_filter == 'blocked':
        filtered_tasks = [t for t in filtered_tasks if t.is_blocked]
    elif status_filter == 'completed':
        filtered_tasks = [t for t in filtered_tasks if t.status == 'COMPLETED']

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
        'all_tasks': all_tasks,
        'status_filter': status_filter,
        'gate_filter': gate_filter,
        'filter_tabs': filter_tabs,
        'priority_choices': DelegationTask.PRIORITY_CHOICES,
        'effort_choices': [1, 2, 3, 5, 8],
        'today': timezone.localdate(),
    })


@login_required
@require_POST
def mine_task(request, pk):
    """
    Atomic task-acquisition:
    - Enforces gate is unlocked
    - Enforces task is OPEN and unclaimed
    - Enforces Single-Task Mining Limit:
      If user already has an active task (CLAIMED, IN_PROGRESS, IN_REVIEW),
      blocks mining unless task.is_multiclaimable is True.
    """
    with transaction.atomic():
        task = get_object_or_404(DelegationTask.objects.select_for_update(), pk=pk)

        # 1. Gate unlocked check
        if not task.gate or not task.gate.is_unlocked:
            messages.error(request, f'Cannot mine "{task.title}": Its gate is locked!')
        # 2. Open state check
        elif task.claimed_by is not None or task.status != 'OPEN':
            messages.warning(request, f'Task "{task.title}" was already mined by another claimant.')
        else:
            # 3. Active task limit check
            user_has_active = DelegationTask.objects.filter(
                claimed_by=request.user,
                status__in=['CLAIMED', 'IN_PROGRESS', 'IN_REVIEW']
            ).exists()

            if user_has_active and not task.is_multiclaimable:
                messages.error(
                    request,
                    'Finish or submit your active task first (only Multi-Claim tasks can be stacked).'
                )
            else:
                task.claimed_by = request.user
                task.status = 'CLAIMED'
                task.claimed_at = timezone.now()
                task.save()
                messages.success(request, f'Mined "{task.title}" ({task.effort_points} pts). It\'s in your queue now.')

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'claimant_dashboard')


@login_required
@require_POST
def task_status_action(request, pk):
    """
    Claimant workflow status transitions:
    - start: CLAIMED -> IN_PROGRESS
    - review: IN_PROGRESS -> IN_REVIEW
    - release: claimed task -> OPEN, claimed_by=None
    NOTE: Claimants/Workers CANNOT mark tasks as COMPLETED!
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
        messages.info(request, f'Submitted "{task.title}" for manager review.')
    elif action == 'complete':
        # Block claimants from completing directly
        messages.error(request, 'Workers cannot mark tasks as completed. Please submit for review to allow managers to approve and mark done.')
    elif action == 'release':
        title = task.title
        task.status = 'OPEN'
        task.claimed_by = None
        task.claimed_at = None
        task.save()
        messages.info(request, f'Released "{title}" back to the open pool.')

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'claimant_dashboard')


@login_required
@require_POST
def task_update_notes(request, pk):
    """
    Claimant endpoint to update progress notes on their active task.
    """
    task = get_object_or_404(DelegationTask, pk=pk)
    if task.claimed_by != request.user:
        messages.error(request, 'You can only update notes on your own mined tasks.')
    else:
        notes = request.POST.get('progress_notes', '').strip()
        task.progress_notes = notes
        task.save()
        messages.success(request, f'Progress notes saved for "{task.title}".')

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'claimant_dashboard')


@login_required
@require_POST
def task_manager_review(request, pk):
    """
    Assigner (Manager) Review & Return/Dissolve Logic:
    - Approve & Mark Done: Sets status = 'COMPLETED'.
    - Return with Feedback:
      Case A (Due date NOT passed): Keep worker, status = 'IN_PROGRESS', append feedback as TaskComment.
      Case B (Due date HAS passed): Overdue dissolution: increment dissolved_count += 1, claimed_by = None,
        status = 'OPEN', preserve progress_notes and log system comment.
    """
    task = get_object_or_404(DelegationTask, pk=pk)
    review_action = request.POST.get('review_action')

    if review_action == 'approve':
        task.status = 'COMPLETED'
        task.save()
        TaskComment.objects.create(
            task=task,
            author=request.user,
            body="[Manager Approved]: Task verified and marked as COMPLETED."
        )
        messages.success(request, f'Approved "{task.title}". It\'s marked completed.')

    elif review_action == 'return':
        feedback = request.POST.get('feedback', '').strip() or 'Revisions requested by manager.'
        today = timezone.localdate()

        if task.due_date and task.due_date < today:
            # Case B: Due date HAS passed -> Dissolved back to open pool
            task.dissolved_count += 1
            former_claimant = task.claimed_by.username if task.claimed_by else "Worker"
            task.claimed_by = None
            task.claimed_at = None
            task.status = 'OPEN'
            task.save()

            TaskComment.objects.create(
                task=task,
                author=request.user,
                body=f"[Dissolved to Pool — Overdue]: Returned to open pool with all progress preserved. Feedback: {feedback}"
            )
            messages.warning(
                request,
                f'Task "{task.title}" was overdue (due {task.due_date}) and has been dissolved back to the open pool. Prior work and notes by @{former_claimant} preserved.'
            )
        else:
            # Case A: Due date has NOT passed -> Keep assigned to same worker, status = IN_PROGRESS
            task.status = 'IN_PROGRESS'
            task.save()

            worker_name = task.claimed_by.username if task.claimed_by else "worker"
            TaskComment.objects.create(
                task=task,
                author=request.user,
                body=f"[Returned for Revision]: {feedback}"
            )
            messages.info(
                request,
                f'Task "{task.title}" returned to @{worker_name} for revision.'
            )

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'assigner_dashboard')


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
def task_add_link(request, pk):
    """
    Attach an external URL / tracking link to a task ticket.
    """
    task = get_object_or_404(DelegationTask, pk=pk)
    url = request.POST.get('url', '').strip()
    title = request.POST.get('title', '').strip()

    if url:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        link = TaskLink.objects.create(task=task, url=url, title=title)
        messages.success(request, f'Added link "{link.display_title}" to ticket.')
    else:
        messages.error(request, 'Please provide a valid URL.')

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'home')


@login_required
@require_POST
def task_delete_link(request, link_pk):
    """
    Remove an attached link from a task ticket.
    """
    link = get_object_or_404(TaskLink, pk=link_pk)
    title = link.display_title
    link.delete()
    messages.info(request, f'Removed link "{title}" from ticket.')

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
    Strict Stage-Gate sign-off:
    A StageGate CANNOT be passed or unlock the next gate unless
    gate.total_tasks > 0 AND gate.completed_tasks == gate.total_tasks (100% completed).
    """
    gate = get_object_or_404(StageGate, pk=pk)

    if not gate.ready_to_pass:
        messages.error(
            request,
            f'Cannot pass Gate {gate.order} ({gate.name}): All tasks in this gate must be completed first ({gate.completed_tasks}/{gate.total_tasks} completed).'
        )
        referer = request.META.get('HTTP_REFERER')
        return redirect(referer or 'assigner_dashboard')

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
            f'Gate {gate.order} ({gate.name}) is cleared. Gate {next_gate.order} ({next_gate.name}) is now unlocked for mining.'
        )
    else:
        messages.success(
            request,
            f'Gate {gate.order} ({gate.name}) is cleared. Every gate in "{gate.project.name}" is now complete.'
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
