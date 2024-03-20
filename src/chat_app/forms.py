from django import forms
from .models import Profile


class ProfileAvatarForm(forms.ModelForm):
    """
    A form for updating the avatar of a user's profile.

    This form allows users to upload a new avatar image for their profile. It is
    associated with the `Profile` model and includes a field for the avatar image.

    Attributes:
        model (Model): The model associated with the form, which is `Profile`.
        fields (list): The fields included in the form, which only includes the `avatar` field.

    """
    class Meta:
        model = Profile
        fields = ['avatar']
