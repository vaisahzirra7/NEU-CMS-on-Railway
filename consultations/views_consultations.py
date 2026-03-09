from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_POST
import json

from consultations.models import Consultation
from appointments.models import Appointment
from patients.models import Patient
from django.conf import settings


def get_user_model():
    from django.contrib.auth import get_user_model
    return get_user_model()


def get_doctors():
    # Doctors, Medical Officers, Admins and Super Admins can be attending doctors
    return get_user_model().objects.filter(
        is_active=True,
        role__name__in=[
            'Doctor', 'Medical Officer', 'doctor', 'medical officer',
            'Admin', 'Super Admin', 'admin', 'super admin',
        ]
    ).order_by('first_name')


# ══════════════════════════════════════════════════════════════════════════════
# LIST
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def consultation_list(request):
    qs = Consultation.objects.select_related(
        'patient', 'doctor', 'appointment'
    ).order_by('-created_at')

    search    = request.GET.get('q', '').strip()
    status    = request.GET.get('status', '')
    doctor_id = request.GET.get('doctor', '')
    date_str  = request.GET.get('date', '')

    if search:
        qs = qs.filter(
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search)  |
            Q(patient__matric_no__icontains=search)  |
            Q(consultation_id__icontains=search)      |
            Q(diagnosis__icontains=search)
        )
    if status:
        qs = qs.filter(status=status)
    if doctor_id:
        qs = qs.filter(doctor_id=doctor_id)
    if date_str:
        qs = qs.filter(created_at__date=date_str)

    today = timezone.localdate()
    context = {
        'consultations':    qs,
        'total_today':      Consultation.objects.filter(created_at__date=today).count(),
        'open_count':       Consultation.objects.filter(status='Open').count(),
        'in_progress':      Consultation.objects.filter(status='In Progress').count(),
        'completed_today':  Consultation.objects.filter(created_at__date=today, status='Completed').count(),
        'doctors':          get_doctors(),
        'status_choices':   Consultation.STATUS_CHOICES,
        'search':           search,
        'filter_status':    status,
        'filter_doctor':    doctor_id,
        'filter_date':      date_str,
        'today':            today.isoformat(),
    }
    return render(request, 'consultations/list.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# CREATE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def consultation_create(request):
    patients     = Patient.objects.filter(is_active=True).order_by('first_name')
    doctors      = get_doctors()
    # Appointments that don't yet have a consultation
    appointments = Appointment.objects.filter(
        status__in=['Scheduled', 'In Progress'],
        consultation__isnull=True,
    ).select_related('patient').order_by('-appointment_date')

    # Pre-fill from appointment if passed
    apt_id = request.GET.get('appointment', '')
    pre_apt = Appointment.objects.filter(pk=apt_id).first() if apt_id else None

    if request.method == 'POST':
        patient_id     = request.POST.get('patient', '')
        appointment_id = request.POST.get('appointment', '')
        doctor_id      = request.POST.get('doctor', '')

        # Vitals
        bp_systolic  = request.POST.get('bp_systolic', '').strip() or None
        bp_diastolic = request.POST.get('bp_diastolic', '').strip() or None
        temperature  = request.POST.get('temperature', '').strip() or None
        pulse        = request.POST.get('pulse', '').strip() or None

        # Extra vitals (dynamic rows)
        extra_labels = request.POST.getlist('extra_label')
        extra_values = request.POST.getlist('extra_value')
        extra_vitals = {}
        for label, val in zip(extra_labels, extra_values):
            label = label.strip()
            val   = val.strip()
            if label and val:
                extra_vitals[label] = val

        # Clinical
        chief_complaint = request.POST.get('chief_complaint', '').strip()
        history         = request.POST.get('history', '').strip()
        examination     = request.POST.get('examination', '').strip()
        diagnosis       = request.POST.get('diagnosis', '').strip()
        icd10_code      = request.POST.get('icd10_code', '').strip()
        icd10_label     = request.POST.get('icd10_label', '').strip()
        management_plan = request.POST.get('management_plan', '').strip()
        follow_up_date  = request.POST.get('follow_up_date', '').strip() or None
        follow_up_notes = request.POST.get('follow_up_notes', '').strip()

        errors = []
        if not patient_id:      errors.append('Patient is required.')
        if not chief_complaint: errors.append('Chief complaint is required.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'consultations/create.html', {
                'patients': patients, 'doctors': doctors,
                'appointments': appointments, 'pre_apt': pre_apt,
                'post': request.POST,
            })

        patient     = get_object_or_404(Patient, pk=patient_id)
        appointment = Appointment.objects.filter(pk=appointment_id).first() if appointment_id else None
        doctor      = get_user_model().objects.filter(pk=doctor_id).first() if doctor_id else None

        con = Consultation.objects.create(
            patient         = patient,
            appointment     = appointment,
            doctor          = doctor,
            bp_systolic     = bp_systolic,
            bp_diastolic    = bp_diastolic,
            temperature     = temperature,
            pulse           = pulse,
            extra_vitals    = extra_vitals,
            chief_complaint = chief_complaint,
            history         = history,
            examination     = examination,
            diagnosis       = diagnosis,
            icd10_code      = icd10_code,
            icd10_label     = icd10_label,
            management_plan = management_plan,
            follow_up_date  = follow_up_date,
            follow_up_notes = follow_up_notes,
            status          = 'Open',
            created_by      = request.user,
        )

        # If linked to appointment, mark appointment In Progress
        if appointment and appointment.status == 'Scheduled':
            appointment.status = 'In Progress'
            appointment.save(update_fields=['status', 'updated_at'])

        messages.success(request, f'✅ Consultation <strong>{con.consultation_id}</strong> started successfully.')
        return redirect('consultation_detail', pk=con.pk)

    return render(request, 'consultations/create.html', {
        'patients':     patients,
        'doctors':      doctors,
        'appointments': appointments,
        'pre_apt':      pre_apt,
        'today':        timezone.localdate().isoformat(),
    })


# ══════════════════════════════════════════════════════════════════════════════
# DETAIL
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def consultation_detail(request, pk):
    con = get_object_or_404(
        Consultation.objects.select_related('patient', 'doctor', 'appointment'),
        pk=pk
    )
    return render(request, 'consultations/detail.html', {'con': con})


# ══════════════════════════════════════════════════════════════════════════════
# EDIT
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def consultation_edit(request, pk):
    con     = get_object_or_404(Consultation, pk=pk)
    doctors = get_doctors()

    if con.status == 'Completed':
        messages.error(request, '⛔ Completed consultations cannot be edited.')
        return redirect('consultation_detail', pk=pk)

    if request.method == 'POST':
        doctor_id      = request.POST.get('doctor', '')
        bp_systolic    = request.POST.get('bp_systolic', '').strip() or None
        bp_diastolic   = request.POST.get('bp_diastolic', '').strip() or None
        temperature    = request.POST.get('temperature', '').strip() or None
        pulse          = request.POST.get('pulse', '').strip() or None

        extra_labels = request.POST.getlist('extra_label')
        extra_values = request.POST.getlist('extra_value')
        extra_vitals = {}
        for label, val in zip(extra_labels, extra_values):
            label = label.strip(); val = val.strip()
            if label and val:
                extra_vitals[label] = val

        con.doctor          = get_user_model().objects.filter(pk=doctor_id).first() if doctor_id else None
        con.bp_systolic     = bp_systolic
        con.bp_diastolic    = bp_diastolic
        con.temperature     = temperature
        con.pulse           = pulse
        con.extra_vitals    = extra_vitals
        con.chief_complaint = request.POST.get('chief_complaint', '').strip()
        con.history         = request.POST.get('history', '').strip()
        con.examination     = request.POST.get('examination', '').strip()
        con.diagnosis       = request.POST.get('diagnosis', '').strip()
        con.icd10_code      = request.POST.get('icd10_code', '').strip()
        con.icd10_label     = request.POST.get('icd10_label', '').strip()
        con.management_plan = request.POST.get('management_plan', '').strip()
        con.follow_up_date  = request.POST.get('follow_up_date', '').strip() or None
        con.follow_up_notes = request.POST.get('follow_up_notes', '').strip()
        con.save()

        messages.success(request, f'✅ Consultation <strong>{con.consultation_id}</strong> updated.')
        return redirect('consultation_detail', pk=pk)

    return render(request, 'consultations/edit.html', {
        'con':     con,
        'doctors': doctors,
    })


# ══════════════════════════════════════════════════════════════════════════════
# UPDATE STATUS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def consultation_update_status(request, pk):
    con        = get_object_or_404(Consultation, pk=pk)
    new_status = request.POST.get('status', '')

    valid = ['Open', 'In Progress', 'Completed']
    if new_status not in valid:
        messages.error(request, 'Invalid status.')
        return redirect('consultation_detail', pk=pk)

    con.status = new_status
    con.save(update_fields=['status', 'updated_at'])

    # When consultation completed, mark linked appointment completed too
    if new_status == 'Completed' and con.appointment:
        con.appointment.status = 'Completed'
        con.appointment.save(update_fields=['status', 'updated_at'])

    messages.success(request, f'✅ Consultation marked as <strong>{new_status}</strong>.')
    return redirect('consultation_detail', pk=pk)


# ══════════════════════════════════════════════════════════════════════════════
# AJAX — load patient's appointments for the create form
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def patient_appointments(request):
    patient_id = request.GET.get('patient', '')
    if not patient_id:
        return JsonResponse({'appointments': []})

    apts = Appointment.objects.filter(
        patient_id=patient_id,
        status__in=['Scheduled', 'In Progress'],
        consultation__isnull=True,
    ).order_by('-appointment_date')

    data = [
        {
            'id':    a.pk,
            'label': f'{a.appointment_id} — {a.appointment_date} {a.time_slot} ({a.get_type_display_full()})',
            'doctor_id': a.assigned_to_id or '',
        }
        for a in apts
    ]
    return JsonResponse({'appointments': data})