# accounts/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import LoginAudit, AuditTrail


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════

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

            # Force password change on first login — redirect BEFORE dashboard
            if user.must_change_password:
                return redirect('force_password_change')

            return redirect('dashboard')

        else:
            LoginAudit.objects.create(
                attempted_email=email, ip_address=ip,
                status='failed', failure_reason='Invalid credentials'
            )
            messages.error(request, 'Invalid email or password. Please try again.')

    return render(request, 'accounts/login.html')


# ══════════════════════════════════════════════════════════════════════════════
# LOGOUT
# ══════════════════════════════════════════════════════════════════════════════

def logout_view(request):
    if request.user.is_authenticated:
        AuditTrail.objects.create(
            user=request.user, action='LOGOUT', module='accounts',
            ip_address=get_client_ip(request),
            description=f'{request.user.get_full_name()} logged out'
        )
    logout(request)
    return redirect('login')


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def dashboard(request):
    # Block access if password change is still required
    if request.user.must_change_password:
        return redirect('force_password_change')

    user = request.user
    hour = timezone.localtime().hour
    if hour < 12:
        greeting = 'morning'
    elif hour < 17:
        greeting = 'afternoon'
    else:
        greeting = 'evening'

    # ── KPI Cards ─────────────────────────────────────────────
    today = timezone.localdate()

    try:
        from patients.models import Patient
        patients_today = Patient.objects.filter(created_at__date=today).count()
    except Exception:
        patients_today = 0

    try:
        from appointments.models import Appointment
        appointments_pending = Appointment.objects.filter(
            status__in=['Scheduled', 'Pending']
        ).count()
    except Exception:
        appointments_pending = 0

    try:
        from wards.models import Bed
        beds_occupied = Bed.objects.filter(status='Occupied').count()
    except Exception:
        beds_occupied = 0

    try:
        from inventory.models import Drug
        from django.db.models import F
        low_stock_items = Drug.objects.filter(
            is_active=True,
            current_stock__lte=F('reorder_level')
        ).count()
    except Exception:
        low_stock_items = 0

    context = {
        'user':                 user,
        'accessible_modules':   user.get_accessible_modules(),
        'greeting':             greeting,
        'patients_today':       patients_today,
        'appointments_pending': appointments_pending,
        'beds_occupied':        beds_occupied,
        'low_stock_items':      low_stock_items,
    }
    return render(request, 'accounts/dashboard.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# FORCE PASSWORD CHANGE — First login
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def force_password_change(request):
    """Intercepts first-login users and forces them to set a new password."""

    # Already changed — send to dashboard
    if not request.user.must_change_password:
        return redirect('dashboard')

    if request.method == 'POST':
        new_password     = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        errors = []
        if not new_password:
            errors.append('New password is required.')
        elif len(new_password) < 8:
            errors.append('Password must be at least 8 characters.')
        elif new_password != confirm_password:
            errors.append('Passwords do not match.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'accounts/force_password_change.html')

        # Set new password and clear the flag
        request.user.set_password(new_password)
        request.user.must_change_password = False
        request.user.save(update_fields=['password', 'must_change_password'])

        # Keep session alive after password change
        update_session_auth_hash(request, request.user)

        AuditTrail.objects.create(
            user=request.user,
            action='UPDATE',
            module='accounts',
            ip_address=get_client_ip(request),
            description=f'{request.user.get_full_name()} changed password on first login'
        )

        messages.success(request, '✅ Password changed successfully. Welcome to VanaraUniCare!')
        return redirect('dashboard')

    return render(request, 'accounts/force_password_change.html')




# ══════════════════════════════════════════════════════════════════════════════
# FORGOT PASSWORD
# Forgot Password Email Content
# ══════════════════════════════════════════════════════════════════════════════


def forgot_password(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'accounts/forgot_password.html')

        try:
            from django.contrib.auth import get_user_model
            from django.core.mail import EmailMultiAlternatives
            from django.conf import settings as django_settings
            from .models import PasswordResetToken
            import secrets

            User = get_user_model()
            user = User.objects.get(email=email, is_active=True)

            # Invalidate existing tokens
            PasswordResetToken.objects.filter(user=user, used=False).update(used=True)

            # Create new token — 1 hour expiry
            token = secrets.token_urlsafe(48)
            PasswordResetToken.objects.create(
                user       = user,
                token      = token,
                expires_at = timezone.now() + timezone.timedelta(hours=1),
            )

            reset_url   = request.build_absolute_uri(f'/auth/reset-password/{token}/')
            clinic_name = django_settings.NEU_HMS.get('CLINIC_NAME', 'VanaraUniCare')
            university  = django_settings.NEU_HMS.get('UNIVERSITY_NAME', 'North-Eastern University')
            user_name   = user.get_full_name() or user.email

            text_body = (
                f"Hi {user_name},\n\n"
                f"Reset your VanaraUniCare password here:\n{reset_url}\n\n"
                f"This link expires in 1 hour.\n\n"
                f"If you didn't request this, ignore this email.\n\n"
                f"— {clinic_name} IT Team"
            )

            html_body = f"""<!DOCTYPE html>

<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>

<body style="margin:0;padding:0;background:#0A1628;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0A1628;padding:40px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="max-width:520px;width:100%;">

        
        
        <tr><td align="center" style="padding-bottom:28px;">
          <table cellpadding="0" cellspacing="0"><tr>
            <td style="background:linear-gradient(145deg,#C9A84C,#a87c2a);border-radius:14px;width:48px;height:48px;text-align:center;vertical-align:middle;font-size:24px;">⚕</td>
            <td style="padding-left:12px;vertical-align:middle;">
              
              <div style="font-size:20px;font-weight:700;color:#FFFFFF;">VanaraUniCare</div>
              
              <div style="font-size:11px;color:#6B84A3;letter-spacing:0.08em;text-transform:uppercase;margin-top:2px;">NEU Clinic Management System</div>
            </td>
          </tr></table>
        </td></tr>

        <tr><td style="background:#0F2040;border:1px solid rgba(255,255,255,0.07);border-radius:20px;padding:44px 48px;">

          <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td align="center" style="padding-bottom:28px;">
              <div style="width:64px;height:64px;background:rgba(201,168,76,0.1);border:1px solid rgba(201,168,76,0.25);border-radius:50%;text-align:center;line-height:64px;font-size:28px;display:inline-block;">🔐</div>
            </td></tr>
          </table>

          <!-- Main content -->

          <h1 style="margin:0 0 8px;font-size:26px;font-weight:700;color:#FFFFFF;text-align:center;">Reset Your Password</h1>
          
          <p style="margin:0 0 28px;font-size:14px;color:#6B84A3;text-align:center;line-height:1.6;">
          
              Hi <strong style="color:#E2C47A;">{user_name}</strong>, we received a request to reset your password.
          
          </p>

          <div style="height:1px;background:rgba(255,255,255,0.07);margin-bottom:28px;"></div>

          <p style="margin:0 0 24px;font-size:14px;color:#8BA0BC;line-height:1.7;text-align:center;">
            
            Click the button below to set a new password. This link is valid for <strong style="color:#FFFFFF;">1 hour</strong> and can only be used once.
          
          </p>

          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
            <tr><td align="center">
              
              <a href="{reset_url}" style="display:inline-block;background:linear-gradient(135deg,#C9A84C,#a87c2a);color:#0A1628;font-size:15px;font-weight:700;text-decoration:none;padding:15px 40px;border-radius:12px;">
                Reset My Password
              </a>
            
            </td></tr>
          </table>

          
          <!-- Alternative link for users who can't click the button -->

          <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:14px 16px;margin-bottom:28px;">
            <p style="margin:0 0 6px;font-size:11px;color:#4A6380;text-transform:uppercase;letter-spacing:0.08em;">Or copy this link</p>
            <p style="margin:0;font-size:12px;color:#6B84A3;word-break:break-all;">{reset_url}</p>
          </div>

          <div style="height:1px;background:rgba(255,255,255,0.07);margin-bottom:24px;"></div>

          <div style="background:rgba(224,85,85,0.07);border:1px solid rgba(224,85,85,0.2);border-radius:10px;padding:14px 16px;">
            
            <p style="margin:0;font-size:13px;color:#f0a0a0;line-height:1.6;">
              If you didn't request a password reset, please ignore this email. Your password will remain unchanged.
            </p>
          
          </div>

        </td></tr>

        <tr><td align="center" style="padding-top:28px;">
          <p>copyright © {timezone.now().year} VanaraUniCare. All rights reserved.</p>
          <p style="margin:0;font-size:11px;color:#1E3050;">This is an automated message — please do not reply.</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

            msg = EmailMultiAlternatives(
                subject    = f'Password Reset — {clinic_name}',
                body       = text_body,
                from_email = django_settings.DEFAULT_FROM_EMAIL,
                to         = [user.email],
            )
            msg.attach_alternative(html_body, 'text/html')
            msg.send(fail_silently=True)

            AuditTrail.objects.create(
                user        = user,
                action      = 'UPDATE',
                module      = 'accounts',
                ip_address  = get_client_ip(request),
                description = f'Password reset requested for {user.email}',
            )

        except Exception:
            pass  # Don't reveal whether email exists

        messages.success(
            request,
            'If that email is registered, you will receive a reset link shortly. '
            'Check your inbox (and spam folder).'
        )
        return redirect('forgot_password')

    return render(request, 'accounts/forgot_password.html')




# ══════════════════════════════════════════════════════════════════════════════
# PASSWORD RESET CONFIRM
# ══════════════════════════════════════════════════════════════════════════════

def password_reset_confirm(request, token):
    if request.user.is_authenticated:
        return redirect('dashboard')

    from .models import PasswordResetToken

    try:
        reset_token = PasswordResetToken.objects.select_related('user').get(token=token)
    except PasswordResetToken.DoesNotExist:
        messages.error(request, 'This reset link is invalid or has already been used.')
        return redirect('forgot_password')

    if not reset_token.is_valid():
        messages.error(request, 'This reset link has expired. Please request a new one.')
        return redirect('forgot_password')

    if request.method == 'POST':
        new_password     = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        errors = []
        if not new_password:
            errors.append('New password is required.')
        elif len(new_password) < 8:
            errors.append('Password must be at least 8 characters.')
        elif new_password != confirm_password:
            errors.append('Passwords do not match.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'accounts/password_reset_confirm.html', {'token': token})

        user = reset_token.user
        user.set_password(new_password)
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password'])

        reset_token.used = True
        reset_token.save(update_fields=['used'])
        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)

        AuditTrail.objects.create(
            user        = user,
            action      = 'UPDATE',
            module      = 'accounts',
            ip_address  = get_client_ip(request),
            description = f'Password reset completed for {user.email}',
        )

        messages.success(request, '✅ Password reset successfully. You can now sign in.')
        return redirect('login')

    return render(request, 'accounts/password_reset_confirm.html', {'token': token})