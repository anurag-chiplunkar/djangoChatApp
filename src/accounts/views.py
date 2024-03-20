from django.shortcuts import render
from .forms import RegisterForm
from django.contrib.auth import get_user_model


User = get_user_model()


def registerPage(request):
    """
    View function for registering a new user.

    Parameters:
    - request (HttpRequest): The HTTP request object.

    Returns:
    - HttpResponse: Rendered HTML response containing the registration form.

    Raises:
    - No explicit exception handling. Any exceptions raised during form validation or user creation
      will bubble up and potentially be handled by Django's built-in error handling mechanisms.
    """
    form = RegisterForm(request.POST or None)
    context = {
        'form': form
    }
    if form.is_valid():
        print(form.cleaned_data)
        email = form.cleaned_data.get('email')
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        newUser = User.objects.create_user(username=username, email=email, password=password)
        print(newUser)
        context['form'] = RegisterForm()
    return render(request, "register/register.html", context)