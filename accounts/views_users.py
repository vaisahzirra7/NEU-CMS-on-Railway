import secrets
import string
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.permissions import permission_required

from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import User, Role, SystemModule, RolePermission, AuditTrail


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')


def log_action(user, action, module, record_id='', description='',
               old=None, new=None, request=None):
    AuditTrail.objects.create(
        user=user,
        action=action,
        module=module,
        record_id=str(record_id),
        description=description,
        old_values=old,
        new_values=new,
        ip_address=get_client_ip(request) if request else None,
    )


# Roles that can NEVER be deleted or have their permissions modified
PROTECTED_ROLES = {'super admin', 'superadmin', 'admin'}


# Superuser account that can NEVER be edited, deactivated, or have password reset
# User account that can NEVER be edited, deactivated, or have password reset
PROTECTED_USER_EMAIL = 'vaisahzirra7@gmail.com'

def is_protected_user(user):
    return user.email.lower().strip() == PROTECTED_USER_EMAIL.lower()

def is_protected_role(role):
    return role.name.lower().strip() in PROTECTED_ROLES



# Temporary password generation
TEMP_PASSWORD = 'Neu@12345'

def generate_temp_password():
    return TEMP_PASSWORD



# ══════════════════════════════════════════════════════════════════════════════
# USER LIST
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('users', 'view')
def user_list(request):
    qs = User.objects.select_related('role').all().order_by('last_name', 'first_name')

    # Filters
    q          = request.GET.get('q', '').strip()
    role_id    = request.GET.get('role', '').strip()
    status     = request.GET.get('status', '').strip()

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)  |
            Q(email__icontains=q)      |
            Q(staff_id__icontains=q)   |
            Q(department__icontains=q)
        )
    if role_id:
        qs = qs.filter(role__id=role_id)
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)

    all_roles = Role.objects.filter(is_active=True).order_by('name')

    context = {
        'users':      qs,
        'roles':      all_roles,
        'q':          q,
        'sel_role':   role_id,
        'sel_status': status,
        # Stats
        'total':      User.objects.count(),
        'active_ct':  User.objects.filter(is_active=True).count(),
        'inactive_ct':User.objects.filter(is_active=False).count(),
        'role_ct':    Role.objects.count(),
    }
    return render(request, 'accounts/users/list.html', context)



# ══════════════════════════════════════════════════════════════════════════════
# CREATE USER
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('users', 'create')
def user_create(request):
    roles = Role.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        p      = request.POST
        errors = []

        if not p.get('first_name', '').strip():
            errors.append('First name is required.')
        if not p.get('last_name', '').strip():
            errors.append('Last name is required.')
        if not p.get('email', '').strip():
            errors.append('Email address is required.')
        elif User.objects.filter(email__iexact=p['email'].strip()).exists():
            errors.append('A user with this email address already exists.')
        if p.get('staff_id', '').strip():
            if User.objects.filter(staff_id=p['staff_id'].strip()).exists():
                errors.append('This Staff ID is already assigned to another user.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'accounts/users/create.html', {
                'roles': roles, 'form': p,
            })

        temp_pw = generate_temp_password()
        role    = Role.objects.filter(id=p.get('role')).first() if p.get('role') else None

        user = User.objects.create_user(
            email             = p['email'].strip().lower(),
            password          = temp_pw,
            first_name        = p['first_name'].strip(),
            last_name         = p['last_name'].strip(),
            other_names       = p.get('other_names', '').strip(),
            staff_id          = p.get('staff_id', '').strip() or None,
            phone             = p.get('phone', '').strip(),
            role              = role,
            department        = p.get('department', '').strip(),
            job_title         = p.get('job_title', '').strip(),
            qualification     = p.get('qualification', '').strip(),
            reg_number        = p.get('reg_number', '').strip(),
            gender            = p.get('gender', ''),
            is_active         = True,
            is_staff          = p.get('is_staff') == 'on',
            must_change_password = True,
            created_by        = request.user,
        )

        log_action(
            request.user, 'CREATE', 'user-management',
            record_id   = user.id,
            description = f'Created staff account for {user.get_full_name()}',
            new         = {
                'name':  user.get_full_name(),
                'email': user.email,
                'role':  role.name if role else None,
            },
            request = request,
        )

        messages.success(
            request,
            f'✅ Account created for <strong>{user.get_full_name()}</strong>. '
            f'Temporary password: <code>{temp_pw}</code> — share this securely with the staff member.'
        )
        return redirect('user_detail', pk=user.pk)

    return render(request, 'accounts/users/create.html', {
        'roles': roles,
        'form':  {},
    })



# ══════════════════════════════════════════════════════════════════════════════
# USER DETAIL
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('users', 'view')
def user_detail(request, pk):
    u          = get_object_or_404(
                    User.objects.select_related('role', 'created_by'),
                    pk=pk
                 )
    audit_logs = AuditTrail.objects.filter(user=u).order_by('-created_at')[:15]

    return render(request, 'accounts/users/detail.html', {
        'u':          u,
        'audit_logs': audit_logs,
    })



# ══════════════════════════════════════════════════════════════════════════════
# EDIT USER
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('users', 'edit')
def user_edit(request, pk):
    u     = get_object_or_404(User, pk=pk)
    roles = Role.objects.filter(is_active=True).order_by('name')

    if is_protected_user(u) and request.user != u:
        messages.error(request, '⛔ This account is protected and cannot be modified.')
        return redirect('user_detail', pk=pk)

    if request.method == 'POST':
        p = request.POST

        old_vals = {
            'first_name': u.first_name,
            'last_name':  u.last_name,
            'email':      u.email,
            'role':       u.role.name if u.role else None,
            'is_active':  u.is_active,
        }

        email = p.get('email', '').strip().lower()
        if email != u.email and User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'That email address is already used by another account.')
            return render(request, 'accounts/users/edit.html', {'u': u, 'roles': roles})

        role = Role.objects.filter(id=p.get('role')).first() if p.get('role') else None

        u.first_name     = p.get('first_name', u.first_name).strip()
        u.last_name      = p.get('last_name',  u.last_name).strip()
        u.other_names    = p.get('other_names', '').strip()
        u.email          = email or u.email
        u.phone          = p.get('phone', '').strip()
        u.role           = role
        u.department     = p.get('department', '').strip()
        u.job_title      = p.get('job_title', '').strip()
        u.qualification  = p.get('qualification', '').strip()
        u.reg_number     = p.get('reg_number', '').strip()
        u.gender         = p.get('gender', '')
        u.is_active      = p.get('is_active') == 'on'
        u.is_staff       = p.get('is_staff') == 'on'
        u.save()

        log_action(
            request.user, 'UPDATE', 'user-management',
            record_id   = u.id,
            description = f'Updated staff account: {u.get_full_name()}',
            old         = old_vals,
            new         = {
                'first_name': u.first_name,
                'last_name':  u.last_name,
                'email':      u.email,
                'role':       role.name if role else None,
                'is_active':  u.is_active,
            },
            request = request,
        )

        messages.success(request, f'✅ {u.get_full_name()}\'s profile has been updated.')
        return redirect('user_detail', pk=u.pk)

    return render(request, 'accounts/users/edit.html', {'u': u, 'roles': roles})



# ══════════════════════════════════════════════════════════════════════════════
# TOGGLE ACTIVE STATUS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('users', 'edit')
@require_POST
def user_toggle_status(request, pk):
    u = get_object_or_404(User, pk=pk)

    if is_protected_user(u):
        messages.error(request, '⛔ This account is protected and cannot be deactivated.')
        return redirect('user_detail', pk=pk)

    if u == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('user_detail', pk=pk)

    u.is_active = not u.is_active
    u.save(update_fields=['is_active'])

    action = 'activated' if u.is_active else 'deactivated'
    log_action(
        request.user, 'UPDATE', 'user-management',
        record_id   = u.id,
        description = f'Account {action}: {u.get_full_name()}',
        request     = request,
    )

    messages.success(request, f'✅ {u.get_full_name()}\'s account has been {action}.')
    return redirect('user_detail', pk=pk)



# ══════════════════════════════════════════════════════════════════════════════
# RESET PASSWORD
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('users', 'edit')
@require_POST
def user_reset_password(request, pk):
    u       = get_object_or_404(User, pk=pk)

    if is_protected_user(u) and request.user != u:
        messages.error(request, '⛔ This account is protected and its password cannot be reset.')
        return redirect('user_detail', pk=pk)

    temp_pw = generate_temp_password()

    u.set_password(temp_pw)
    u.must_change_password = True
    u.save(update_fields=['password', 'must_change_password'])

    log_action(
        request.user, 'UPDATE', 'user-management',
        record_id   = u.id,
        description = f'Password reset for {u.get_full_name()}',
        request     = request,
    )

    messages.success(
        request,
        f'🔐 Password reset for <strong>{u.get_full_name()}</strong>. '
        f'New temporary password: <code>{temp_pw}</code> — share this securely.'
    )
    return redirect('user_detail', pk=pk)



# ══════════════════════════════════════════════════════════════════════════════
# ROLES LIST
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('roles', 'view')
def role_list(request):
    roles = Role.objects.prefetch_related('users', 'permissions').all().order_by('name')
    return render(request, 'accounts/users/roles.html', {'roles': roles})



# ══════════════════════════════════════════════════════════════════════════════
# CREATE ROLE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('roles', 'create')
@require_POST
def role_create(request):
    name        = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()

    if not name:
        messages.error(request, 'Role name is required.')
        return redirect('role_list')

    if Role.objects.filter(name__iexact=name).exists():
        messages.error(request, f'A role named "<strong>{name}</strong>" already exists.')
        return redirect('role_list')

    # Generate a unique slug
    base_slug = slugify(name)
    slug      = base_slug
    counter   = 1
    while Role.objects.filter(slug=slug).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1

    role = Role.objects.create(
        name           = name,
        slug           = slug,
        description    = description,
        is_system_role = False,
        is_active      = True,
        created_by     = request.user,
    )

    log_action(
        request.user, 'CREATE', 'role-management',
        record_id   = role.id,
        description = f'Created role: {role.name}',
        request     = request,
    )

    messages.success(request, f'✅ Role "<strong>{role.name}</strong>" created. You can now configure its permissions.')
    return redirect('role_permissions', pk=role.pk)



# ══════════════════════════════════════════════════════════════════════════════
# DELETE ROLE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('roles', 'delete')
@require_POST
def role_delete(request, pk):
    role = get_object_or_404(Role, pk=pk)

    if is_protected_role(role):
        messages.error(request, f'⛔ The <strong>{role.name}</strong> role is protected and cannot be deleted.')
        return redirect('role_list')

    if role.is_system_role:
        messages.error(request, f'⛔ System roles cannot be deleted.')
        return redirect('role_list')

    if role.users.exists():
        count = role.users.count()
        messages.error(
            request,
            f'⛔ Cannot delete "<strong>{role.name}</strong>" — '
            f'{count} staff member{"s are" if count > 1 else " is"} assigned to this role. '
            f'Reassign them first.'
        )
        return redirect('role_list')

    role_name = role.name
    log_action(
        request.user, 'DELETE', 'role-management',
        record_id   = role.id,
        description = f'Deleted role: {role_name}',
        request     = request,
    )
    role.delete()

    messages.success(request, f'✅ Role "<strong>{role_name}</strong>" has been deleted.')
    return redirect('role_list')



# ══════════════════════════════════════════════════════════════════════════════
# ROLE PERMISSIONS MATRIX
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('roles', 'view')
def role_permissions(request, pk):
    role    = get_object_or_404(Role, pk=pk)
    modules = SystemModule.objects.filter(is_active=True).order_by('sort_order', 'name')

    # Build lookup: module_id → RolePermission object
    perms_qs = {p.module_id: p for p in role.permissions.all()}

    # Build a flat list of (module, perm_or_None) so template needs no custom filter
    module_perms = []
    for module in modules:
        p = perms_qs.get(module.id)
        module_perms.append({
            'module':     module,
            'can_view':   p.can_view   if p else False,
            'can_create': p.can_create if p else False,
            'can_edit':   p.can_edit   if p else False,
            'can_delete': p.can_delete if p else False,
            'can_export': p.can_export if p else False,
        })

    protected = is_protected_role(role)

    if request.method == 'POST':
        if protected:
            messages.error(request, f'⛔ Permissions for <strong>{role.name}</strong> are protected and cannot be modified.')
            return redirect('role_permissions', pk=pk)

        for module in modules:
            prefix  = f'mod_{module.id}_'
            perm, _ = RolePermission.objects.get_or_create(role=role, module=module)
            perm.can_view   = bool(request.POST.get(f'{prefix}view'))
            perm.can_create = bool(request.POST.get(f'{prefix}create'))
            perm.can_edit   = bool(request.POST.get(f'{prefix}edit'))
            perm.can_delete = bool(request.POST.get(f'{prefix}delete'))
            perm.can_export = bool(request.POST.get(f'{prefix}export'))
            perm.save()

        log_action(
            request.user, 'UPDATE', 'role-permissions',
            record_id   = role.id,
            description = f'Updated permissions for role: {role.name}',
            request     = request,
        )

        messages.success(request, f'✅ Permissions for <strong>{role.name}</strong> saved successfully.')
        return redirect('role_permissions', pk=pk)

    return render(request, 'accounts/users/role_permissions.html', {
        'role':         role,
        'module_perms': module_perms,
        'protected':    protected,
    })