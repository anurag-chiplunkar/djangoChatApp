import os
import random
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
import uuid


def getFileName(filePath):
    """
    Extracts the name and extension of a file path.

    Args:
        filePath (str): The file path.

    Returns:
        Two variables containing the name and extension of the file.
    """
    baseName = os.path.basename(filePath)
    name, ext = os.path.splitext(baseName)
    return name, ext


def uploadImagePath(instance, fileName):
    """
    Generates a unique filename for an uploaded image and constructs the final path.

    Args:
        instance (Profile): The Profile instance associated with the image.
        fileName (str): The original filename of the image.

    Returns:
        str: The final path for the uploaded image. This string contains the initial folder avatars and then the respective
        folder for each of the user with username as the name of the folder followed by the final file name.
    """
    newFileName = random.randint(1, 9999999999)
    name, ext = getFileName(fileName)
    finalFileName = f'{newFileName}{ext}'
    return f"avatars/{instance.user}/{finalFileName}"


class Profile(models.Model):
    """
    Represents a user profile with additional information.

    Attributes:
        user (User): The user associated with the profile.
        avatar (ImageField): The avatar image of the user.
        is_online (bool): Indicates whether the user is currently online.

    Properties:
        avatarUrl (str): The URL of the user's avatar image.
    """
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name='profile_detail')
    avatar = models.ImageField(upload_to=uploadImagePath, null=True, blank=True, default="avatars/default/default.jpg")
    is_online = models.BooleanField(default = False)

    @property
    def avatarUrl(self):
        """
        Gets the URL of the user's avatar image.

        Returns:
            str: The URL of the avatar image.
        """
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        else:
            return "/avatars/default/default.jpg"


class ChatSession(models.Model):
    """
    Represents a chat session between two users.

    Attributes:
        user1 (User): The first user in the chat session.
        user2 (User): The second user in the chat session.
        updated_on (DateTimeField): The timestamp of the last update to the chat session.

    Meta:
        unique_together (tuple): Specifies that each combination of user1 and user2 must be unique.
        verbose_name (str): Human-readable name for the model in the Django admin interface.

    Methods:
        __str__(): Returns a string representation of the chat session.
        room_group_name(): Generates the name of the room group for this chat session.
        chat_session_exists(user1, user2): Checks if a chat session exists between the given users.
        create_if_not_exists(user1, user2): Creates a new chat session if it does not already exist.

    """
    user1 = models.ForeignKey(User,on_delete=models.CASCADE,related_name='user1_name')
    user2 = models.ForeignKey(User,on_delete=models.CASCADE,related_name='user2_name')
    updated_on = models.DateTimeField(auto_now = True)
    
    class Meta:
        unique_together = ("user1", "user2")
        verbose_name = 'Chat Message'
        
    def __str__(self):
        """
        Returns a string representation of the chat session.

        Returns:
            str: The string representation of the chat session in the format "user1_username_user2_username".
        """
        return '%s_%s' % (self.user1.username, self.user2.username)
        
    @property
    def room_group_name(self):
        """
        Generates the name of the room group for this chat session.

        Returns:
            str: The name of the room group.
        """
        return f'chat_{self.id}'

    @staticmethod
    def chat_session_exists(user1,user2):
        """
        Checks if a chat session exists between the given users.

        Args:
            user1 (User): The first user.
            user2 (User): The second user.

        Returns:
            ChatSession or None: The chat session if it exists, otherwise None.
        """
        return ChatSession.objects.filter(Q(user1=user1, user2=user2) | Q(user1=user2, user2=user1)).first()
    
    @staticmethod
    def create_if_not_exists(user1,user2):
        """
        Creates a new chat session if it does not already exist.

        Args:
            user1 (User): The first user.
            user2 (User): The second user.

        Returns:
            bool: True if a new chat session was created, False if it already existed.
        """
        res = ChatSession.chat_session_exists(user1,user2)
        return False if res else ChatSession.objects.create(user1=user1,user2=user2)


class ChatMessage(models.Model):
    """
    Represents a message in a chat session.

    Attributes:
        id (UUIDField): The unique identifier for the message.
        chat_session (ForeignKey): The chat session to which the message belongs.
        user (ForeignKey): The user who sent the message.
        message_detail (JSONField): Details of the message, including timestamp and read status.

    Meta:
        ordering (list): Specifies the default ordering of instances in queries.

    Methods:
        __str__(): Returns a string representation of the message.
        save(*args, **kwargs): Saves the message instance and updates the corresponding chat session's timestamp.
        count_overall_unread_msg(user_id): Counts the overall number of unread messages for a user.
        message_read_true(message_id): Marks a specific message as read.
        all_msg_read(room_id, user): Marks all unread messages in a chat session as read for a specific user.
        sender_inactive_msg(message_id): Marks a message as sender inactive.
        receiver_inactive_msg(message_id): Marks a message as receiver inactive.
    """
    id = models.UUIDField(primary_key=True, editable = False)
    chat_session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='user_messages')
    user = models.ForeignKey(User, verbose_name='message_sender', on_delete=models.CASCADE)
    message_detail = models.JSONField()

    class Meta:
        ordering = ['-message_detail__timestamp']
    
    def __str__(self):
        """
        Returns a string representation of the message.

        Returns:
            str: The timestamp of the message.
        """
        return '%s' %(self.message_detail["timestamp"])

    def save(self,*args,**kwargs):
        """
        Saves the message instance and updates the corresponding chat session's timestamp.
        """
        super().save(*args,**kwargs)
        ChatSession.objects.get(id = self.chat_session.id).save()   # Update ChatSession TimeStampe

    @staticmethod
    def count_overall_unread_msg(user_id):
        """
        Counts the overall number of unread messages for a user.

        Args:
            user_id (int): The ID of the user.

        Returns:
            int: The total number of unread messages.
        """
        total_unread_msg = 0
        user_all_friends = ChatSession.objects.filter(Q(user1__id = user_id) | Q(user2__id = user_id))
        for ch_session in user_all_friends:
            un_read_msg_count = ChatMessage.objects.filter(chat_session = ch_session.id,message_detail__read = False).exclude(user__id = user_id).count()        
            total_unread_msg += un_read_msg_count
        return total_unread_msg

    @staticmethod
    def meassage_read_true(message_id):
        """
        Marks a specific message as read.

        Args:
            message_id (UUID): The ID of the message.
        """
        msg_inst = ChatMessage.objects.filter(id = message_id).first()
        msg_inst.message_detail['read'] = True
        msg_inst.save(update_fields = ['message_detail',])
        return None

    @staticmethod
    def all_msg_read(room_id,user):
        """
        Marks all unread messages in a chat session as read for a specific user.

        Args:
            room_id (UUID): The ID of the chat session.
            user (str): The username of the user.
        """
        all_msg = ChatMessage.objects.filter(chat_session = room_id,message_detail__read = False).exclude(user__username = user)
        for msg in all_msg:
            msg.message_detail['read'] = True
            msg.save(update_fields = ['message_detail',])
        return None

    @staticmethod
    def sender_inactive_msg(message_id):
        """
        Marks a message as sender inactive.

        Args:
            message_id (UUID): The ID of the message.
        """
        return ChatMessage.objects.filter(id = message_id).update(message_detail__Sclr = True)

    @staticmethod
    def receiver_inactive_msg(message_id):
        """
        Marks a message as receiver inactive.

        Args:
            message_id (UUID): The ID of the message.
        """
        return ChatMessage.objects.filter(id = message_id).update(message_detail__Rclr = True)
