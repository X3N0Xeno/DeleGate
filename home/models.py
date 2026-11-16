from django.db import models
from django.contrib.auth.models import User

class Project(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_projects')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def overall_progress(self):
        total = self.tasks.count()
        if total == 0:
            return 0
        completed = self.tasks.filter(status='COMPLETED').count()
        return int(round((completed / total) * 100))

    @property
    def total_effort(self):
        return sum(self.tasks.values_list('effort_points', flat=True))

    @property
    def completed_effort(self):
        return sum(self.tasks.filter(status='COMPLETED').values_list('effort_points', flat=True))


class StageGate(models.Model):
    project = models.ForeignKey(Project, related_name='gates', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=150)
    exit_criteria = models.CharField(max_length=255, blank=True)
    is_unlocked = models.BooleanField(default=False)
    is_passed = models.BooleanField(default=False)
    unlocked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.project.name} - Gate {self.order}: {self.name}"

    @property
    def total_tasks(self):
        return self.tasks.count()

    @property
    def completed_tasks(self):
        return self.tasks.filter(status='COMPLETED').count()

    @property
    def progress_percent(self):
        total = self.total_tasks
        if total == 0:
            return 0
        return int(round((self.completed_tasks / total) * 100))

    @property
    def ready_to_pass(self):
        return self.total_tasks > 0 and self.completed_tasks == self.total_tasks

    @property
    def queued_effort(self):
        return sum(self.tasks.values_list('effort_points', flat=True))


class DelegationTask(models.Model):
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MED', 'Medium'),
        ('HIGH', 'High'),
        ('CRIT', 'Critical'),
    ]
    STATUS_CHOICES = [
        ('OPEN', 'Open in Pool'),
        ('CLAIMED', 'Claimed'),
        ('IN_PROGRESS', 'In Progress'),
        ('IN_REVIEW', 'In Review'),
        ('COMPLETED', 'Completed'),
    ]

    project = models.ForeignKey(Project, related_name='tasks', null=True, blank=True, on_delete=models.CASCADE)
    gate = models.ForeignKey(StageGate, related_name='tasks', null=True, blank=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, related_name='dispatched_tasks', on_delete=models.CASCADE, null=True, blank=True)
    claimed_by = models.ForeignKey(User, related_name='mined_tasks', null=True, blank=True, on_delete=models.SET_NULL)
    priority = models.CharField(max_length=4, choices=PRIORITY_CHOICES, default='MED')
    effort_points = models.PositiveIntegerField(default=3)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='OPEN')
    is_multiclaimable = models.BooleanField(default=False)
    progress_notes = models.TextField(blank=True)
    dissolved_count = models.PositiveIntegerField(default=0)
    is_blocked = models.BooleanField(default=False)
    blocker_note = models.CharField(max_length=255, blank=True)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    claimed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class TaskComment(models.Model):
    task = models.ForeignKey(DelegationTask, related_name='comments', on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.task.title}"
