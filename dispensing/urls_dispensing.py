from django.urls import path
from dispensing import views_dispensing

urlpatterns = [
    path('dispensing/',                         views_dispensing.dispensing_queue,  name='dispensing_queue'),
    path('dispensing/<int:pk>/',                views_dispensing.dispense_detail,   name='dispense_detail'),
    path('dispensing/<int:pk>/in-progress/',    views_dispensing.mark_in_progress,  name='mark_in_progress'),
    path('dispensing/<int:pk>/confirm/',        views_dispensing.confirm_dispense,  name='confirm_dispense'),
    path('dispensing/<int:pk>/slip/',           views_dispensing.dispense_slip,     name='dispense_slip'),
    path('dispensing/history/',                 views_dispensing.dispensing_history, name='dispensing_history'),
]