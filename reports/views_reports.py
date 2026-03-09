import json
import csv
import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.permissions import permission_required

from django.http import HttpResponse
from django.db.models import Count, Q, Avg
from django.db.models.functions import TruncMonth, TruncDate, TruncWeek
from django.utils import timezone


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _parse_filters(request):
    """Extract common filters from GET params."""
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')
    session   = request.GET.get('session', '')
    faculty   = request.GET.get('faculty', '')
    dept      = request.GET.get('department', '')

    # Default: all time (wide range to catch all data)
    if not date_from:
        date_from = '2020-01-01'
    if not date_to:
        date_to = timezone.now().strftime('%Y-%m-%d')

    return {
        'date_from': date_from,
        'date_to':   date_to,
        'session':   session,
        'faculty':   faculty,
        'department': dept,
    }


def _month_labels(qs, date_field='created_at__date'):
    """Convert a monthly-annotated queryset to chart-ready lists."""
    labels = [r['month'].strftime('%b %Y') for r in qs]
    values = [r['count'] for r in qs]
    return labels, values


# ══════════════════════════════════════════════════════════════════════════════
# MAIN REPORTS VIEW
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('reports', 'view')
def reports_dashboard(request):
    from patients.models import Patient, Faculty, Department
    from consultations.models import Consultation
    from laboratory.models import LabRequest, LabResult, LabTest
    from prescriptions.models import Prescription, PrescriptionItem
    from clearance.models import ClearanceSubmission, ClearanceSession

    f = _parse_filters(request)
    # Use timezone-aware datetimes to avoid UTC offset issues with __date lookups
    tz      = timezone.get_current_timezone()
    df      = timezone.make_aware(datetime.datetime.strptime(f['date_from'], '%Y-%m-%d'), tz)
    dt      = timezone.make_aware(datetime.datetime.strptime(f['date_to'],   '%Y-%m-%d').replace(hour=23, minute=59, second=59), tz)

    # ── PATIENT ANALYTICS ─────────────────────────────────────────────────────
    patients_qs = Patient.objects.filter(created_at__gte=df, created_at__lte=dt)
    if f['faculty']:
        patients_qs = patients_qs.filter(faculty_id=f['faculty'])
    if f['department']:
        patients_qs = patients_qs.filter(department_id=f['department'])

    # Registrations per month
    reg_monthly = (
        patients_qs.annotate(month=TruncMonth('created_at'))
        .values('month').annotate(count=Count('pk')).order_by('month')
    )
    reg_labels, reg_values = _month_labels(reg_monthly)

    # By gender
    gender_data = list(
        patients_qs.values('gender').annotate(count=Count('pk')).order_by('-count')
    )

    # By patient type
    ptype_data = list(
        patients_qs.values('patient_type').annotate(count=Count('pk')).order_by('-count')
    )

    # By faculty (top 8)
    faculty_data = list(
        patients_qs.filter(faculty__isnull=False)
        .values('faculty__name').annotate(count=Count('pk')).order_by('-count')[:8]
    )

    # By blood group (all time — not filtered by date)
    blood_data = list(
        Patient.objects.exclude(blood_group='Unknown')
        .values('blood_group').annotate(count=Count('pk')).order_by('-count')
    )

    # Totals (all time)
    total_patients    = Patient.objects.count()
    active_patients   = Patient.objects.filter(is_active=True).count()
    inactive_patients = Patient.objects.filter(is_active=False).count()
    new_this_period   = patients_qs.count()

    # ── CLINICAL REPORTS ──────────────────────────────────────────────────────
    consult_qs = Consultation.objects.filter(created_at__gte=df, created_at__lte=dt)
    if f['faculty']:
        consult_qs = consult_qs.filter(patient__faculty_id=f['faculty'])
    if f['department']:
        consult_qs = consult_qs.filter(patient__department_id=f['department'])

    # Consultations per month
    consult_monthly = (
        consult_qs.annotate(month=TruncMonth('created_at'))
        .values('month').annotate(count=Count('pk')).order_by('month')
    )
    consult_labels, consult_values = _month_labels(consult_monthly)

    # Top diagnoses (split on comma/newline, count occurrences)
    diagnoses_raw = list(
        consult_qs.exclude(diagnosis='').values_list('diagnosis', flat=True)
    )
    diag_counter = {}
    for d in diagnoses_raw:
        for part in d.replace('\n', ',').split(','):
            key = part.strip().title()
            if key and len(key) > 2:
                diag_counter[key] = diag_counter.get(key, 0) + 1
    top_diagnoses = sorted(diag_counter.items(), key=lambda x: -x[1])[:10]
    diag_labels = [d[0] for d in top_diagnoses]
    diag_values = [d[1] for d in top_diagnoses]

    # By status
    consult_status = list(
        consult_qs.values('status').annotate(count=Count('pk')).order_by('-count')
    )

    total_consultations = consult_qs.count()

    # ── LABORATORY REPORTS ────────────────────────────────────────────────────
    lab_qs = LabRequest.objects.filter(created_at__gte=df, created_at__lte=dt)

    # Lab requests per month
    lab_monthly = (
        lab_qs.annotate(month=TruncMonth('created_at'))
        .values('month').annotate(count=Count('pk')).order_by('month')
    )
    lab_labels, lab_values = _month_labels(lab_monthly)

    # Top tests ordered
    top_tests = list(
        LabResult.objects.filter(request__in=lab_qs)
        .values('test__name').annotate(count=Count('pk')).order_by('-count')[:10]
    )
    test_labels = [t['test__name'] for t in top_tests]
    test_values = [t['count'] for t in top_tests]

    # By status
    lab_status = list(
        lab_qs.values('status').annotate(count=Count('pk')).order_by('-count')
    )

    # Interpretation breakdown
    interp_data = list(
        LabResult.objects.filter(request__in=lab_qs)
        .values('interpretation').annotate(count=Count('pk')).order_by('-count')
    )

    total_lab     = lab_qs.count()
    completed_lab = lab_qs.filter(status='Completed').count()

    # ── PHARMACY REPORTS ──────────────────────────────────────────────────────
    rx_qs = Prescription.objects.filter(created_at__gte=df, created_at__lte=dt)

    # Prescriptions per month
    rx_monthly = (
        rx_qs.annotate(month=TruncMonth('created_at'))
        .values('month').annotate(count=Count('pk')).order_by('month')
    )
    rx_labels, rx_values = _month_labels(rx_monthly)

    # Top dispensed drugs
    top_drugs = list(
        PrescriptionItem.objects.filter(prescription__in=rx_qs)
        .values('drug__name').annotate(count=Count('pk')).order_by('-count')[:10]
    )
    drug_labels = [d['drug__name'] for d in top_drugs]
    drug_values = [d['count'] for d in top_drugs]

    # Prescription status
    rx_status = list(
        rx_qs.values('status').annotate(count=Count('pk')).order_by('-count')
    )

    total_rx     = rx_qs.count()
    dispensed_rx = rx_qs.filter(status='Dispensed').count()
    pending_rx   = rx_qs.filter(status='Pending').count()

    # ── CLEARANCE REPORTS ─────────────────────────────────────────────────────
    clearance_qs = ClearanceSubmission.objects.filter(submitted_at__gte=df, submitted_at__lte=dt)
    if f['session']:
        clearance_qs = clearance_qs.filter(session_id=f['session'])
    if f['faculty']:
        clearance_qs = clearance_qs.filter(patient__faculty_id=f['faculty'])
    if f['department']:
        clearance_qs = clearance_qs.filter(patient__department_id=f['department'])

    # Submissions per month
    cl_monthly = (
        clearance_qs.annotate(month=TruncMonth('submitted_at'))
        .values('month').annotate(count=Count('pk')).order_by('month')
    )
    cl_labels, cl_values = _month_labels(cl_monthly)

    # Approval rate
    cl_status = list(
        clearance_qs.values('status').annotate(count=Count('pk')).order_by('-count')
    )

    # By session
    cl_by_session = list(
        clearance_qs.values('session__academic_session', 'session__stream')
        .annotate(total=Count('pk'), approved=Count('pk', filter=Q(status='Approved')))
        .order_by('-session__academic_session')[:8]
    )

    # By faculty
    cl_by_faculty = list(
        clearance_qs.filter(patient__faculty__isnull=False)
        .values('patient__faculty__name')
        .annotate(total=Count('pk'), approved=Count('pk', filter=Q(status='Approved')))
        .order_by('-total')[:8]
    )

    total_cl   = clearance_qs.count()
    approved_cl = clearance_qs.filter(status='Approved').count()
    approval_rate = round((approved_cl / total_cl * 100), 1) if total_cl else 0

    # ── FILTER OPTIONS ────────────────────────────────────────────────────────
    faculties   = Faculty.objects.filter(is_active=True).order_by('name')
    departments = Department.objects.filter(is_active=True).order_by('name')
    if f['faculty']:
        departments = departments.filter(faculty_id=f['faculty'])
    sessions = ClearanceSession.objects.order_by('-academic_session')

    # ══ CONTEXT ══════════════════════════════════════════════════════════════
    context = {
        'filters': f,
        'faculties':   faculties,
        'departments': departments,
        'sessions':    sessions,
        'active_tab':  request.GET.get('tab', 'patients'),

        # Patient
        'total_patients':   total_patients,
        'active_patients':  active_patients,
        'inactive_patients': inactive_patients,
        'new_this_period':  new_this_period,
        'reg_labels':       reg_labels,
        'reg_values':       reg_values,
        'gender_data':      gender_data,
        'ptype_data':       ptype_data,
        'faculty_data':     faculty_data,
        'blood_data':       blood_data,

        # Clinical
        'total_consultations': total_consultations,
        'consult_labels':   consult_labels,
        'consult_values':   consult_values,
        'diag_labels':      diag_labels,
        'diag_values':      diag_values,
        'consult_status':   consult_status,

        # Lab
        'total_lab':        total_lab,
        'completed_lab':    completed_lab,
        'lab_labels':       lab_labels,
        'lab_values':       lab_values,
        'test_labels':      test_labels,
        'test_values':      test_values,
        'lab_status':       lab_status,
        'interp_data':      interp_data,

        # Pharmacy
        'total_rx':         total_rx,
        'dispensed_rx':     dispensed_rx,
        'pending_rx':       pending_rx,
        'rx_labels':        rx_labels,
        'rx_values':        rx_values,
        'drug_labels':      drug_labels,
        'drug_values':      drug_values,
        'rx_status':        rx_status,

        # Clearance
        'total_cl':         total_cl,
        'approved_cl':      approved_cl,
        'approval_rate':    approval_rate,
        'cl_labels':        cl_labels,
        'cl_values':        cl_values,
        'cl_status':        cl_status,
        'cl_by_session':    cl_by_session,
        'cl_by_faculty':    json.dumps(cl_by_faculty),  # needs safe serialization for inline JS
    }
    return render(request, 'reports/dashboard.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# CSV EXPORTS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('reports', 'export')
def export_csv(request, report_type):
    from patients.models import Patient
    from consultations.models import Consultation
    from laboratory.models import LabRequest
    from prescriptions.models import Prescription
    from clearance.models import ClearanceSubmission

    f  = _parse_filters(request)
    tz = timezone.get_current_timezone()
    df = timezone.make_aware(datetime.datetime.strptime(f['date_from'], '%Y-%m-%d'), tz)
    dt = timezone.make_aware(datetime.datetime.strptime(f['date_to'],   '%Y-%m-%d').replace(hour=23, minute=59, second=59), tz)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="neu_{report_type}_{f["date_from"]}_to_{f["date_to"]}.csv"'
    writer = csv.writer(response)

    if report_type == 'patients':
        writer.writerow(['Matric No', 'Full Name', 'Gender', 'Patient Type', 'Faculty', 'Department', 'Level', 'Blood Group', 'Registered'])
        qs = Patient.objects.filter(created_at__gte=df, created_at__lte=dt).select_related('faculty', 'department')
        for p in qs:
            writer.writerow([p.matric_no, p.get_full_name(), p.gender, p.patient_type,
                             str(p.faculty or ''), str(p.department or ''), p.level,
                             p.blood_group, p.created_at.strftime('%Y-%m-%d')])

    elif report_type == 'clinical':
        writer.writerow(['Consultation ID', 'Patient', 'Matric No', 'Diagnosis', 'Status', 'Date'])
        qs = Consultation.objects.filter(created_at__gte=df, created_at__lte=dt).select_related('patient')
        for c in qs:
            writer.writerow([c.consultation_id, c.patient.get_full_name(), c.patient.matric_no,
                             c.diagnosis, c.status, c.created_at.strftime('%Y-%m-%d')])

    elif report_type == 'laboratory':
        writer.writerow(['Lab ID', 'Patient', 'Matric No', 'Status', 'Priority', 'Date'])
        qs = LabRequest.objects.filter(created_at__gte=df, created_at__lte=dt).select_related('patient')
        for r in qs:
            writer.writerow([r.lab_id, r.patient.get_full_name(), r.patient.matric_no,
                             r.status, r.priority, r.created_at.strftime('%Y-%m-%d')])

    elif report_type == 'pharmacy':
        writer.writerow(['Prescription ID', 'Patient', 'Matric No', 'Status', 'Date'])
        qs = Prescription.objects.filter(created_at__gte=df, created_at__lte=dt).select_related('patient')
        for rx in qs:
            writer.writerow([rx.prescription_id, rx.patient.get_full_name(), rx.patient.matric_no,
                             rx.status, rx.created_at.strftime('%Y-%m-%d')])

    elif report_type == 'clearance':
        writer.writerow(['Submission ID', 'Patient', 'Matric No', 'Session', 'Stream', 'Status', 'Submitted'])
        qs = ClearanceSubmission.objects.filter(submitted_at__gte=df, submitted_at__lte=dt).select_related('patient', 'session')
        for s in qs:
            writer.writerow([s.submission_id, s.patient.get_full_name(), s.patient.matric_no,
                             s.session.academic_session, s.session.stream,
                             s.status, s.submitted_at.strftime('%Y-%m-%d')])

    return response