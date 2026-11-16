from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import DelegationTask

@login_required
def home_view(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        priority = request.POST.get('priority', 'MED')
        due_date = request.POST.get('due_date') or None
        
        if title:
            DelegationTask.objects.create(
                title=title,
                assigned_by=request.user,
                priority=priority,
                due_date=due_date
            )
        return redirect('home')

    tasks = DelegationTask.objects.filter(assigned_by=request.user).order_by('-created_at')
    return render(request, 'home/home.html', {'tasks': tasks})