from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_POST

from appointments.models import Appointment
from patients.models import Patient
from django.conf import settings

User = settings.AUTH_USER_MODEL

# ── Only Doctors can be assigned to student appointments ─────────────────────
CLINICAL_ROLES = ['Doctor', 'Medical Officer', 'doctor', 'medical officer']


def get_user_model():
    from django.contrib.auth import get_user_model
    return get_user_model()


def get_clinical_staff():
    """Return only clinical staff — Doctors, Nurses, Medical Officers etc."""
    return get_user_model().objects.filter(
        is_active=True,
        role__name__in=CLINICAL_ROLES
    ).order_by('first_name')


# ══════════════════════════════════════════════════════════════════════════════
# LIST
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def appointment_list(request):
    qs = Appointment.objects.select_related(
        'patient', 'assigned_to'
    ).order_by('-appointment_date', 'time_slot')

    search    = request.GET.get('q', '').strip()
    status    = request.GET.get('status', '')
    apt_type  = request.GET.get('type', '')
    date_str  = request.GET.get('date', '')
    doctor_id = request.GET.get('doctor', '')

    if search:
        qs = qs.filter(
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search)  |
            Q(patient__matric_no__icontains=search)  |
            Q(appointment_id__icontains=search)
        )
    if status:
        qs = qs.filter(status=status)
    if apt_type:
        qs = qs.filter(appointment_type=apt_type)
    if date_str:
        qs = qs.filter(appointment_date=date_str)
    if doctor_id:
        qs = qs.filter(assigned_to_id=doctor_id)

    today      = timezone.localdate()
    today_apts = Appointment.objects.filter(appointment_date=today)

    context = {
        'appointments':    qs,
        'total_today':     today_apts.count(),
        'scheduled_today': today_apts.filter(status='Scheduled').count(),
        'in_progress':     Appointment.objects.filter(status='In Progress').count(),
        'completed_today': today_apts.filter(status='Completed').count(),
        'doctors':         get_clinical_staff(),
        'status_choices':  Appointment.STATUS_CHOICES,
        'type_choices':    Appointment.TYPE_CHOICES,
        'search':          search,
        'filter_status':   status,
        'filter_type':     apt_type,
        'filter_date':     date_str,
        'filter_doctor':   doctor_id,
        'today':           today.isoformat(),
    }
    return render(request, 'appointments/list.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# CREATE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def appointment_create(request):
    patients = Patient.objects.filter(is_active=True).order_by('first_name')
    doctors  = get_clinical_staff()

    if request.method == 'POST':
        patient_id     = request.POST.get('patient', '')
        apt_type       = request.POST.get('appointment_type', '')
        custom_type    = request.POST.get('custom_type', '').strip()
        apt_date       = request.POST.get('appointment_date', '')
        time_slot      = request.POST.get('time_slot', '').strip()
        reason         = request.POST.get('reason', '').strip()
        notes          = request.POST.get('notes', '').strip()
        assigned_to_id = request.POST.get('assigned_to', '')

        errors = []
        if not patient_id: errors.append('Patient is required.')
        if not apt_type:   errors.append('Appointment type is required.')
        if not apt_date:   errors.append('Appointment date is required.')
        if not time_slot:  errors.append('Please select a time for the appointment.')
        if apt_type == 'Other' and not custom_type:
            errors.append('Please specify the appointment type.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'appointments/create.html', {
                'patients':     patients,
                'doctors':      doctors,
                'type_choices': Appointment.TYPE_CHOICES,
                'post':         request.POST,
            })

        # Warn on duplicate slot for same doctor
        if assigned_to_id and Appointment.objects.filter(
            assigned_to_id=assigned_to_id,
            appointment_date=apt_date,
            time_slot=time_slot,
            status__in=['Scheduled', 'In Progress'],
        ).exists():
            messages.warning(
                request,
                f'⚠️ This doctor already has an appointment at {time_slot} on this date. '
                'The appointment was still saved — please verify.'
            )

        patient     = get_object_or_404(Patient, pk=patient_id)
        assigned_to = get_user_model().objects.filter(pk=assigned_to_id).first() if assigned_to_id else None

        apt = Appointment.objects.create(
            patient          = patient,
            appointment_type = apt_type,
            custom_type      = custom_type,
            appointment_date = apt_date,
            time_slot        = time_slot,
            reason           = reason,
            notes            = notes,
            assigned_to      = assigned_to,
            status           = 'Scheduled',
            created_by       = request.user,
        )

        messages.success(request, f'✅ Appointment <strong>{apt.appointment_id}</strong> booked successfully.')
        return redirect('appointment_detail', pk=apt.pk)

    return render(request, 'appointments/create.html', {
        'patients':     patients,
        'doctors':      doctors,
        'type_choices': Appointment.TYPE_CHOICES,
        'today':        timezone.localdate().isoformat(),
    })


# ══════════════════════════════════════════════════════════════════════════════
# DETAIL
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def appointment_detail(request, pk):
    apt = get_object_or_404(Appointment, pk=pk)
    return render(request, 'appointments/detail.html', {'apt': apt})


# ══════════════════════════════════════════════════════════════════════════════
# EDIT
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def appointment_edit(request, pk):
    apt     = get_object_or_404(Appointment, pk=pk)
    doctors = get_clinical_staff()

    if apt.status in ('Completed', 'Cancelled'):
        messages.error(request, '⛔ Completed or cancelled appointments cannot be edited.')
        return redirect('appointment_detail', pk=pk)

    if request.method == 'POST':
        apt_type       = request.POST.get('appointment_type', '')
        custom_type    = request.POST.get('custom_type', '').strip()
        apt_date       = request.POST.get('appointment_date', '')
        time_slot      = request.POST.get('time_slot', '').strip()
        reason         = request.POST.get('reason', '').strip()
        notes          = request.POST.get('notes', '').strip()
        assigned_to_id = request.POST.get('assigned_to', '')

        if not time_slot:
            messages.error(request, 'Please select a time for the appointment.')
            return render(request, 'appointments/edit.html', {
                'apt':          apt,
                'doctors':      doctors,
                'type_choices': Appointment.TYPE_CHOICES,
            })

        apt.appointment_type = apt_type
        apt.custom_type      = custom_type
        apt.appointment_date = apt_date
        apt.time_slot        = time_slot
        apt.reason           = reason
        apt.notes            = notes
        apt.assigned_to      = get_user_model().objects.filter(pk=assigned_to_id).first() if assigned_to_id else None
        apt.save()

        messages.success(request, f'✅ Appointment <strong>{apt.appointment_id}</strong> updated.')
        return redirect('appointment_detail', pk=pk)

    return render(request, 'appointments/edit.html', {
        'apt':          apt,
        'doctors':      doctors,
        'type_choices': Appointment.TYPE_CHOICES,
    })


# ══════════════════════════════════════════════════════════════════════════════
# UPDATE STATUS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def appointment_update_status(request, pk):
    apt           = get_object_or_404(Appointment, pk=pk)
    new_status    = request.POST.get('status', '')
    cancel_reason = request.POST.get('cancellation_reason', '').strip()

    valid = ['Scheduled', 'In Progress', 'Completed', 'Cancelled']
    if new_status not in valid:
        messages.error(request, 'Invalid status.')
        return redirect('appointment_detail', pk=pk)

    if new_status == 'Cancelled' and not cancel_reason:
        messages.error(request, '⚠️ Please provide a reason for cancellation.')
        return redirect('appointment_detail', pk=pk)

    apt.status = new_status
    if new_status == 'Cancelled':
        apt.cancellation_reason = cancel_reason
    apt.save(update_fields=['status', 'cancellation_reason', 'updated_at'])

    messages.success(request, f'✅ Appointment status updated to <strong>{new_status}</strong>.')
    return redirect('appointment_detail', pk=pk)


# ══════════════════════════════════════════════════════════════════════════════
# AJAX — booked times for a given date + doctor
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def booked_slots(request):
    date      = request.GET.get('date', '')
    doctor_id = request.GET.get('doctor', '')

    if not date:
        return JsonResponse({'slots': []})

    qs = Appointment.objects.filter(
        appointment_date=date,
        status__in=['Scheduled', 'In Progress'],
    )
    if doctor_id:
        qs = qs.filter(assigned_to_id=doctor_id)

    slots = list(qs.values_list('time_slot', flat=True))
    return JsonResponse({'slots': slots})