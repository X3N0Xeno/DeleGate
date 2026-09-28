""""
Entities (9):
    auth_user        -> django.contrib.auth.models.User (built in, not redefined)
    user_profile     -> UserProfile
    user_settings    -> UserSettings
    project          -> Project
    project_member   -> ProjectMember
    gate             -> Gate
    task             -> Task
    handover_report  -> HandoverReport
    audit_log        -> AuditLog

"""

from django.conf import settings
from django.db import models
from django.db.models import Q

# auth_user is Django's standard auth table.
User = settings.AUTH_USER_MODEL


# ---------------------------------------------------------------------------
# Entity 2: user_profile   (auth_user 1 : 1 user_profile)
# ---------------------------------------------------------------------------
class UserProfile(models.Model):
    class Role(models.TextChoices):
        MANAGER = "Manager", "Manager"
        LEAD = "Lead", "Lead"
        CONTRIBUTOR = "Contributor", "Contributor"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    full_name = models.CharField(max_length=150, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.CONTRIBUTOR,
    )
    # Enforces the single-active-task cap (anti-hoarding rule).
    active_task = models.ForeignKey(
        "Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_for_profiles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profile"

    def __str__(self):
        return f"Profile<{self.user_id}> {self.full_name or ''}".strip()


# ---------------------------------------------------------------------------
# Entity 3: user_settings   (auth_user 1 : 1 user_settings)
# ---------------------------------------------------------------------------
class UserSettings(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="settings",
    )
    dark_mode = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    auto_claim_reminder = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_settings"
        verbose_name_plural = "user settings"

    def __str__(self):
        return f"Settings<{self.user_id}>"


# ---------------------------------------------------------------------------
# Entity 4: project   (auth_user 1 : N project via owner_id)
# ---------------------------------------------------------------------------
class Project(models.Model):
    class Status(models.TextChoices):
        PLANNING = "PLANNING", "Planning"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        ARCHIVED = "ARCHIVED", "Archived"

    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    owner = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="owned_projects",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PLANNING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Members reachable through the ProjectMember junction table (N : N).
    members = models.ManyToManyField(
        User,
        through="ProjectMember",
        related_name="projects",
    )

    class Meta:
        db_table = "project"

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# Entity 5: project_member   (junction: auth_user N : N project)
# ---------------------------------------------------------------------------
class ProjectMember(models.Model):
    class RoleInProject(models.TextChoices):
        MANAGER = "MANAGER", "Manager"
        CONTRIBUTOR = "CONTRIBUTOR", "Contributor"
        VIEWER = "VIEWER", "Viewer"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )
    role_in_project = models.CharField(
        max_length=30,
        choices=RoleInProject.choices,
        default=RoleInProject.CONTRIBUTOR,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project_member"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                name="uq_project_member_project_user",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} in {self.project_id} ({self.role_in_project})"


# ---------------------------------------------------------------------------
# Entity 6: gate   (project 1 : N gate)
# ---------------------------------------------------------------------------
class Gate(models.Model):
    class Status(models.TextChoices):
        LOCKED = "LOCKED", "Locked"
        OPEN = "OPEN", "Open"
        IN_REVIEW = "IN_REVIEW", "In review"
        CLEARED = "CLEARED", "Cleared"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="gates",
    )
    sequence_order = models.IntegerField()
    title = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.LOCKED,
    )
    deadline = models.DateTimeField(null=True, blank=True)
    cleared_at = models.DateTimeField(null=True, blank=True)
    cleared_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cleared_gates",
    )

    class Meta:
        db_table = "gate"
        ordering = ["project", "sequence_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "sequence_order"],
                name="uq_gate_project_sequence_order",
            ),
        ]

    def __str__(self):
        return f"{self.title} [{self.status}]"


# ---------------------------------------------------------------------------
# Entity 7: task   (gate 1 : N task, self-ref parent_task_id, user claims)
# ---------------------------------------------------------------------------
class Task(models.Model):
    class Status(models.TextChoices):
        UNCLAIMED = "UNCLAIMED", "Unclaimed"
        CLAIMED = "CLAIMED", "Claimed"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        SUBMITTED = "SUBMITTED", "Submitted"
        COMPLETED = "COMPLETED", "Completed"
        EXPIRED = "EXPIRED", "Expired"
        EXPIRED_RESOLVED = "EXPIRED_RESOLVED", "Expired (resolved)"

    gate = models.ForeignKey(
        Gate,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    # Self-referencing FK: residual tickets point back to the expired parent.
    parent_task = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="residual_tasks",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    claimed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claimed_tasks",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.UNCLAIMED,
    )
    # Managerial override: lets a member already holding a task claim this one.
    allow_multiclaim = models.BooleanField(default=False)
    # True when auto-spawned from an expiration delta.
    is_residual = models.BooleanField(default=False)
    claimed_at = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "task"

    def __str__(self):
        return f"{self.title} [{self.status}]"


# ---------------------------------------------------------------------------
# Entity 8: handover_report
#   task 1 : 1 handover_report   (an expired task has exactly one report)
#   spawned_task 0..1 : 1 task   (pointer to the residual ticket)
# ---------------------------------------------------------------------------
class HandoverReport(models.Model):
    task = models.OneToOneField(
        Task,
        on_delete=models.CASCADE,
        related_name="handover_report",
    )
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="handover_reports",
    )
    work_done = models.TextField()
    work_remaining = models.TextField()
    blocker_reason = models.TextField()
    percent_completed = models.IntegerField()
    spawned_task = models.OneToOneField(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="spawned_from_report",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "handover_report"
        constraints = [
            models.CheckConstraint(
                condition=Q(percent_completed__gte=0) & Q(percent_completed__lt=100),
                name="ck_handover_percent_completed_0_99",
            ),
        ]

    def __str__(self):
        return f"Handover for task {self.task_id} ({self.percent_completed}%)"


# ---------------------------------------------------------------------------
# Entity 9: audit_log   (project 1 : N audit_log, auth_user 1 : N audit_log)
# ---------------------------------------------------------------------------
class AuditLog(models.Model):
    class EntityType(models.TextChoices):
        TASK = "TASK", "Task"
        GATE = "GATE", "Gate"
        HANDOVER = "HANDOVER", "Handover"
        OVERRIDE = "OVERRIDE", "Override"

    class Action(models.TextChoices):
        CLAIM = "CLAIM", "Claim"
        RELEASE = "RELEASE", "Release"
        COMPLETE = "COMPLETE", "Complete"
        EXPIRE = "EXPIRE", "Expire"
        SPLIT = "SPLIT", "Split"
        GATE_CLEAR = "GATE_CLEAR", "Gate clear"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="audit_logs",
    )
    entity_type = models.CharField(max_length=50, choices=EntityType.choices)
    entity_id = models.BigIntegerField()
    action = models.CharField(max_length=50, choices=Action.choices)
    old_state = models.JSONField(null=True, blank=True)
    new_state = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.action} {self.entity_type}#{self.entity_id} by {self.actor_id}"