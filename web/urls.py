from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('student', views.student_login, name='student_login'),
    path('student/session', views.student_session, name='student_session'),
    path('student/session/attendance', views.student_session_attendance, name='student_session_attendance'),
    path('student/session/<str:session_id>', views.student_session_id, name='student_session_id'),
    path('student/session/attendance/compelted', views.student_session_attendance_complete, name='student_session_attendance_completed'),
    path('event/waiver/list', views.event_waiver_list, name='event_waiver_list'),
    path('event/<int:event_id>/waiver', views.event_waiver, name='event_waiver'),
    path('event/waiver/success', views.event_waiver_success, name='event_waiver_success'),
    path('kiosk', views.kiosk_home, name='kiosk_home'),
    path('kiosk/activate', views.kiosk_activate, name='kiosk_activate'),
    path('kiosk/deactivate', views.kiosk_deactivate, name='kiosk_deactivate'),
    path('kiosk/register', views.kiosk_register, name='kiosk_register'),
    path('kiosk/register/success', views.kiosk_register_success, name='kiosk_register_success'),
    path('kiosk/attendance', views.kiosk_attendance, name='kiosk_attendance'),
    path('kiosk/attendance/session/<int:session_id>', views.kiosk_attendance_session, name='kiosk_attendance_session'),
    path('kiosk/attendance/completed', views.kiosk_attendance_completed, name='kiosk_attendance_completed'),
    path('kiosk/attendees', views.kiosk_attendees, name='kiosk_attendees'),
    path('kiosk/attendees/session/<int:session_id>', views.kiosk_attendees_session, name='kiosk_attendees_session'),
]