from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('student', views.student_login, name='student_login'),
    path('student/session', views.student_session, name='student_session'),
    path('student/session/attendance', views.student_session_attendance, name='student_session_attendance'),
    path('student/session/attendance/compelted', views.student_session_attendance_complete, name='student_session_attendance_completed'),
]