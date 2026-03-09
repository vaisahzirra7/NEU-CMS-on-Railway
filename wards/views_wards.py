from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.permissions import permission_required

from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_POST

from wards.models import Ward, Bed, Admission, TransferLog


# ══════════════════════════════════════════════════════════════════════════════
# WARD OVERVIEW — occupancy dashboard
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('wards', 'view')
def ward_overview(request):
    wards = Ward.objects.filter(is_active=True).prefetch_related('beds')

    total_beds       = sum(w.total_beds       for w in wards)
    total_available  = sum(w.available_beds   for w in wards)
    total_occupied   = sum(w.occupied_beds    for w in wards)
    total_reserved   = sum(w.reserved_beds    for w in wards)
    total_maintenance= sum(w.maintenance_beds for w in wards)

    context = {
        'wards':             wards,
        'total_beds':        total_beds,
        'total_available':   total_available,
        'total_occupied':    total_occupied,
        'total_reserved':    total_reserved,
        'total_maintenance': total_maintenance,
        'current_admissions':Admission.objects.filter(status='Admitted').count(),
    }
    return render(request, 'wards/overview.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# WARD DETAIL — beds grid for one ward
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('wards', 'view')
def ward_detail(request, pk):
    ward       = get_object_or_404(Ward, pk=pk)
    beds       = ward.beds.prefetch_related('admissions').all()
    admissions = Admission.objects.filter(
                     ward=ward, status='Admitted'
                 ).select_related('patient', 'bed', 'admitting_doctor')

    context = {'ward': ward, 'beds': beds, 'admissions': admissions}
    return render(request, 'wards/ward_detail.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# WARD SETUP — create/manage wards and beds
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('wards', 'edit')
def ward_setup(request):
    wards = Ward.objects.prefetch_related('beds').all()

    if request.method == 'POST':
        action = request.POST.get('action', '')

        # --- Create Ward ---
        if action == 'create_ward':
            name = request.POST.get('name', '').strip()
            desc = request.POST.get('description', '').strip()
            if not name:
                messages.error(request, 'Ward name is required.')
            elif Ward.objects.filter(name__iexact=name).exists():
                messages.error(request, f'A ward named "{name}" already exists.')
            else:
                Ward.objects.create(name=name, description=desc)
                messages.success(request, f'✅ Ward <strong>{name}</strong> created.')
            return redirect('ward_setup')

        # --- Add Bed to Ward ---
        elif action == 'add_bed':
            ward_id    = request.POST.get('ward_id', '').strip()
            bed_number = request.POST.get('bed_number', '').strip()
            bed_notes  = request.POST.get('bed_notes', '').strip()
            try:
                ward = Ward.objects.get(pk=ward_id)
            except Ward.DoesNotExist:
                messages.error(request, 'Ward not found.')
                return redirect('ward_setup')
            if not bed_number:
                messages.error(request, 'Bed number is required.')
            elif Bed.objects.filter(ward=ward, bed_number__iexact=bed_number).exists():
                messages.error(request, f'Bed "{bed_number}" already exists in {ward.name}.')
            else:
                Bed.objects.create(ward=ward, bed_number=bed_number, notes=bed_notes)
                messages.success(request, f'✅ Bed <strong>{bed_number}</strong> added to {ward.name}.')
            return redirect('ward_setup')

        # --- Update Bed Status ---
        elif action == 'update_bed_status':
            bed_id = request.POST.get('bed_id', '').strip()
            status = request.POST.get('status', '').strip()
            try:
                bed = Bed.objects.get(pk=bed_id)
                if bed.status == 'Occupied':
                    messages.error(request, 'Cannot manually change status of an occupied bed.')
                else:
                    bed.status = status
                    bed.save(update_fields=['status'])
                    messages.success(request, f'✅ {bed} status updated to {status}.')
            except Bed.DoesNotExist:
                messages.error(request, 'Bed not found.')
            return redirect('ward_setup')

        # --- Toggle Ward Active ---
        elif action == 'toggle_ward':
            ward_id = request.POST.get('ward_id', '').strip()
            try:
                ward = Ward.objects.get(pk=ward_id)
                ward.is_active = not ward.is_active
                ward.save(update_fields=['is_active'])
                state = 'activated' if ward.is_active else 'deactivated'
                messages.success(request, f'✅ Ward <strong>{ward.name}</strong> {state}.')
            except Ward.DoesNotExist:
                messages.error(request, 'Ward not found.')
            return redirect('ward_setup')

        # --- Delete Ward ---
        elif action == 'delete_ward':
            ward_id = request.POST.get('ward_id', '').strip()
            try:
                ward = Ward.objects.get(pk=ward_id)
                if ward.admissions.filter(status='Admitted').exists():
                    messages.error(request, f'Cannot delete <strong>{ward.name}</strong> — it has active admissions.')
                elif ward.beds.filter(status='Occupied').exists():
                    messages.error(request, f'Cannot delete <strong>{ward.name}</strong> — it has occupied beds.')
                else:
                    name = ward.name
                    ward.delete()
                    messages.success(request, f'✅ Ward <strong>{name}</strong> deleted.')
            except Ward.DoesNotExist:
                messages.error(request, 'Ward not found.')
            return redirect('ward_setup')

        # --- Delete Bed ---
        elif action == 'delete_bed':
            bed_id = request.POST.get('bed_id', '').strip()
            try:
                bed = Bed.objects.select_related('ward').get(pk=bed_id)
                if bed.status == 'Occupied':
                    messages.error(request, f'Cannot delete <strong>{bed.bed_number}</strong> — it is currently occupied.')
                else:
                    ward_name = bed.ward.name
                    bed_num   = bed.bed_number
                    bed.delete()
                    messages.success(request, f'✅ Bed <strong>{bed_num}</strong> removed from {ward_name}.')
            except Bed.DoesNotExist:
                messages.error(request, 'Bed not found.')
            return redirect('ward_setup')

    return render(request, 'wards/setup.html', {'wards': wards})


# ══════════════════════════════════════════════════════════════════════════════
# ADMISSIONS LIST
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('wards', 'view')
def admission_list(request):
    search   = request.GET.get('q', '').strip()
    status   = request.GET.get('status', '').strip()
    ward_id  = request.GET.get('ward', '').strip()
    date_from= request.GET.get('from', '').strip()
    date_to  = request.GET.get('to', '').strip()

    qs = Admission.objects.select_related(
        'patient', 'ward', 'bed', 'admitting_doctor'
    ).order_by('-admitted_at')

    if search:
        qs = qs.filter(
            Q(admission_id__icontains=search) |
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(patient__matric_no__icontains=search)
        ).distinct()
    if status:
        qs = qs.filter(status=status)
    if ward_id:
        qs = qs.filter(ward_id=ward_id)
    if date_from:
        qs = qs.filter(admitted_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(admitted_at__date__lte=date_to)

    context = {
        'admissions':       qs,
        'search':           search,
        'filter_status':    status,
        'filter_ward':      ward_id,
        'date_from':        date_from,
        'date_to':          date_to,
        'wards':            Ward.objects.filter(is_active=True),
        'admitted_ct':      Admission.objects.filter(status='Admitted').count(),
        'discharged_today': Admission.objects.filter(
                                status='Discharged',
                                discharged_at__date=timezone.localdate()
                            ).count(),
        'discharged_total': Admission.objects.filter(status='Discharged').count(),
        'total_ct':         Admission.objects.count(),
    }
    return render(request, 'wards/admission_list.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# ADMIT PATIENT
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('wards', 'create')
def admit_patient(request):
    from patients.models import Patient
    from consultations.models import Consultation

    wards    = Ward.objects.filter(is_active=True).prefetch_related('beds')
    patients = Patient.objects.filter(is_active=True).order_by('last_name', 'first_name')

    pre_con    = None
    pre_con_id = request.GET.get('consultation')
    pre_ward_id= request.GET.get('ward', '')
    if pre_con_id:
        try:
            pre_con = Consultation.objects.select_related('patient', 'attending_doctor').get(pk=pre_con_id)
        except Consultation.DoesNotExist:
            pass

    if request.method == 'POST':
        p          = request.POST
        patient_id = p.get('patient', '').strip()
        ward_id    = p.get('ward', '').strip()
        bed_id     = p.get('bed', '').strip()
        con_id     = p.get('consultation', '').strip()
        reason     = p.get('reason', '').strip()
        notes      = p.get('notes', '').strip()
        admitted_at= p.get('admitted_at', '').strip()

        errors = []
        if not patient_id: errors.append('Patient is required.')
        if not ward_id:    errors.append('Ward is required.')
        if not bed_id:     errors.append('Bed is required.')
        if not reason:     errors.append('Reason for admission is required.')

        bed = None
        if bed_id:
            try:
                bed = Bed.objects.select_related('ward').get(pk=bed_id)
                if bed.status != 'Available':
                    errors.append(f'Bed {bed.bed_number} is not available (status: {bed.status}).')
            except Bed.DoesNotExist:
                errors.append('Selected bed not found.')

        # Check patient not already admitted
        if patient_id:
            already = Admission.objects.filter(
                patient_id=patient_id, status='Admitted'
            ).first()
            if already:
                errors.append(
                    f'This patient is already admitted — {already.admission_id} '
                    f'({already.ward.name}, {already.bed.bed_number}).'
                )

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'wards/admit.html', {
                'wards': wards, 'patients': patients, 'pre_con': pre_con,
                'pre_ward_id': pre_ward_id, 'post': p,
            })

        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            messages.error(request, 'Patient not found.')
            return redirect('admit_patient')

        consultation = None
        if con_id:
            try:
                consultation = Consultation.objects.select_related('attending_doctor').get(pk=con_id, patient=patient)
            except Consultation.DoesNotExist:
                pass

        # Admitting doctor: use consultation's attending doctor if available, else logged-in user
        admitting_doctor = request.user
        if consultation and getattr(consultation, 'attending_doctor', None):
            admitting_doctor = consultation.attending_doctor

        # Parse admitted_at
        from django.utils.dateparse import parse_datetime
        adm_dt = parse_datetime(admitted_at) if admitted_at else timezone.now()
        if adm_dt and timezone.is_naive(adm_dt):
            adm_dt = timezone.make_aware(adm_dt)
        if not adm_dt:
            adm_dt = timezone.now()

        # Create admission
        admission = Admission.objects.create(
            patient          = patient,
            ward             = bed.ward,
            bed              = bed,
            consultation     = consultation,
            admitting_doctor = admitting_doctor,
            reason           = reason,
            notes            = notes,
            status           = 'Admitted',
            admitted_at      = adm_dt,
            created_by       = request.user,
        )

        # Mark bed as occupied
        bed.status = 'Occupied'
        bed.save(update_fields=['status'])

        messages.success(
            request,
            f'✅ <strong>{patient.get_full_name()}</strong> admitted — '
            f'{admission.admission_id} · {bed.ward.name}, {bed.bed_number}.'
        )
        return redirect('admission_detail', pk=admission.pk)

    return render(request, 'wards/admit.html', {
        'wards': wards, 'patients': patients, 'pre_con': pre_con,
        'pre_ward_id': pre_ward_id, 'post': {},
    })


# ══════════════════════════════════════════════════════════════════════════════
# ADMISSION DETAIL
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('wards', 'view')
def admission_detail(request, pk):
    admission = get_object_or_404(
        Admission.objects.select_related(
            'patient', 'ward', 'bed', 'admitting_doctor',
            'consultation', 'discharged_by'
        ),
        pk=pk
    )
    transfers = admission.transfers.select_related(
        'from_ward', 'from_bed', 'to_ward', 'to_bed', 'transferred_by'
    ).all()
    available_beds = Bed.objects.filter(status='Available').select_related('ward')

    context = {
        'admission':      admission,
        'transfers':      transfers,
        'available_beds': available_beds,
    }
    return render(request, 'wards/admission_detail.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# TRANSFER PATIENT
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('wards', 'edit')
@require_POST
def transfer_patient(request, pk):
    admission = get_object_or_404(Admission, pk=pk, status='Admitted')
    new_bed_id= request.POST.get('new_bed', '').strip()
    reason    = request.POST.get('reason', '').strip()

    try:
        new_bed = Bed.objects.select_related('ward').get(pk=new_bed_id)
    except Bed.DoesNotExist:
        messages.error(request, 'Selected bed not found.')
        return redirect('admission_detail', pk=pk)

    if new_bed.status != 'Available':
        messages.error(request, f'{new_bed.bed_number} is not available (status: {new_bed.status}).')
        return redirect('admission_detail', pk=pk)

    if new_bed == admission.bed:
        messages.error(request, 'Patient is already in that bed.')
        return redirect('admission_detail', pk=pk)

    # Log transfer
    TransferLog.objects.create(
        admission      = admission,
        from_ward      = admission.ward,
        from_bed       = admission.bed,
        to_ward        = new_bed.ward,
        to_bed         = new_bed,
        reason         = reason,
        transferred_by = request.user,
    )

    # Free old bed
    old_bed        = admission.bed
    old_bed.status = 'Available'
    old_bed.save(update_fields=['status'])

    # Occupy new bed
    new_bed.status = 'Occupied'
    new_bed.save(update_fields=['status'])

    # Update admission
    admission.ward = new_bed.ward
    admission.bed  = new_bed
    admission.save(update_fields=['ward', 'bed'])

    messages.success(
        request,
        f'✅ Patient transferred to <strong>{new_bed.ward.name} — {new_bed.bed_number}</strong>.'
    )
    return redirect('admission_detail', pk=pk)


# ══════════════════════════════════════════════════════════════════════════════
# DISCHARGE PATIENT
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('wards', 'edit')
@require_POST
def discharge_patient(request, pk):
    admission       = get_object_or_404(Admission, pk=pk, status='Admitted')
    discharge_notes = request.POST.get('discharge_notes', '').strip()

    # Free the bed
    bed        = admission.bed
    bed.status = 'Available'
    bed.save(update_fields=['status'])

    # Update admission
    admission.status          = 'Discharged'
    admission.discharged_at   = timezone.now()
    admission.discharge_notes = discharge_notes
    admission.discharged_by   = request.user
    admission.save(update_fields=['status', 'discharged_at', 'discharge_notes', 'discharged_by'])

    messages.success(
        request,
        f'✅ <strong>{admission.patient.get_full_name()}</strong> discharged from '
        f'{admission.ward.name} — {admission.bed.bed_number}.'
    )
    return redirect('admission_list')


# ══════════════════════════════════════════════════════════════════════════════
# AJAX — Get available beds for a ward
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('wards', 'view')
def available_beds_ajax(request):
    ward_id = request.GET.get('ward', '').strip()
    if not ward_id:
        return JsonResponse({'beds': []})
    beds = Bed.objects.filter(ward_id=ward_id, status='Available').order_by('bed_number')
    data = [{'id': b.pk, 'label': b.bed_number} for b in beds]
    return JsonResponse({'beds': data})