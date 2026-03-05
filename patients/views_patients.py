import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from .models import (
    Patient, Faculty, Department, Programme,
    GENDER_CHOICES, MARITAL_CHOICES, LEVEL_CHOICES,
    RELIGION_CHOICES, BLOOD_GROUP_CHOICES,
    GENOTYPE_CHOICES, PATIENT_TYPE_CHOICES,
)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')


def log_patient_action(user, action, patient, description='', request=None):
    try:
        from accounts.models import AuditTrail
        AuditTrail.objects.create(
            user        = user,
            action      = action,
            module      = 'patient-records',
            record_id   = str(patient.matric_no),
            description = description,
            ip_address  = get_client_ip(request) if request else None,
        )
    except Exception:
        pass


def form_choices():
    """Return all dropdown choices needed by create/edit forms."""
    return {
        'faculties':       Faculty.objects.filter(is_active=True).order_by('name'),
        'departments':     Department.objects.filter(is_active=True).order_by('name'),
        'programmes':      Programme.objects.filter(is_active=True).order_by('name'),
        'gender_choices':  GENDER_CHOICES,
        'marital_choices': MARITAL_CHOICES,
        'level_choices':   LEVEL_CHOICES,
        'religion_choices':RELIGION_CHOICES,
        'blood_choices':   BLOOD_GROUP_CHOICES,
        'genotype_choices':GENOTYPE_CHOICES,
        'type_choices':    PATIENT_TYPE_CHOICES,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PATIENT LIST
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def patient_list(request):
    qs = Patient.objects.select_related(
             'faculty', 'department', 'programme'
         ).all()

    q            = request.GET.get('q', '').strip()
    faculty_id   = request.GET.get('faculty', '').strip()
    programme_id = request.GET.get('programme', '').strip()
    level        = request.GET.get('level', '').strip()
    status       = request.GET.get('status', '').strip()
    blood_grp    = request.GET.get('blood_group', '').strip()

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)  |
            Q(last_name__icontains=q)   |
            Q(other_names__icontains=q) |
            Q(matric_no__icontains=q)   |
            Q(nin__icontains=q)         |
            Q(phone__icontains=q)       |
            Q(email__icontains=q)
        )
    if faculty_id:
        qs = qs.filter(faculty__id=faculty_id)
    if programme_id:
        qs = qs.filter(programme__id=programme_id)
    if level:
        qs = qs.filter(level=level)
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)
    if blood_grp:
        qs = qs.filter(blood_group=blood_grp)

    context = {
        'patients':      qs,
        'faculties':     Faculty.objects.filter(is_active=True).order_by('name'),
        'programmes':    Programme.objects.filter(is_active=True).order_by('name'),
        'level_choices': LEVEL_CHOICES,
        'blood_choices': BLOOD_GROUP_CHOICES,
        'q':             q,
        'sel_faculty':   faculty_id,
        'sel_programme': programme_id,
        'sel_level':     level,
        'sel_status':    status,
        'sel_blood':     blood_grp,
        'total':         Patient.objects.count(),
        'active_ct':     Patient.objects.filter(is_active=True).count(),
        'inactive_ct':   Patient.objects.filter(is_active=False).count(),
        'today_ct':      Patient.objects.filter(
                             created_at__date=timezone.now().date()
                         ).count(),
    }
    return render(request, 'patients/list.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# CREATE PATIENT
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def patient_create(request):
    ctx = form_choices()

    if request.method == 'POST':
        p      = request.POST
        errors = []

        if not p.get('matric_no', '').strip():
            errors.append('Matric / Student ID is required.')
        elif Patient.objects.filter(matric_no=p['matric_no'].strip().upper()).exists():
            errors.append(
                f'A patient with matric number '
                f'<strong>{p["matric_no"].strip()}</strong> already exists.'
            )
        if not p.get('first_name', '').strip():
            errors.append('First name is required.')
        if not p.get('last_name', '').strip():
            errors.append('Last name is required.')

        if errors:
            for e in errors:
                messages.error(request, e)
            ctx['form'] = p
            return render(request, 'patients/create.html', ctx)

        faculty    = Faculty.objects.filter(id=p.get('faculty')).first()    if p.get('faculty')    else None
        department = Department.objects.filter(id=p.get('department')).first() if p.get('department') else None
        programme  = Programme.objects.filter(id=p.get('programme')).first()  if p.get('programme')  else None
        photo      = request.FILES.get('photo') or None

        patient = Patient.objects.create(
            matric_no           = p['matric_no'].strip().upper(),
            patient_type        = p.get('patient_type', 'Student'),
            first_name          = p['first_name'].strip(),
            last_name           = p['last_name'].strip(),
            other_names         = p.get('other_names', '').strip(),
            photo               = photo,
            date_of_birth       = p.get('date_of_birth') or None,
            gender              = p.get('gender', ''),
            marital_status      = p.get('marital_status', ''),
            religion            = p.get('religion', ''),
            nationality         = p.get('nationality', 'Nigerian').strip(),
            state_of_origin     = p.get('state_of_origin', '').strip(),
            lga                 = p.get('lga', '').strip(),
            home_address        = p.get('home_address', '').strip(),
            phone               = p.get('phone', '').strip(),
            email               = p.get('email', '').strip().lower(),
            nin                 = p.get('nin', '').strip(),
            faculty             = faculty,
            department          = department,
            programme           = programme,
            level               = p.get('level', ''),
            academic_session    = p.get('academic_session', '').strip(),
            blood_group         = p.get('blood_group', 'Unknown'),
            genotype            = p.get('genotype', 'Unknown'),
            allergies           = p.get('allergies', '').strip(),
            chronic_conditions  = p.get('chronic_conditions', '').strip(),
            disabilities        = p.get('disabilities', '').strip(),
            current_medications = p.get('current_medications', '').strip(),
            surgical_history    = p.get('surgical_history', '').strip(),
            family_history      = p.get('family_history', '').strip(),
            emergency_name         = p.get('emergency_name', '').strip(),
            emergency_relationship = p.get('emergency_relationship', '').strip(),
            emergency_phone        = p.get('emergency_phone', '').strip(),
            emergency_address      = p.get('emergency_address', '').strip(),
            nok_name         = p.get('nok_name', '').strip(),
            nok_relationship = p.get('nok_relationship', '').strip(),
            nok_phone        = p.get('nok_phone', '').strip(),
            nok_address      = p.get('nok_address', '').strip(),
            notes            = p.get('notes', '').strip(),
            registered_by    = request.user,
            sync_source      = 'MANUAL',
        )

        log_patient_action(
            request.user, 'CREATE', patient,
            description = f'Registered {patient.get_full_name()} ({patient.matric_no})',
            request     = request,
        )

        messages.success(
            request,
            f'✅ Patient <strong>{patient.get_full_name()}</strong> '
            f'({patient.matric_no}) registered successfully.'
        )
        return redirect('patient_detail', matric_no=patient.matric_no)

    ctx['form'] = {}
    return render(request, 'patients/create.html', ctx)


# ══════════════════════════════════════════════════════════════════════════════
# PATIENT DETAIL
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def patient_detail(request, matric_no):
    patient = get_object_or_404(
                  Patient.objects.select_related(
                      'faculty', 'department', 'programme', 'registered_by'
                  ),
                  matric_no=matric_no
              )
    return render(request, 'patients/detail.html', {'patient': patient})


# ══════════════════════════════════════════════════════════════════════════════
# EDIT PATIENT
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def patient_edit(request, matric_no):
    patient = get_object_or_404(Patient, matric_no=matric_no)
    ctx     = form_choices()
    ctx['patient'] = patient

    if request.method == 'POST':
        p = request.POST

        faculty    = Faculty.objects.filter(id=p.get('faculty')).first()       if p.get('faculty')    else None
        department = Department.objects.filter(id=p.get('department')).first() if p.get('department') else None
        programme  = Programme.objects.filter(id=p.get('programme')).first()   if p.get('programme')  else None

        if request.FILES.get('photo'):
            patient.photo = request.FILES['photo']

        patient.patient_type        = p.get('patient_type', patient.patient_type)
        patient.first_name          = p.get('first_name', patient.first_name).strip()
        patient.last_name           = p.get('last_name', patient.last_name).strip()
        patient.other_names         = p.get('other_names', '').strip()
        patient.date_of_birth       = p.get('date_of_birth') or None
        patient.gender              = p.get('gender', '')
        patient.marital_status      = p.get('marital_status', '')
        patient.religion            = p.get('religion', '')
        patient.nationality         = p.get('nationality', 'Nigerian').strip()
        patient.state_of_origin     = p.get('state_of_origin', '').strip()
        patient.lga                 = p.get('lga', '').strip()
        patient.home_address        = p.get('home_address', '').strip()
        patient.phone               = p.get('phone', '').strip()
        patient.email               = p.get('email', '').strip().lower()
        patient.nin                 = p.get('nin', '').strip()
        patient.faculty             = faculty
        patient.department          = department
        patient.programme           = programme
        patient.level               = p.get('level', '')
        patient.academic_session    = p.get('academic_session', '').strip()
        patient.blood_group         = p.get('blood_group', 'Unknown')
        patient.genotype            = p.get('genotype', 'Unknown')
        patient.allergies           = p.get('allergies', '').strip()
        patient.chronic_conditions  = p.get('chronic_conditions', '').strip()
        patient.disabilities        = p.get('disabilities', '').strip()
        patient.current_medications = p.get('current_medications', '').strip()
        patient.surgical_history    = p.get('surgical_history', '').strip()
        patient.family_history      = p.get('family_history', '').strip()
        patient.emergency_name         = p.get('emergency_name', '').strip()
        patient.emergency_relationship = p.get('emergency_relationship', '').strip()
        patient.emergency_phone        = p.get('emergency_phone', '').strip()
        patient.emergency_address      = p.get('emergency_address', '').strip()
        patient.nok_name         = p.get('nok_name', '').strip()
        patient.nok_relationship = p.get('nok_relationship', '').strip()
        patient.nok_phone        = p.get('nok_phone', '').strip()
        patient.nok_address      = p.get('nok_address', '').strip()
        patient.notes            = p.get('notes', '').strip()
        patient.save()

        log_patient_action(
            request.user, 'UPDATE', patient,
            description = f'Updated record: {patient.get_full_name()} ({patient.matric_no})',
            request     = request,
        )

        messages.success(request, f'✅ {patient.get_full_name()}\'s record has been updated.')
        return redirect('patient_detail', matric_no=patient.matric_no)

    return render(request, 'patients/edit.html', ctx)


# ══════════════════════════════════════════════════════════════════════════════
# TOGGLE STATUS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def patient_toggle_status(request, matric_no):
    patient           = get_object_or_404(Patient, matric_no=matric_no)
    patient.is_active = not patient.is_active
    patient.save(update_fields=['is_active'])

    action = 'activated' if patient.is_active else 'deactivated'
    log_patient_action(
        request.user, 'UPDATE', patient,
        description = f'Patient record {action}: {patient.get_full_name()}',
        request     = request,
    )

    messages.success(request, f'✅ {patient.get_full_name()}\'s record has been {action}.')
    return redirect('patient_detail', matric_no=matric_no)


# ══════════════════════════════════════════════════════════════════════════════
# AJAX — DEPARTMENTS & PROGRAMMES BY FACULTY
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def faculty_departments(request, faculty_id):
    depts = Department.objects.filter(
                faculty__id=faculty_id, is_active=True
            ).order_by('name').values('id', 'name')
    return JsonResponse({'departments': list(depts)})


@login_required
def faculty_programmes(request, faculty_id):
    progs = Programme.objects.filter(
                faculty__id=faculty_id, is_active=True
            ).order_by('name').values('id', 'name', 'duration')
    return JsonResponse({'programmes': list(progs)})


# ══════════════════════════════════════════════════════════════════════════════
# CSV IMPORT
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def patient_import(request):
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')

        if not csv_file:
            messages.error(request, 'Please select a CSV file to upload.')
            return redirect('patient_import')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File must be a .csv file.')
            return redirect('patient_import')

        try:
            decoded = csv_file.read().decode('utf-8')
        except UnicodeDecodeError:
            decoded = csv_file.read().decode('latin-1')

        reader  = csv.DictReader(io.StringIO(decoded))
        created = 0
        skipped = 0
        errors  = []

        required_cols = {'matric_no', 'first_name', 'last_name'}
        if not required_cols.issubset(set(reader.fieldnames or [])):
            messages.error(
                request,
                f'CSV is missing required columns: {", ".join(required_cols)}. '
                f'Download the template for the correct format.'
            )
            return redirect('patient_import')

        for i, row in enumerate(reader, start=2):
            matric_no = row.get('matric_no', '').strip().upper()
            first     = row.get('first_name', '').strip()
            last      = row.get('last_name', '').strip()

            if not matric_no or not first or not last:
                errors.append(f'Row {i}: Missing required field — skipped.')
                skipped += 1
                continue

            if Patient.objects.filter(matric_no=matric_no).exists():
                errors.append(f'Row {i}: <strong>{matric_no}</strong> already exists — skipped.')
                skipped += 1
                continue

            # Resolve Faculty
            faculty = None
            fac_name = row.get('faculty', '').strip()
            if fac_name:
                faculty, _ = Faculty.objects.get_or_create(
                    name=fac_name, defaults={'is_active': True}
                )

            # Resolve Department
            department = None
            dep_name = row.get('department', '').strip()
            if dep_name and faculty:
                department, _ = Department.objects.get_or_create(
                    name=dep_name, faculty=faculty,
                    defaults={'is_active': True}
                )

            # Resolve Programme
            programme = None
            prog_name = row.get('programme', '').strip()
            if prog_name and faculty:
                programme, _ = Programme.objects.get_or_create(
                    name=prog_name, faculty=faculty,
                    defaults={'department': department, 'is_active': True}
                )

            try:
                Patient.objects.create(
                    matric_no        = matric_no,
                    first_name       = first,
                    last_name        = last,
                    other_names      = row.get('other_names', '').strip(),
                    patient_type     = row.get('patient_type', 'Student'),
                    date_of_birth    = row.get('date_of_birth') or None,
                    gender           = row.get('gender', ''),
                    phone            = row.get('phone', '').strip(),
                    email            = row.get('email', '').strip().lower(),
                    nin              = row.get('nin', '').strip(),
                    faculty          = faculty,
                    department       = department,
                    programme        = programme,
                    level            = row.get('level', ''),
                    academic_session = row.get('academic_session', '').strip(),
                    blood_group      = row.get('blood_group', 'Unknown'),
                    genotype         = row.get('genotype', 'Unknown'),
                    state_of_origin  = row.get('state_of_origin', '').strip(),
                    nationality      = row.get('nationality', 'Nigerian').strip(),
                    allergies        = row.get('allergies', '').strip(),
                    chronic_conditions = row.get('chronic_conditions', '').strip(),
                    emergency_name   = row.get('emergency_name', '').strip(),
                    emergency_phone  = row.get('emergency_phone', '').strip(),
                    registered_by    = request.user,
                    sync_source      = 'CSV_IMPORT',
                )
                created += 1
            except Exception as e:
                errors.append(f'Row {i}: Error — {str(e)}')
                skipped += 1

        if created:
            messages.success(
                request,
                f'✅ Import complete. <strong>{created}</strong> patient record'
                f'{"s" if created != 1 else ""} imported.'
                f'{" " + str(skipped) + " skipped." if skipped else ""}'
            )
        if errors:
            for e in errors[:10]:
                messages.warning(request, e)
            if len(errors) > 10:
                messages.warning(request, f'… and {len(errors) - 10} more issues.')

        return redirect('patient_list')

    return render(request, 'patients/import.html')


# ══════════════════════════════════════════════════════════════════════════════
# DOWNLOAD CSV TEMPLATE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def download_csv_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="patient_import_template.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'matric_no', 'first_name', 'last_name', 'other_names',
        'patient_type', 'date_of_birth', 'gender', 'phone', 'email', 'nin',
        'faculty', 'department', 'programme', 'level', 'academic_session',
        'blood_group', 'genotype', 'state_of_origin', 'nationality',
        'allergies', 'chronic_conditions',
        'emergency_name', 'emergency_phone',
    ])
    writer.writerow([
        'NEU/2024/001', 'Amina', 'Babangida', 'Grace',
        'Student', '2002-05-14', 'Female', '08012345678', 'amina@neu.edu.ng', '12345678901',
        'Faculty of Medicine', 'Medicine & Surgery', 'Medicine & Surgery', '300', '2022/2023',
        'O+', 'AA', 'Kano', 'Nigerian',
        'Penicillin', 'Asthma',
        'Ibrahim Babangida', '08098765432',
    ])

    return response