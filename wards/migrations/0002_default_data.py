from django.db import migrations


DEFAULT_WARDS = [
    {
        'name': 'Male Ward',
        'description': 'General male patient ward',
        'beds': [f'Bed {i}' for i in range(1, 11)],  # 10 beds
    },
    {
        'name': 'Female Ward',
        'description': 'General female patient ward',
        'beds': [f'Bed {i}' for i in range(1, 11)],  # 10 beds
    },
    {
        'name': 'Emergency Ward',
        'description': 'Emergency and critical care ward',
        'beds': [f'Bed {i}' for i in range(1, 7)],   # 6 beds
    },
]


def create_default_wards(apps, schema_editor):
    Ward = apps.get_model('wards', 'Ward')
    Bed  = apps.get_model('wards', 'Bed')
    for wd in DEFAULT_WARDS:
        ward, created = Ward.objects.get_or_create(
            name=wd['name'],
            defaults={'description': wd['description'], 'is_active': True}
        )
        if created:
            for bed_num in wd['beds']:
                Bed.objects.get_or_create(
                    ward=ward, bed_number=bed_num,
                    defaults={'status': 'Available'}
                )


def reverse_default_wards(apps, schema_editor):
    Ward = apps.get_model('wards', 'Ward')
    Ward.objects.filter(name__in=[w['name'] for w in DEFAULT_WARDS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('wards', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_wards, reverse_default_wards),
    ]