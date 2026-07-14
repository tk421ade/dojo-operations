from datetime import date

from django import forms
from django.core.validators import RegexValidator

from shodan.models import SessionFeedbackQuestion


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


# ---------------------------------------------------------------------------
# Session Feedback
# ---------------------------------------------------------------------------

DEFAULT_FEEDBACK_QUESTIONS = [
    {
        'question_text': 'Overall, how would you rate this session?',
        'question_type': 'rating',
        'choices': [],
        'order': 1,
        'required': True,
    },
    {
        'question_text': 'How much did you enjoy the session?',
        'question_type': 'rating',
        'choices': [],
        'order': 2,
        'required': True,
    },
    {
        'question_text': 'How well did the session help you learn something new?',
        'question_type': 'rating',
        'choices': [],
        'order': 3,
        'required': True,
    },
    {
        'question_text': 'Did this session inspire you or your student on their karate journey '
                         '(e.g., grading, tournaments, resuming training)?',
        'question_type': 'rating',
        'choices': [],
        'order': 4,
        'required': True,
    },
    {
        'question_text': 'What was one drill or topic covered that was of most benefit?',
        'question_type': 'text',
        'choices': [],
        'order': 5,
        'required': False,
    },
    {
        'question_text': 'What would you have liked more time on?',
        'question_type': 'text',
        'choices': [],
        'order': 6,
        'required': False,
    },
    {
        'question_text': 'What was not covered but you would have liked?',
        'question_type': 'text',
        'choices': [],
        'order': 7,
        'required': False,
    },
    {
        'question_text': 'Would you attend another session like this?',
        'question_type': 'yes_no',
        'choices': [],
        'order': 8,
        'required': True,
    },
    {
        'question_text': 'Why not? (cost, travel time, etc)',
        'question_type': 'text',
        'choices': [],
        'order': 9,
        'required': False,
        'conditional_parent_text': 'Would you attend another session like this?',
        'conditional_answer': 'no',
    },
    {
        'question_text': 'If yes, what would be the ideal duration?',
        'question_type': 'choice',
        'choices': ['2 hours', '3 hours', '4 hours', 'Half-day', 'Full day', 'Full weekend'],
        'order': 9,
        'required': False,
        'conditional_parent_text': 'Would you attend another session like this?',
        'conditional_answer': 'yes',
    },
    {
        'question_text': 'Any other comments or feedback?',
        'question_type': 'text',
        'choices': [],
        'order': 10,
        'required': False,
    },
]

RATING_CHOICES = [
    ('1', '1 — Poor'),
    ('2', '2 — Fair'),
    ('3', '3 — Good'),
    ('4', '4 — Very Good'),
    ('5', '5 — Excellent'),
]


def sync_default_questions(feedback_link):
    """Ensure all default questions exist on a link (adding missing ones) and resolve
    conditional parent references. Returns the number of questions created."""
    by_text = {q.question_text: q for q in feedback_link.questions.all()}
    created = 0
    for q_def in DEFAULT_FEEDBACK_QUESTIONS:
        text = q_def['question_text']
        if text not in by_text:
            obj = SessionFeedbackQuestion.objects.create(
                feedback_link=feedback_link,
                question_text=text,
                question_type=q_def['question_type'],
                choices=q_def['choices'],
                order=q_def['order'],
                required=q_def['required'],
            )
            by_text[text] = obj
            created += 1
    for q_def in DEFAULT_FEEDBACK_QUESTIONS:
        parent_text = q_def.get('conditional_parent_text')
        if parent_text and parent_text in by_text:
            child = by_text.get(q_def['question_text'])
            if child:
                child.conditional_parent = by_text[parent_text]
                child.conditional_answer = q_def.get('conditional_answer', '')
                child.save(update_fields=['conditional_parent', 'conditional_answer'])
    return created


def build_feedback_form(questions):
    """Build a dynamic Django Form from SessionFeedbackQuestion instances."""
    class _FeedbackForm(forms.Form):
        email2 = forms.CharField(
            required=False,
            label='',
            widget=forms.TextInput(attrs={
                'style': 'position:absolute;left:-9999px;top:-9999px;',
                'tabindex': '-1',
                'autocomplete': 'off',
            })
        )

    for q in questions:
        field_name = f'q_{q.pk}'
        if q.question_type == 'rating':
            _FeedbackForm.base_fields[field_name] = forms.ChoiceField(
                choices=RATING_CHOICES,
                widget=forms.RadioSelect,
                label=q.question_text,
                required=q.required,
            )
        elif q.question_type == 'yes_no':
            _FeedbackForm.base_fields[field_name] = forms.ChoiceField(
                choices=YES_NO_CHOICES,
                widget=forms.RadioSelect,
                label=q.question_text,
                required=q.required,
            )
        elif q.question_type == 'text':
            _FeedbackForm.base_fields[field_name] = forms.CharField(
                widget=forms.Textarea(attrs={'rows': 3}),
                label=q.question_text,
                required=q.required,
            )
        elif q.question_type == 'choice':
            choices = [(c, c) for c in (q.choices or [])]
            _FeedbackForm.base_fields[field_name] = forms.TypedChoiceField(
                choices=choices,
                widget=forms.Select,
                label=q.question_text,
                required=q.required,
            )

    return _FeedbackForm