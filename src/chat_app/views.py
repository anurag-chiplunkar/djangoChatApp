from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth import logout
from .forms import ProfileAvatarForm
from .models import *
from django.http.response import HttpResponse, HttpResponseRedirect
from django.contrib import messages

# def room_name(request):
#     return render(request, 'chat/enter_room_name.html')
# def room(request, room_name):
#     return render(request, 'chat/chat.html', {'room_name': room_name})


def home(request):
    if request.user.is_authenticated:
        """
        Renders the home page view.

        This view function renders the home page of the chat application. If the user
        is authenticated, it retrieves the user's profile information and counts the
        overall unread messages for the user. It then renders the home page template
        with the unread message count and the user's profile information if available.

        If the user is not authenticated, it only counts the overall unread messages
        for the anonymous user and renders the home page template with the unread
        message count.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            HttpResponse: The HTTP response containing the rendered home page template.

        """
        profile = Profile.objects.get(user__id=request.user.id)
        unread_msg = ChatMessage.count_overall_unread_msg(request.user.id)
        return render(request, 'chat/home.html', {"unread_msg": unread_msg, "profile": profile})
    else:
        unread_msg = ChatMessage.count_overall_unread_msg(request.user.id)
        return render(request, 'chat/home.html', {"unread_msg": unread_msg})


@login_required
def create_friend(request):
    """
    Handles the creation of a new friend (chat session) for the current user.

    This view function allows an authenticated user to create a new friend (chat session).
    If a user ID is provided as a query parameter in the request, it retrieves the user
    corresponding to that ID and creates a chat session between the current user and
    the selected user. If the chat session is successfully created, a success message
    is displayed; otherwise, an appropriate message is shown.

    If no user ID is provided in the request, the function retrieves a list of all users
    who are not already friends with the current user and renders the create friend page
    template with the available user list.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The HTTP response containing the rendered create friend page template
        or a redirect response to the create friend page.

    """
    user_1 = request.user
    print("user_1", user_1)
    if request.GET.get('id'):
        user2_id = request.GET.get('id')
        print("user2_id", user2_id)
        user_2 = get_object_or_404(User,id = user2_id)
        print("user_2", user_2)
        get_create = ChatSession.create_if_not_exists(user_1,user_2)
        if get_create:
            messages.add_message(request,messages.SUCCESS,f'{user_2.username} successfully added in your chat list!!')
        else:
            messages.add_message(request,messages.SUCCESS,f'{user_2.username} already added in your chat list!!')
        return HttpResponseRedirect('/create_friend')
    else:
        user_all_friends = ChatSession.objects.filter(Q(user1 = user_1) | Q(user2 = user_1))
        user_list = []
        for ch_session in user_all_friends:
            user_list.append(ch_session.user1.id)
            user_list.append(ch_session.user2.id)
        all_user = User.objects.exclude(Q(username=user_1.username)|Q(id__in = list(set(user_list))))
    return render(request, 'chat/create_friend.html',{'all_user' : all_user})


@login_required
def friend_list(request):
    """
    Renders the list of friends (chat sessions) for the current user.

    This view function retrieves the list of chat sessions associated with the
    current user where the current user is either user1 or user2. It orders the
    chat sessions by their last update time and retrieves relevant information
    about each friend, including their username, unread message count, online
    status, avatar, and user ID.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The HTTP response containing the rendered friend list page template
        with the list of friends and their information.

    """
    user_inst = request.user
    user_all_friends = ChatSession.objects.filter(Q(user1 = user_inst) | Q(user2 = user_inst)).select_related('user1','user2').order_by('-updated_on')
    all_friends = []
    for ch_session in user_all_friends:
        user, user_inst = [ch_session.user2,ch_session.user1] if request.user.username == ch_session.user1.username else [ch_session.user1,ch_session.user2]
        un_read_msg_count = ChatMessage.objects.filter(chat_session = ch_session.id,message_detail__read = False).exclude(user = user_inst).count()        
        data = {
            "user_name": user.username,
            "room_name": ch_session.room_group_name,
            "un_read_msg_count": un_read_msg_count,
            "status": user.profile_detail.is_online,
            "avatar": user.profile_detail.avatar,
            "user_id": user.id
        }
        all_friends.append(data)

    return render(request, 'chat/friend_list.html', {'user_list': all_friends})


@login_required
def start_chat(request, room_name):
    """
    Renders the chat interface for the specified chat session.

    This view function handles requests to start a chat with a specific user.
    It first checks if the current user has permission to access the chat session
    specified by the given room name. If the user has permission, it retrieves
    information about the chat session, including the opposite user, and fetches
    all messages associated with the chat session. It then renders the chat interface
    template with the necessary data.

    Args:
        request (HttpRequest): The HTTP request object.
        room_name (str): The unique identifier of the chat session (room).

    Returns:
        HttpResponse: The HTTP response containing the rendered chat interface template
        or an error message if the user doesn't have permission to access the chat session.

    """
    current_user = request.user
    try:

        check_user = ChatSession.objects.filter(Q(id = room_name[5:])&(Q(user1 = current_user) | Q(user2 = current_user)))
    except Exception:
        return HttpResponse("Something went wrong!!!")
    if check_user.exists():
        chat_user_pair = check_user.first()
        opposite_user = chat_user_pair.user2 if chat_user_pair.user1.username == current_user.username else chat_user_pair.user1
        fetch_all_message = ChatMessage.objects.filter(chat_session__id = room_name[5:]).order_by('message_detail__timestamp')
        return render(request,'chat/start_chat.html',{'room_name' : room_name,'opposite_user' : opposite_user,'fetch_all_message' : fetch_all_message})
    else:
        return HttpResponse("You have't permission to chatting with this user!!!")


def get_last_message(request):
    """
    Retrieves the last message from a chat session.

    This function handles requests to retrieve the last message from a specified chat session.
    It expects a POST request containing the 'room_id' parameter in the request data, which
    represents the unique identifier of the chat session (room). The function retrieves the
    last message from the chat session specified by the 'room_id' parameter and returns it.

    Args:
        request (HttpRequest): The HTTP request object containing the 'room_id' parameter in the request data.

    Returns:
        ChatMessage: The last message object from the specified chat session.

    Raises:
        IndexError: If no messages are found in the specified chat session.
    """
    session_id = request.data.get('room_id')
    qs = ChatMessage.objects.filter(chat_session__id=session_id)[10]
    return qs


def logoutView(request):
    """
    Logs out the current user.

    This function handles POST requests to log out the currently authenticated user.
    Upon receiving a POST request, it logs out the user by calling the Django `logout` function,
    which flushes the user's session data. After logging out, the function redirects the user
    to the home page.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponseRedirect: Redirects the user to the home page after successfully logging out.
    """
    if request.method == 'POST':
        logout(request)
        return redirect("home_page")


def updateProfile(request):
    """
    Updates the profile information of the currently authenticated user.

    This function handles requests to update the profile information of the currently authenticated user.
    If the user is authenticated, it retrieves the user's profile data and populates a profile form with
    the existing data. Upon receiving a POST request with updated profile information, the function validates
    the form data. If the form is valid, it saves the updated profile information and redirects the user to
    the home page. If the user is not authenticated, the function redirects them to the home page.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponseRedirect or HttpResponse: Redirects the user to the home page if the user is not authenticated,
        or redirects them to the home page after successfully updating the profile information.

    """
    if request.user.is_authenticated:
        profileUser = Profile.objects.get(user__id=request.user.id)

        profileForm = ProfileAvatarForm(request.POST or None, request.FILES or None, instance=profileUser)
        if profileForm.is_valid():
            profileForm.save()
            return redirect('home_page')
        return render(request, "chat/updateProfile.html", {'profileForm': profileForm})
    else:
        return redirect('home_page')
