from django import forms
from django.contrib.admin.widgets import AdminTimeWidget

from .models import Session


class AdminSessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['time_from', 'time_to']
        # widgets = {
        #     'time_from': AdminTimeWidget,
        #     'time_to': AdminTimeWidget,
        # }

    def __init__(self, *args, **kwargs):
        super(AdminSessionForm, self).__init__(*args, **kwargs)
        #self.fields['title'].widget.attrs.pop('maxlength', None)
