from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.permissions import permission_required

from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_POST

from laboratory.models import LabTest, LabRequest, LabResult


# ══════════════════════════════════════════════════════════════════════════════
# LAB REQUEST LIST
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('laboratory', 'view')
def lab_list(request):
    search   = request.GET.get('q', '').strip()
    status   = request.GET.get('status', '').strip()
    priority = request.GET.get('priority', '').strip()
    date_from= request.GET.get('from', '').strip()
    date_to  = request.GET.get('to', '').strip()

    qs = LabRequest.objects.select_related(
        'patient', 'requested_by', 'processed_by'
    ).prefetch_related('results').order_by('-created_at')

    if search:
        qs = qs.filter(
            Q(lab_id__icontains=search) |
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(patient__matric_no__icontains=search)
        ).distinct()
    if status:
        qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    today = timezone.localdate()
    context = {
        'requests':       qs,
        'search':         search,
        'filter_status':  status,
        'filter_priority':priority,
        'date_from':      date_from,
        'date_to':        date_to,
        'pending_ct':     LabRequest.objects.filter(status='Pending').count(),
        'in_progress_ct': LabRequest.objects.filter(status='In Progress').count(),
        'completed_today':LabRequest.objects.filter(
                              status='Completed', processed_at__date=today
                          ).count(),
        'total_today':    LabRequest.objects.filter(created_at__date=today).count(),
    }
    return render(request, 'laboratory/list.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# CREATE LAB REQUEST
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('laboratory', 'create')
def lab_create(request):
    from patients.models import Patient
    from consultations.models import Consultation

    tests    = LabTest.objects.filter(is_active=True).order_by('name')
    patients = Patient.objects.filter(is_active=True).order_by('last_name', 'first_name')

    pre_con    = None
    pre_con_id = request.GET.get('consultation')
    if pre_con_id:
        try:
            pre_con = Consultation.objects.select_related('patient', 'attending_doctor').get(pk=pre_con_id)
        except Consultation.DoesNotExist:
            pass

    if request.method == 'POST':
        p          = request.POST
        patient_id = p.get('patient', '').strip()
        con_id     = p.get('consultation', '').strip()
        priority   = p.get('priority', 'Routine').strip()
        notes      = p.get('clinical_notes', '').strip()
        test_ids   = p.getlist('tests')

        errors = []
        if not patient_id: errors.append('Patient is required.')
        if not test_ids:   errors.append('Select at least one test.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'laboratory/create.html', {
                'tests': tests, 'patients': patients, 'pre_con': pre_con, 'post': p,
            })

        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            messages.error(request, 'Patient not found.')
            return redirect('lab_create')

        consultation = None
        if con_id:
            try:
                consultation = Consultation.objects.get(pk=con_id, patient=patient)
            except Consultation.DoesNotExist:
                pass

        lab_req = LabRequest.objects.create(
            patient        = patient,
            consultation   = consultation,
            requested_by   = request.user,
            status         = 'Pending',
            priority       = priority,
            clinical_notes = notes,
            created_by     = request.user,
        )

        # Create one LabResult row per selected test (empty result)
        for tid in test_ids:
            try:
                test = LabTest.objects.get(pk=tid, is_active=True)
                LabResult.objects.create(
                    request         = lab_req,
                    test            = test,
                    reference_range = test.reference_range,
                    unit            = test.unit,
                )
            except LabTest.DoesNotExist:
                pass

        messages.success(
            request,
            f'✅ Lab request <strong>{lab_req.lab_id}</strong> created for {patient.get_full_name()}.'
        )
        return redirect('lab_detail', pk=lab_req.pk)

    return render(request, 'laboratory/create.html', {
        'tests': tests, 'patients': patients, 'pre_con': pre_con, 'post': {},
    })


# ══════════════════════════════════════════════════════════════════════════════
# LAB REQUEST DETAIL
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('laboratory', 'view')
def lab_detail(request, pk):
    lab_req = get_object_or_404(
        LabRequest.objects.select_related(
            'patient', 'requested_by', 'processed_by', 'consultation'
        ),
        pk=pk
    )
    results = lab_req.results.select_related('test', 'entered_by').all()
    context = {'lab_req': lab_req, 'results': results}
    return render(request, 'laboratory/detail.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# ENTER / UPDATE RESULTS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('laboratory', 'edit')
@require_POST
def lab_enter_results(request, pk):
    lab_req = get_object_or_404(LabRequest, pk=pk)

    if lab_req.status == 'Cancelled':
        messages.error(request, 'Cannot enter results for a cancelled request.')
        return redirect('lab_detail', pk=pk)

    now = timezone.now()
    any_entered = False

    for result in lab_req.results.select_related('test').all():
        val_key    = f'result_{result.pk}'
        ref_key    = f'ref_{result.pk}'
        interp_key = f'interp_{result.pk}'
        rem_key    = f'remarks_{result.pk}'

        val        = request.POST.get(val_key, '').strip()
        ref        = request.POST.get(ref_key, '').strip()
        interp     = request.POST.get(interp_key, '').strip()
        remarks    = request.POST.get(rem_key, '').strip()

        if val:
            result.result_value   = val
            result.reference_range= ref
            result.interpretation = interp
            result.remarks        = remarks
            result.entered_by     = request.user
            result.entered_at     = now
            result.save()
            any_entered = True

    if any_entered:
        # Auto-advance status
        if lab_req.status == 'Pending':
            lab_req.status = 'In Progress'

        # If all results filled → Completed
        all_filled = all(r.has_result for r in lab_req.results.all())
        if all_filled:
            lab_req.status       = 'Completed'
            lab_req.processed_by = request.user
            lab_req.processed_at = now

        lab_req.save(update_fields=['status', 'processed_by', 'processed_at'])
        messages.success(request, '✅ Results saved successfully.')
    else:
        messages.warning(request, 'No results were entered.')

    return redirect('lab_detail', pk=pk)


# ══════════════════════════════════════════════════════════════════════════════
# UPDATE STATUS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('laboratory', 'edit')
@require_POST
def lab_update_status(request, pk):
    lab_req    = get_object_or_404(LabRequest, pk=pk)
    new_status = request.POST.get('status', '').strip()

    valid = {
        'Pending':     ['In Progress', 'Cancelled'],
        'In Progress': ['Completed', 'Cancelled'],
    }
    allowed = valid.get(lab_req.status, [])

    if new_status not in allowed:
        messages.error(request, f'Cannot change status from {lab_req.status} to {new_status}.')
        return redirect('lab_detail', pk=pk)

    lab_req.status = new_status
    if new_status in ['Completed', 'In Progress']:
        lab_req.processed_by = request.user
        lab_req.processed_at = timezone.now()
        lab_req.save(update_fields=['status', 'processed_by', 'processed_at'])
    else:
        lab_req.save(update_fields=['status'])

    messages.success(request, f'✅ Status updated to <strong>{new_status}</strong>.')
    return redirect('lab_detail', pk=pk)


# ══════════════════════════════════════════════════════════════════════════════
# LAB REPORT — printable
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('laboratory', 'export')
def lab_report(request, pk):
    lab_req = get_object_or_404(
        LabRequest.objects.select_related(
            'patient', 'requested_by', 'processed_by', 'consultation'
        ),
        pk=pk
    )
    results = lab_req.results.select_related('test', 'entered_by').all()
    return render(request, 'laboratory/report.html', {'lab_req': lab_req, 'results': results})


# ══════════════════════════════════════════════════════════════════════════════
# TEST CATALOG MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('laboratory', 'edit')
def lab_catalog(request):
    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'create':
            name  = request.POST.get('name', '').strip()
            code  = request.POST.get('short_code', '').strip()
            desc  = request.POST.get('description', '').strip()
            ref   = request.POST.get('reference_range', '').strip()
            unit  = request.POST.get('unit', '').strip()
            if not name:
                messages.error(request, 'Test name is required.')
            elif LabTest.objects.filter(name__iexact=name).exists():
                messages.error(request, f'A test named "{name}" already exists.')
            else:
                LabTest.objects.create(
                    name=name, short_code=code, description=desc,
                    reference_range=ref, unit=unit
                )
                messages.success(request, f'✅ Test <strong>{name}</strong> added to catalog.')

        elif action == 'toggle':
            tid = request.POST.get('test_id', '').strip()
            try:
                t = LabTest.objects.get(pk=tid)
                t.is_active = not t.is_active
                t.save(update_fields=['is_active'])
                state = 'activated' if t.is_active else 'deactivated'
                messages.success(request, f'✅ <strong>{t.name}</strong> {state}.')
            except LabTest.DoesNotExist:
                messages.error(request, 'Test not found.')

        elif action == 'delete':
            tid = request.POST.get('test_id', '').strip()
            try:
                t = LabTest.objects.get(pk=tid)
                if t.results.exists():
                    messages.error(request, f'Cannot delete <strong>{t.name}</strong> — it has existing results.')
                else:
                    name = t.name
                    t.delete()
                    messages.success(request, f'✅ Test <strong>{name}</strong> deleted.')
            except LabTest.DoesNotExist:
                messages.error(request, 'Test not found.')

        return redirect('lab_catalog')

    tests = LabTest.objects.all()
    return render(request, 'laboratory/catalog.html', {'tests': tests})


# ══════════════════════════════════════════════════════════════════════════════
# AJAX — patient consultations (reuse prescriptions ajax)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('laboratory', 'view')
def lab_patient_consultations_ajax(request):
    patient_id = request.GET.get('patient', '').strip()
    if not patient_id:
        return JsonResponse({'consultations': []})
    from consultations.models import Consultation
    cons = Consultation.objects.select_related('attending_doctor').filter(
        patient_id=patient_id,
        status__in=['Open', 'In Progress'],
    ).order_by('-created_at')[:10]
    data = [
        {
            'id':    c.pk,
            'label': f'{c.consultation_id} — {c.chief_complaint[:40]} ({c.created_at:%d %b %Y})',
        }
        for c in cons
    ]
    return JsonResponse({'consultations': data})