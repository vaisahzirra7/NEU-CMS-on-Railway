from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.permissions import permission_required

from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_POST

from prescriptions.models import Prescription, PrescriptionItem
from inventory.models import Drug, StockBatch, StockTransaction


def get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')


# ══════════════════════════════════════════════════════════════════════════════
# PRESCRIPTION LIST
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('prescriptions', 'view')
def prescription_list(request):
    qs = Prescription.objects.select_related('patient', 'prescribed_by').order_by('-created_at')

    search       = request.GET.get('q', '').strip()
    status       = request.GET.get('status', '').strip()
    date         = request.GET.get('date', '').strip()

    if search:
        qs = qs.filter(
            Q(prescription_id__icontains=search) |
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(patient__matric_no__icontains=search) |
            Q(items__drug_name__icontains=search)
        ).distinct()
    if status:
        qs = qs.filter(status=status)
    if date:
        qs = qs.filter(created_at__date=date)

    today = timezone.localdate()
    context = {
        'prescriptions':   qs,
        'search':          search,
        'filter_status':   status,
        'filter_date':     date,
        'total_today':     Prescription.objects.filter(created_at__date=today).count(),
        'pending_ct':      Prescription.objects.filter(status='Pending').count(),
        'in_progress_ct':  Prescription.objects.filter(status='In Progress').count(),
        'dispensed_today': Prescription.objects.filter(status='Dispensed', dispensed_at__date=today).count(),
    }
    return render(request, 'prescriptions/list.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# CREATE PRESCRIPTION
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('prescriptions', 'create')
def prescription_create(request):
    from patients.models import Patient
    from consultations.models import Consultation

    patients   = Patient.objects.filter(is_active=True).order_by('last_name', 'first_name')
    pre_con    = None
    pre_con_id = request.GET.get('consultation')

    if pre_con_id:
        try:
            pre_con = Consultation.objects.select_related('patient').get(pk=pre_con_id)
        except Consultation.DoesNotExist:
            pass

    if request.method == 'POST':
        p          = request.POST
        patient_id = p.get('patient', '').strip()
        con_id     = p.get('consultation', '').strip()
        notes      = p.get('notes', '').strip()

        # Parse drug lists from POST
        drug_ids     = p.getlist('drug_id')
        drug_names   = p.getlist('drug_name')
        dosages      = p.getlist('dosage')
        frequencies  = p.getlist('frequency')
        durations    = p.getlist('duration')
        routes       = p.getlist('route')
        quantities   = p.getlist('quantity')
        instructions = p.getlist('instructions')

        errors = []
        if not patient_id:
            errors.append('Patient is required.')
        if not any(n.strip() for n in drug_names):
            errors.append('At least one drug must be added to the prescription.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'prescriptions/create.html', {
                'patients':    patients,
                'pre_con':     pre_con,
                'routes':      PrescriptionItem.ROUTE_CHOICES,
                'frequencies': PrescriptionItem.FREQUENCY_CHOICES,
                'post':        p,
            })

        # FIX: use clean import instead of __import__ hack
        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            messages.error(request, 'Selected patient not found.')
            return render(request, 'prescriptions/create.html', {
                'patients': patients, 'pre_con': pre_con,
                'routes': PrescriptionItem.ROUTE_CHOICES,
                'frequencies': PrescriptionItem.FREQUENCY_CHOICES,
                'post': p,
            })

        consultation = None
        if con_id:
            try:
                consultation = Consultation.objects.get(pk=con_id, patient=patient)
            except Consultation.DoesNotExist:
                pass  # silently ignore invalid consultation ID

        rx = Prescription.objects.create(
            patient       = patient,
            consultation  = consultation,
            prescribed_by = request.user,
            notes         = notes,
            status        = 'Pending',
            created_by    = request.user,
        )

        # Create prescription items
        for i, drug_name in enumerate(drug_names):
            name = drug_name.strip()
            if not name:
                continue  # skip empty rows

            # Try to link to inventory drug
            drug_obj = None
            drug_id  = drug_ids[i] if i < len(drug_ids) else ''
            if drug_id:
                try:
                    drug_obj = Drug.objects.get(pk=int(drug_id))
                    # If name was not typed, fall back to drug's name
                    if not name:
                        name = drug_obj.name
                except (Drug.DoesNotExist, ValueError, TypeError):
                    drug_obj = None

            # Safe quantity parse
            qty = 1
            try:
                raw_qty = quantities[i] if i < len(quantities) else ''
                qty = max(1, int(raw_qty)) if raw_qty else 1
            except (ValueError, TypeError):
                qty = 1

            PrescriptionItem.objects.create(
                prescription = rx,
                drug         = drug_obj,
                drug_name    = name,
                dosage       = dosages[i].strip()      if i < len(dosages)      else '',
                frequency    = frequencies[i].strip()  if i < len(frequencies)  else '',
                duration     = durations[i].strip()    if i < len(durations)    else '',
                route        = routes[i]               if i < len(routes)       else 'Oral',
                quantity     = qty,
                instructions = instructions[i].strip() if i < len(instructions) else '',
            )

        # Flag the linked consultation as having a prescription
        if consultation:
            consultation.has_prescription = True
            consultation.save(update_fields=['has_prescription'])

        messages.success(request, f'✅ Prescription <strong>{rx.prescription_id}</strong> created successfully.')
        return redirect('prescription_detail', pk=rx.pk)

    return render(request, 'prescriptions/create.html', {
        'patients':    patients,
        'pre_con':     pre_con,
        'routes':      PrescriptionItem.ROUTE_CHOICES,
        'frequencies': PrescriptionItem.FREQUENCY_CHOICES,
        'post':        {},
    })


# ══════════════════════════════════════════════════════════════════════════════
# PRESCRIPTION DETAIL
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('prescriptions', 'view')
def prescription_detail(request, pk):
    rx    = get_object_or_404(
                Prescription.objects.select_related(
                    'patient', 'prescribed_by', 'dispensed_by', 'consultation'
                ),
                pk=pk
            )
    items = rx.items.select_related('drug').all()
    return render(request, 'prescriptions/detail.html', {'rx': rx, 'items': items})


# ══════════════════════════════════════════════════════════════════════════════
# UPDATE STATUS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('prescriptions', 'edit')
@require_POST
def prescription_update_status(request, pk):
    rx         = get_object_or_404(Prescription, pk=pk)
    new_status = request.POST.get('status', '').strip()

    valid_transitions = {
        'Pending':     ['In Progress', 'Cancelled'],
        'In Progress': ['Dispensed',   'Cancelled'],
    }

    allowed = valid_transitions.get(rx.status, [])
    if new_status not in allowed:
        messages.error(request, f'Cannot change status from {rx.status} to {new_status}.')
        return redirect('prescription_detail', pk=pk)

    rx.status = new_status

    if new_status == 'Dispensed':
        rx.dispensed_by = request.user
        rx.dispensed_at = timezone.now()

        # Deduct stock for every item linked to inventory
        for item in rx.items.select_related('drug').all():
            if item.drug and item.quantity > 0:
                _deduct_stock(item.drug, item.quantity, rx.prescription_id, request.user)
                item.dispensed_qty = item.quantity
                item.save(update_fields=['dispensed_qty'])

    rx.save()
    messages.success(request, f'✅ Prescription status updated to <strong>{new_status}</strong>.')
    return redirect('prescription_detail', pk=pk)


def _deduct_stock(drug, qty_needed, reference, user):
    """Deduct stock using FEFO — First Expiry, First Out."""
    batches = StockBatch.objects.filter(
        drug=drug,
        is_active=True,
        quantity_remaining__gt=0,
    ).order_by('expiry_date', 'created_at')  # oldest expiry first

    remaining = qty_needed
    for batch in batches:
        if remaining <= 0:
            break
        deduct = min(batch.quantity_remaining, remaining)
        batch.quantity_remaining -= deduct
        if batch.quantity_remaining == 0:
            batch.is_active = False
        batch.save(update_fields=['quantity_remaining', 'is_active'])

        StockTransaction.objects.create(
            drug         = drug,
            batch        = batch,
            type         = 'OUT',
            quantity     = -deduct,
            reference    = reference,
            notes        = f'Dispensed via prescription {reference}',
            performed_by = user,
        )
        remaining -= deduct
    # Note: if remaining > 0 after all batches, drug was out of stock —
    # prescription is still marked dispensed but stock went to 0


# ══════════════════════════════════════════════════════════════════════════════
# AJAX — Patient consultations (for linking dropdown)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('prescriptions', 'view')
def patient_consultations_ajax(request):
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
            'id':     c.pk,
            'label':  f'{c.consultation_id} — {c.chief_complaint[:40]} ({c.created_at:%d %b %Y})',
            'doctor': c.attending_doctor.get_full_name() if getattr(c, 'attending_doctor', None) else '',
        }
        for c in cons
    ]
    return JsonResponse({'consultations': data})