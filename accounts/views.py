# accounts/views.py
# This file contains the views for user authentication, including login, logout, and dashboard access.
# It also includes logging of login attempts and audit trails for security monitoring.
# Author: [ZIRRA VAISAH PETER]

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import LoginAudit, AuditTrail


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        ip       = get_client_ip(request)

        user = authenticate(request, email=email, password=password)

        if user is not None:
            if not user.is_active:
                LoginAudit.objects.create(
                    attempted_email=email, ip_address=ip,
                    status='failed', failure_reason='Account is deactivated'
                )
                messages.error(request, 'Your account has been deactivated. Please contact the administrator.')
                return render(request, 'accounts/login.html')

            login(request, user)

            # Log successful login
            LoginAudit.objects.create(
                user=user, attempted_email=email,
                ip_address=ip, status='success'
            )
            AuditTrail.objects.create(
                user=user, action='LOGIN', module='accounts',
                ip_address=ip, description=f'{user.get_full_name()} logged in'
            )

            # Update last login IP
            user.last_login_ip = ip
            user.last_login    = timezone.now()
            user.save(update_fields=['last_login_ip', 'last_login'])

            # Force password change on first login
            if user.must_change_password:
                messages.warning(request, 'Please change your password before continuing.')

            return redirect('dashboard')

        else:
            LoginAudit.objects.create(
                attempted_email=email, ip_address=ip,
                status='failed', failure_reason='Invalid credentials'
            )
            messages.error(request, 'Invalid email or password. Please try again.')

    return render(request, 'accounts/login.html')


def logout_view(request):
    if request.user.is_authenticated:
        AuditTrail.objects.create(
            user=request.user, action='LOGOUT', module='accounts',
            ip_address=get_client_ip(request),
            description=f'{request.user.get_full_name()} logged out'
        )
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    user = request.user
    hour = timezone.localtime().hour
    if hour < 12:
        greeting = 'morning'
    elif hour < 17:
        greeting = 'afternoon'
    else:
        greeting = 'evening'
    context = {
        'user':               user,
        'accessible_modules': user.get_accessible_modules(),
        'greeting':           greeting,
    }
    return render(request, 'accounts/dashboard.html', context)