from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST

from patients.models import Faculty, Department, Programme


# ══════════════════════════════════════════════════════════════════════════════
# ACCESS CONTROL
# ══════════════════════════════════════════════════════════════════════════════

def admin_required(view_func):
    """Allow only Super Admin and Admin roles."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        # role is a ForeignKey to Role model — get the name string from it
        role_obj  = getattr(request.user, 'role', None)
        role_name = ''
        if role_obj is not None:
            role_name = str(getattr(role_obj, 'name', role_obj)).lower()
        if role_name not in ('super admin', 'admin', 'superadmin'):
            messages.error(request, '⛔ You do not have permission to access System Settings.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@admin_required
def settings_dashboard(request):
    context = {
        'faculty_ct':    Faculty.objects.count(),
        'dept_ct':       Department.objects.count(),
        'programme_ct':  Programme.objects.count(),
        'active_fac':    Faculty.objects.filter(is_active=True).count(),
        'active_dept':   Department.objects.filter(is_active=True).count(),
        'active_prog':   Programme.objects.filter(is_active=True).count(),
    }
    return render(request, 'settings/dashboard.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# FACULTIES
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@admin_required
def faculty_list(request):
    faculties = Faculty.objects.all().order_by('name')
    return render(request, 'settings/faculties.html', {'faculties': faculties})


@login_required
@admin_required
def faculty_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()

        if not name:
            messages.error(request, 'Faculty name is required.')
            return redirect('faculty_list')

        if Faculty.objects.filter(name__iexact=name).exists():
            messages.error(request, f'A faculty named "<strong>{name}</strong>" already exists.')
            return redirect('faculty_list')

        Faculty.objects.create(name=name, code=code, is_active=True)
        messages.success(request, f'✅ Faculty "<strong>{name}</strong>" created successfully.')
        return redirect('faculty_list')

    return redirect('faculty_list')


@login_required
@admin_required
def faculty_edit(request, pk):
    faculty = get_object_or_404(Faculty, pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()

        if not name:
            messages.error(request, 'Faculty name is required.')
            return redirect('faculty_list')

        if Faculty.objects.filter(name__iexact=name).exclude(pk=pk).exists():
            messages.error(request, f'Another faculty named "<strong>{name}</strong>" already exists.')
            return redirect('faculty_list')

        faculty.name = name
        faculty.code = code
        faculty.save()
        messages.success(request, f'✅ Faculty updated to "<strong>{name}</strong>".')
        return redirect('faculty_list')

    return redirect('faculty_list')


@login_required
@admin_required
@require_POST
def faculty_toggle(request, pk):
    faculty = get_object_or_404(Faculty, pk=pk)
    faculty.is_active = not faculty.is_active
    faculty.save(update_fields=['is_active'])
    action = 'activated' if faculty.is_active else 'deactivated'
    messages.success(request, f'✅ Faculty "<strong>{faculty.name}</strong>" {action}.')
    return redirect('faculty_list')


# ══════════════════════════════════════════════════════════════════════════════
# DEPARTMENTS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@admin_required
def department_list(request):
    departments = Department.objects.select_related('faculty').order_by('faculty__name', 'name')
    faculties   = Faculty.objects.filter(is_active=True).order_by('name')
    return render(request, 'settings/departments.html', {
        'departments': departments,
        'faculties':   faculties,
    })


@login_required
@admin_required
def department_create(request):
    if request.method == 'POST':
        name       = request.POST.get('name', '').strip()
        code       = request.POST.get('code', '').strip().upper()
        faculty_id = request.POST.get('faculty', '')

        if not name or not faculty_id:
            messages.error(request, 'Department name and faculty are required.')
            return redirect('department_list')

        faculty = get_object_or_404(Faculty, pk=faculty_id)

        if Department.objects.filter(name__iexact=name, faculty=faculty).exists():
            messages.error(request, f'This department already exists under {faculty.name}.')
            return redirect('department_list')

        Department.objects.create(name=name, code=code, faculty=faculty, is_active=True)
        messages.success(request, f'✅ Department "<strong>{name}</strong>" created under {faculty.name}.')
        return redirect('department_list')

    return redirect('department_list')


@login_required
@admin_required
def department_edit(request, pk):
    dept = get_object_or_404(Department, pk=pk)

    if request.method == 'POST':
        name       = request.POST.get('name', '').strip()
        code       = request.POST.get('code', '').strip().upper()
        faculty_id = request.POST.get('faculty', '')

        if not name or not faculty_id:
            messages.error(request, 'Department name and faculty are required.')
            return redirect('department_list')

        faculty = get_object_or_404(Faculty, pk=faculty_id)

        if Department.objects.filter(name__iexact=name, faculty=faculty).exclude(pk=pk).exists():
            messages.error(request, f'This department already exists under {faculty.name}.')
            return redirect('department_list')

        dept.name    = name
        dept.code    = code
        dept.faculty = faculty
        dept.save()
        messages.success(request, f'✅ Department "<strong>{name}</strong>" updated.')
        return redirect('department_list')

    return redirect('department_list')


@login_required
@admin_required
@require_POST
def department_toggle(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    dept.is_active = not dept.is_active
    dept.save(update_fields=['is_active'])
    action = 'activated' if dept.is_active else 'deactivated'
    messages.success(request, f'✅ Department "<strong>{dept.name}</strong>" {action}.')
    return redirect('department_list')


# ══════════════════════════════════════════════════════════════════════════════
# PROGRAMMES
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@admin_required
def programme_list(request):
    programmes = Programme.objects.select_related(
                     'faculty', 'department'
                 ).order_by('faculty__name', 'name')
    faculties   = Faculty.objects.filter(is_active=True).order_by('name')
    departments = Department.objects.filter(is_active=True).order_by('name')
    return render(request, 'settings/programmes.html', {
        'programmes':  programmes,
        'faculties':   faculties,
        'departments': departments,
    })


@login_required
@admin_required
def programme_create(request):
    if request.method == 'POST':
        name       = request.POST.get('name', '').strip()
        code       = request.POST.get('code', '').strip().upper()
        faculty_id = request.POST.get('faculty', '')
        dept_id    = request.POST.get('department', '')
        duration   = request.POST.get('duration', '4').strip()

        if not name or not faculty_id:
            messages.error(request, 'Programme name and faculty are required.')
            return redirect('programme_list')

        faculty    = get_object_or_404(Faculty, pk=faculty_id)
        department = Department.objects.filter(pk=dept_id).first() if dept_id else None

        if Programme.objects.filter(name__iexact=name, faculty=faculty).exists():
            messages.error(request, f'This programme already exists under {faculty.name}.')
            return redirect('programme_list')

        Programme.objects.create(
            name       = name,
            code       = code,
            faculty    = faculty,
            department = department,
            duration   = int(duration) if duration.isdigit() else 4,
            is_active  = True,
        )
        messages.success(request, f'✅ Programme "<strong>{name}</strong>" created.')
        return redirect('programme_list')

    return redirect('programme_list')


@login_required
@admin_required
def programme_edit(request, pk):
    prog = get_object_or_404(Programme, pk=pk)

    if request.method == 'POST':
        name       = request.POST.get('name', '').strip()
        code       = request.POST.get('code', '').strip().upper()
        faculty_id = request.POST.get('faculty', '')
        dept_id    = request.POST.get('department', '')
        duration   = request.POST.get('duration', '4').strip()

        if not name or not faculty_id:
            messages.error(request, 'Programme name and faculty are required.')
            return redirect('programme_list')

        faculty    = get_object_or_404(Faculty, pk=faculty_id)
        department = Department.objects.filter(pk=dept_id).first() if dept_id else None

        if Programme.objects.filter(name__iexact=name, faculty=faculty).exclude(pk=pk).exists():
            messages.error(request, f'This programme already exists under {faculty.name}.')
            return redirect('programme_list')

        prog.name       = name
        prog.code       = code
        prog.faculty    = faculty
        prog.department = department
        prog.duration   = int(duration) if duration.isdigit() else 4
        prog.save()
        messages.success(request, f'✅ Programme "<strong>{name}</strong>" updated.')
        return redirect('programme_list')

    return redirect('programme_list')


@login_required
@admin_required
@require_POST
def programme_toggle(request, pk):
    prog = get_object_or_404(Programme, pk=pk)
    prog.is_active = not prog.is_active
    prog.save(update_fields=['is_active'])
    action = 'activated' if prog.is_active else 'deactivated'
    messages.success(request, f'✅ Programme "<strong>{prog.name}</strong>" {action}.')
    return redirect('programme_list')