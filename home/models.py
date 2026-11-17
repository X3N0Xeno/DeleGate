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
        if hasattr(self, '_overall_progress'):
            return self._overall_progress
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
    target_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.project.name} - Gate {self.order}: {self.name}"

    @property
    def total_tasks(self):
        if hasattr(self, '_total_tasks'):
            return self._total_tasks
        if hasattr(self, 'total_tasks_count'):
            return self.total_tasks_count
        return self.tasks.count()

    @property
    def completed_tasks(self):
        if hasattr(self, '_completed_tasks'):
            return self._completed_tasks
        if hasattr(self, 'completed_tasks_count'):
            return self.completed_tasks_count
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


class Sprint(models.Model):
    project = models.ForeignKey(Project, related_name='sprints', on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    goal = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_active', 'start_date', 'name']

    def __str__(self):
        return f"{self.project.name} - {self.name}"

    @property
    def total_points(self):
        return sum(self.tasks.values_list('effort_points', flat=True))

    @property
    def completed_points(self):
        return sum(self.tasks.filter(status='COMPLETED').values_list('effort_points', flat=True))

    @property
    def progress_percent(self):
        total = self.total_points
        if total == 0:
            return 0
        return int(round((self.completed_points / total) * 100))


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
    sprint = models.ForeignKey(Sprint, related_name='tasks', null=True, blank=True, on_delete=models.SET_NULL)
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
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    target_release_date = models.DateField(null=True, blank=True)
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


class TaskLink(models.Model):
    task = models.ForeignKey(DelegationTask, related_name='links', on_delete=models.CASCADE)
    url = models.URLField(max_length=1000)
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return self.title or self.url

    @property
    def display_title(self):
        if self.title:
            return self.title
        cleaned = self.url.replace('https://', '').replace('http://', '')
        return cleaned[:40] + ('…' if len(cleaned) > 40 else '')
