from django.db import migrations

DEFAULT_TESTS = [
    {
        'name': 'Malaria Parasite (MP)',
        'short_code': 'MP',
        'description': 'Thick and thin blood film for malaria parasite detection',
        'reference_range': 'Not seen',
        'unit': '',
    },
    {
        'name': 'Urinalysis',
        'short_code': 'URS',
        'description': 'Physical, chemical and microscopic examination of urine',
        'reference_range': 'See individual parameters',
        'unit': '',
    },
    {
        'name': 'Blood Glucose (RBS)',
        'short_code': 'RBS',
        'description': 'Random Blood Sugar',
        'reference_range': '3.9 – 7.8 mmol/L',
        'unit': 'mmol/L',
    },
    {
        'name': 'Blood Glucose (FBS)',
        'short_code': 'FBS',
        'description': 'Fasting Blood Sugar',
        'reference_range': '3.9 – 5.6 mmol/L',
        'unit': 'mmol/L',
    },
    {
        'name': 'Stool Analysis',
        'short_code': 'S/A',
        'description': 'Stool microscopy and culture',
        'reference_range': 'No ova/cysts/parasites seen',
        'unit': '',
    },
    {
        'name': 'Widal Test',
        'short_code': 'WDL',
        'description': 'Serological test for typhoid fever (Salmonella typhi)',
        'reference_range': 'TO < 1:80, TH < 1:80',
        'unit': 'titre',
    },
    {
        'name': 'Genotype',
        'short_code': 'GEN',
        'description': 'Haemoglobin genotype',
        'reference_range': 'AA (Normal)',
        'unit': '',
    },
    {
        'name': 'Blood Group & Rhesus',
        'short_code': 'BG',
        'description': 'ABO blood group and Rhesus factor',
        'reference_range': 'A/B/AB/O, Rh+/-',
        'unit': '',
    },
]


def create_default_tests(apps, schema_editor):
    LabTest = apps.get_model('laboratory', 'LabTest')
    for t in DEFAULT_TESTS:
        LabTest.objects.get_or_create(
            name=t['name'],
            defaults={
                'short_code':      t['short_code'],
                'description':     t['description'],
                'reference_range': t['reference_range'],
                'unit':            t['unit'],
                'is_active':       True,
            }
        )


def reverse_default_tests(apps, schema_editor):
    LabTest = apps.get_model('laboratory', 'LabTest')
    LabTest.objects.filter(name__in=[t['name'] for t in DEFAULT_TESTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('laboratory', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_tests, reverse_default_tests),
    ]