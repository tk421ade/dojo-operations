from datetime import date

from django import forms
from django.core.validators import RegexValidator


class EmailForm(forms.Form):
    email = forms.EmailField(label='Email Address')


class KioskPinForm(forms.Form):
    pin = forms.CharField(
        max_length=6,
        label='PIN',
        widget=forms.PasswordInput(attrs={'inputmode': 'numeric', 'pattern': '[0-9]*', 'autofocus': True}),
    )
    website = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={
            'style': 'position:absolute;left:-9999px;top:-9999px;',
            'tabindex': '-1',
            'autocomplete': 'off',
        })
    )


QUESTIONNAIRE_QUESTIONS = [
    ('q1', 'Has your doctor ever said you have a heart condition or vascular disease?'),
    ('q2', 'Do you ever experience chest pains?'),
    ('q3', 'Have you experienced any chest pain recently?'),
    ('q4', 'Do you ever feel faint, dizzy, lose balance or lose consciousness?'),
    ('q5', 'Has your doctor ever said you have high blood pressure (140/90)?'),
    ('q6', 'Are you taking any medication for blood pressure or a heart condition?'),
    ('q7', 'Are you a male over 35 or, a female over 45 and not accustomed to exercise?'),
    ('q8', 'Do you have a bone or joint problem that could be made worse by a change in your physical activity?'),
    ('q9', 'Do you suffer from asthma?'),
    ('q10', 'Do you suffer from any other respiratory problems?'),
    ('q11', 'Do you suffer from diabetes?'),
    ('q12', 'Do you suffer from epilepsy?'),
    ('q13', 'Do you currently suffer from any illness not mentioned here?'),
    ('q14', 'Do you know of any other reason why you should not participate in physical activity?'),
]

YES_NO_CHOICES = [('yes', 'Yes'), ('no', 'No')]

GRADE_CHOICES = [
    ('', 'None'),
    ('10kyu', '10th Kyu'),
    ('9kyu', '9th Kyu'),
    ('8kyu', '8th Kyu'),
    ('7kyu', '7th Kyu'),
    ('6kyu', '6th Kyu'),
    ('5kyu', '5th Kyu'),
    ('4kyu', '4th Kyu'),
    ('3kyu', '3rd Kyu'),
    ('2kyu', '2nd Kyu'),
    ('1kyu', '1st Kyu'),
    ('black', 'Black Belt (Shodan+)'),
]

PHONE_VALIDATOR = RegexValidator(
    r'^[\d\s\+\-\(\)]{6,20}$',
    'Enter a valid phone number (digits, spaces, +, -, brackets).')

DATE_WIDGET = forms.DateInput(
    attrs={'placeholder': 'dd/mm/yyyy', 'autocomplete': 'off'},
    format='%d/%m/%Y',
)
DATE_INPUT_FORMATS = ['%d/%m/%Y', '%Y-%m-%d']
PHONE_WIDGET = forms.TextInput(attrs={'type': 'tel'})


class EventWaiverForm(forms.Form):
    # Honeypot field — hidden from real users
    email2 = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={
            'style': 'position:absolute;left:-9999px;top:-9999px;',
            'tabindex': '-1',
            'autocomplete': 'off',
        })
    )

    # Personal information
    first_name = forms.CharField(max_length=200, label='First name')
    last_name = forms.CharField(max_length=200, label='Last name')
    address = forms.CharField(max_length=255, label='Address')
    suburb = forms.CharField(max_length=200, required=False, label='Suburb')
    state = forms.CharField(max_length=100, required=False, label='State')
    post_code = forms.CharField(max_length=20, required=False, label='Post code')
    phone = forms.CharField(max_length=50, label='Phone number', validators=[PHONE_VALIDATOR], widget=PHONE_WIDGET)
    email = forms.EmailField(max_length=200, label='Email')
    date_of_birth = forms.DateField(
        required=True, label='Date of birth', widget=DATE_WIDGET,
        input_formats=DATE_INPUT_FORMATS)
    current_grade = forms.ChoiceField(choices=GRADE_CHOICES, required=False, label='Current grade')

    # Emergency contact
    emergency_contact_name = forms.CharField(max_length=200, label='Emergency contact name')
    emergency_contact_relationship = forms.CharField(max_length=100, required=False, label='Emergency contact relationship')
    emergency_contact_phone = forms.CharField(max_length=50, label='Emergency contact phone',
                                               validators=[PHONE_VALIDATOR], widget=PHONE_WIDGET)

    # Terms acceptance
    terms_accepted = forms.BooleanField(
        required=True, label='I have read and agree to the terms and conditions above.')

    # Physical readiness questionnaire (14 yes/no)
    q1 = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect, label='1. Has your doctor ever said you have a heart condition or vascular disease?')
    q2 = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect, label='2. Do you ever experience chest pains?')
    q3 = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect, label='3. Have you experienced any chest pain recently?')
    q4 = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect, label='4. Do you ever feel faint, dizzy, lose balance or lose consciousness?')
    q5 = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect, label='5. Has your doctor ever said you have high blood pressure (140/90)?')
    q6 = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect, label='6. Are you taking any medication for blood pressure or a heart condition?')
    q7 = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect, label='7. Are you a male over 35 or, a female over 45 and not accustomed to exercise?')
    q8 = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect, label='8. Do you have a bone or joint problem that could be made worse by a change in your physical activity?')
    q9 = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect, label='9. Do you suffer from asthma?')
    q10 = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect, label='10. Do you suffer from any other respiratory problems?')
    q11 = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect, label='11. Do you suffer from diabetes?')
    q12 = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect, label='12. Do you suffer from epilepsy?')
    q13 = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect, label='13. Do you currently suffer from any illness not mentioned here?')
    q14 = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect, label='14. Do you know of any other reason why you should not participate in physical activity?')

    # Questionnaire specifications
    q13_specify = forms.CharField(required=False, label='Please specify (Q13)',
                                   widget=forms.Textarea(attrs={'rows': 2}))
    q14_specify = forms.CharField(required=False, label='Please specify (Q14)',
                                   widget=forms.Textarea(attrs={'rows': 2}))

    # Allergies
    allergies = forms.CharField(required=False, label='Do you suffer from any allergies? Please specify:',
                                 widget=forms.Textarea(attrs={'rows': 2}))

    # Signature data (base64 PNG from canvas — populated by JS)
    applicant_signature_data = forms.CharField(
        widget=forms.HiddenInput(), required=True,
        error_messages={'required': 'Applicant signature is required.'})
    applicant_name = forms.CharField(max_length=200, label='Name (applicant)')
    applicant_date = forms.DateField(label='Date', initial=date.today, widget=DATE_WIDGET,
                                      input_formats=DATE_INPUT_FORMATS)

    guardian_signature_data = forms.CharField(
        widget=forms.HiddenInput(), required=False)
    guardian_name = forms.CharField(max_length=200, required=False, label='Name (parent or legal guardian)')
    guardian_date = forms.DateField(required=False, label='Date', widget=DATE_WIDGET,
                                     input_formats=DATE_INPUT_FORMATS)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('q13') == 'yes' and not cleaned_data.get('q13_specify', '').strip():
            self.add_error('q13_specify', 'Please specify the illness (Q13).')
        if cleaned_data.get('q14') == 'yes' and not cleaned_data.get('q14_specify', '').strip():
            self.add_error('q14_specify', 'Please specify the reason (Q14).')

        dob = cleaned_data.get('date_of_birth')
        if dob:
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 18:
                if not cleaned_data.get('guardian_signature_data'):
                    self.add_error('guardian_signature_data',
                                   'Guardian signature is required for participants under 18.')
                if not cleaned_data.get('guardian_name', '').strip():
                    self.add_error('guardian_name',
                                   'Guardian name is required for participants under 18.')
                if not cleaned_data.get('guardian_date'):
                    self.add_error('guardian_date',
                                   'Guardian date is required for participants under 18.')

        return cleaned_data