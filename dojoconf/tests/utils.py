
def print_form_errors_from_response(response):
    # Check for form validation errors
    if response.context and response.context['adminform'].errors:
        # Form validation errors exist
        print("Form validation errors:")
        for field, errors in response.context['adminform'].errors.items():
            print(f"{field}: {errors}")
