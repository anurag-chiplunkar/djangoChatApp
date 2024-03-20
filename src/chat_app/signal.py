from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_save
from .models import ChatSession,ChatMessage,Profile
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User


@receiver(post_save,sender=ChatSession)
def sender_receiver_no_same(sender, instance, created, **kwargs):
    """
    Validates that the sender and receiver of a chat session are not the same.

    This signal receiver function is triggered after a new `ChatSession` instance
    is saved. It checks if the sender and receiver of the chat session are the same
    user, and if so, it raises a ValidationError to indicate that the sender and
    receiver should not be the same.

    Args:
        sender (Model): The model class that sent the signal, which is `ChatSession`.
        instance (ChatSession): The instance of the `ChatSession` model that was saved.
        created (bool): A boolean indicating whether the instance was created or updated.
        **kwargs: Additional keyword arguments.

    Raises:
        ValidationError: If the sender and receiver of the chat session are the same.

    """
    if created:
        if instance.user1 == instance.user2:
            raise ValidationError("Sender and Receiver are not same!!", code='Invalid')


@receiver(post_save,sender=User)
def at_ending_save(sender, instance, created, **kwargs):
    """
    Creates associated profile after saving a new user.

    This signal receiver function is triggered after a new `User` instance is saved.
    It checks if the user instance was newly created, and if so, it creates a corresponding
    `Profile` instance associated with the user. This ensures that a profile is created
    for every new user added to the system.

    Args:
        sender (Model): The model class that sent the signal, which is `User`.
        instance (User): The instance of the `User` model that was saved.
        created (bool): A boolean indicating whether the instance was created or updated.
        **kwargs: Additional keyword arguments.

    """
    if created:
        # UserChat.objects.create(user = instance)
        Profile.objects.create(user=instance)


@receiver(post_save,sender=ChatMessage)
def user_must_sender_or_receiver(sender, instance, created, **kwargs):
    """
    Validates that the message sender is either the sender or receiver of the chat session.

    This signal receiver function is triggered after a new `ChatMessage` instance
    is saved. It checks if the message sender is either the sender or receiver of
    the associated chat session. If not, it raises a ValidationError to indicate
    that the sender must be one of the participants of the chat session.

    Args:
        sender (Model): The model class that sent the signal, which is `ChatMessage`.
        instance (ChatMessage): The instance of the `ChatMessage` model that was saved.
        created (bool): A boolean indicating whether the instance was created or updated.
        **kwargs: Additional keyword arguments.

    Raises:
        ValidationError: If the message sender is not one of the participants of the chat session.

    """
    if created:
        if instance.user != instance.chat_session.user1 and instance.user != instance.chat_session.user2:
            raise ValidationError("Invalid sender!!", code='Invalid')