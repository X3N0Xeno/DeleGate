from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required

@login_required
def home_view(request):
    return render(request, 'home/home.html', {'user': request.user})

def logout_view(request):
    logout(request)
    return redirect('login')