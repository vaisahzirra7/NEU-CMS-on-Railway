from django.urls import path
from reports import views_reports as v

urlpatterns = [
    path('reports/',                    v.reports_dashboard, name='reports_dashboard'),
    path('reports/export/<str:report_type>/', v.export_csv, name='reports_export_csv'),
]