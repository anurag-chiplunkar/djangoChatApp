from django import forms


class RegisterForm(forms.Form):
    """
    Form class for user registration.

    Fields:
    - email (EmailField): Field for user email.
    - username (CharField): Field for user username.
    - password (CharField): Field for user password.
    - confirmPassword (CharField): Field for confirming user password.

    Methods:
    - clean(): Custom form validation method to ensure password and confirmPassword match.
    """

    email = forms.EmailField(label="Email", widget=forms.TextInput(attrs={"class": "form-control mb-2"}))
    username = forms.CharField(label="Username", widget=forms.TextInput(attrs={"class": "form-control mb-2"}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={"class": "form-control mb-2"}))
    confirmPassword = forms.CharField(label="Confirm Password", widget=forms.PasswordInput(attrs={"class": "form-control mb-2"}))

    def clean(self):
        """
        Custom form validation method to ensure password and confirmPassword match.

        Returns:
        - dict: Cleaned form data if passwords match.

        Raises:
        - ValidationError: If passwords do not match.
        """
        data = self.cleaned_data
        password = self.cleaned_data.get('password')
        confirmPassword = self.cleaned_data.get('confirmPassword')
        if password != confirmPassword:
            raise forms.ValidationError("Password must match.")
        return data

