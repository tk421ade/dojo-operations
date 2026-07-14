from django.db import migrations


def backfill_conditional_questions(apps, schema_editor):
    SessionFeedbackLink = apps.get_model('shodan', 'SessionFeedbackLink')
    SessionFeedbackQuestion = apps.get_model('shodan', 'SessionFeedbackQuestion')

    PARENT_TEXT = 'Would you attend another session like this?'
    IDEAL_DURATION_TEXT = 'If yes, what would be the ideal duration?'
    WHY_NOT_TEXT = 'Why not? (cost, travel time, etc)'

    for link in SessionFeedbackLink.objects.all():
        parent = link.questions.filter(question_text=PARENT_TEXT).first()
        if not parent:
            continue

        # Make the "ideal duration" question conditional on "yes"
        ideal = link.questions.filter(question_text=IDEAL_DURATION_TEXT).first()
        if ideal:
            ideal.conditional_parent = parent
            ideal.conditional_answer = 'yes'
            ideal.save(update_fields=['conditional_parent', 'conditional_answer'])

        # Create the "Why not?" question (conditional on "no") if missing
        why_not = link.questions.filter(question_text=WHY_NOT_TEXT).first()
        if not why_not:
            order = ideal.order if ideal else 9
            SessionFeedbackQuestion.objects.create(
                feedback_link=link,
                question_text=WHY_NOT_TEXT,
                question_type='text',
                choices=[],
                order=order,
                required=False,
                conditional_parent=parent,
                conditional_answer='no',
            )


class Migration(migrations.Migration):

    dependencies = [
        ('shodan', '0029_feedback_conditional_questions'),
    ]

    operations = [
        migrations.RunPython(backfill_conditional_questions, migrations.RunPython.noop),
    ]
