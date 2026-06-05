from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .forms import UserRegisterForm, UserUpdateForm
from django.shortcuts import render,redirect
from django.contrib.auth import login,authenticate
from django.contrib.auth.decorators import login_required
from movies.models import Movie , Booking
from django.shortcuts import render, redirect
from django.contrib import messages

def home(request):
    movies= Movie.objects.all()
    return render(request,'home.html',{'movies':movies})
def register(request):
    if request.method == 'POST':
        form=UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username=form.cleaned_data.get('username')
            password=form.cleaned_data.get('password1')
            user=authenticate(username=username,password=password)
            login(request,user)
            return redirect('profile')
    else:
        form=UserRegisterForm()
    return render(request,'users/register.html',{'form':form})

def login_view(request):
    # Preserve the intended redirect URL
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # If a 'next' was supplied, redirect there; otherwise home
            return redirect(next_url if next_url else '/analytics/')
    else:
        form = AuthenticationForm()
    # Render the login template and pass the next URL so the form can include it as a hidden field
    return render(request, 'users/login.html', {'form': form, 'next': next_url})

@login_required(login_url='/login/')
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        if u_form.is_valid():
            u_form.save()
            messages.success(request, "Your profile has been successfully updated!")
            return redirect('profile')
    else:
        # Pre-fills the input boxes with your current logged-in data
        u_form = UserUpdateForm(instance=request.user)

    # Grabs all your past tickets to display inside the bottom panel card
    bookings = Booking.objects.filter(user=request.user).order_by('-booked_at')

    context = {
        'u_form': u_form,
        'bookings': bookings
    }
    return render(request, 'users/profile.html', context)
@login_required
def reset_password(request):
    if request.method == 'POST':
        form=PasswordChangeForm(user=request.user,data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form=PasswordChangeForm(user=request.user)
    return render(request,'users/reset_password.html',{'form':form})