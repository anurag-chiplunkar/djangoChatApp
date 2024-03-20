from django.contrib import admin
from .models import *
from django_admin_inline_paginator.admin import TabularInlinePaginated


class ChatMessageInline(TabularInlinePaginated):
    """
    Inline editor for displaying chat messages within the Django admin interface.

    This inline editor class is used to display chat messages within the Django admin interface
    when viewing or editing a ChatSession object. It provides a paginated table format for efficient
    display of chat messages associated with a ChatSession.

    Attributes:
        model (Model): The model class for the chat messages (ChatMessage).
        can_delete (bool): Indicates whether users can delete chat messages inline (False in this case).
        fields (tuple): A tuple specifying the fields to be displayed in the inline editor.
        max_num (int): The maximum number of inline chat messages to display (0 for unlimited).
        readonly_fields (tuple): A tuple specifying fields that should be read-only in the inline editor.
        per_page (int): The number of chat messages to display per page in the paginated view.
    """
    model = ChatMessage
    can_delete = False
    fields = ('user','message_detail')
    max_num = 0
    readonly_fields = fields
    per_page = 10


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    """
    Admin configuration for managing chat sessions.

    This admin class provides configuration for managing chat sessions within the Django admin interface.
    It defines the list display, search fields, pagination settings, inline editors, and ordering for the
    ChatSession model.

    Attributes:
        list_display (list): A list of fields to be displayed in the list view of chat sessions.
        search_fields (list): A list of fields to enable searching for chat sessions in the admin interface.
        list_per_page (int): The number of chat sessions to display per page in the admin interface.
        list_display_links (list): A list of fields that serve as links to the detail view of chat sessions.
        inlines (list): A list of inline editors to be included in the detail view of chat sessions.
        ordering (list): A list specifying the default ordering of chat sessions in the admin interface.
    """
    list_display= ["id","user1","user2",'updated_on']
    search_fields=["id","user1__username","user2_username"]
    list_per_page = 10
    list_display_links = list_display
    inlines = [ChatMessageInline,]
    ordering = ['-updated_on']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for managing user profiles.

    This admin class provides configuration for managing user profiles within the Django admin interface.
    It defines the list display, search fields, pagination settings, and ordering for the Profile model.

    Attributes:
        list_display (list): A list of fields to be displayed in the list view of user profiles.
        search_fields (list): A list of fields to enable searching for user profiles in the admin interface.
        list_per_page (int): The number of user profiles to display per page in the admin interface.
        list_display_links (list): A list of fields that serve as links to the detail view of user profiles.
        ordering (list): A list specifying the default ordering of user profiles in the admin interface.
    """
    list_display= ["id","user","is_online"]
    search_fields=["id","user__username"]
    list_per_page = 10
    list_display_links = list_display
    ordering = ['is_online']
