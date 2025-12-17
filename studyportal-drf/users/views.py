from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render


def user_login(request):
    # Check if form submitted
    if request.method == 'POST':
        # Bind submitted data to Django's built-in login form
        form = AuthenticationForm(request, data=request.POST)

        # Validate credentials
        if form.is_valid():
            # Get the authenticated user
            user = form.get_user()

            # Log the user in (creates session)
            login(request, user)

            # Redirect to homepage (or you can use next param)
            return redirect('/')
    else:
        # If GET request, display empty form
        form = AuthenticationForm()

    # Render login page with the form (including errors if POST failed)
    return render(request, 'users/login.html', {'form': form})


def user_logout(request):
    # Log the user out (destroy session)
    logout(request)

    # Redirect to homepage after logout
    return redirect('/')
