from channels.generic.websocket import AsyncWebsocketConsumer
import json
from datetime import datetime
from chat_app.models import ChatSession, ChatMessage
from channels.db import database_sync_to_async
import uuid
from .models import Profile
from django.db.models import Q


MESSAGE_MAX_LENGTH = 10

MESSAGE_ERROR_TYPE = {
    "MESSAGE_OUT_OF_LENGTH": 'MESSAGE_OUT_OF_LENGTH',
    "UN_AUTHENTICATED": 'UN_AUTHENTICATED',
    "INVALID_MESSAGE": 'INVALID_MESSAGE',
}

MESSAGE_TYPE = {
    "WENT_ONLINE": 'WENT_ONLINE',
    "WENT_OFFLINE": 'WENT_OFFLINE',
    "IS_TYPING": 'IS_TYPING',
    "NOT_TYPING": 'NOT_TYPING',
    "MESSAGE_COUNTER": 'MESSAGE_COUNTER',
    "OVERALL_MESSAGE_COUNTER": 'OVERALL_MESSAGE_COUNTER',
    "TEXT_MESSAGE": 'TEXT_MESSAGE',
    "MESSAGE_READ": 'MESSAGE_READ',
    "ALL_MESSAGE_READ": 'ALL_MESSAGE_READ',
    "ERROR_OCCURED": 'ERROR_OCCURED'
}


class PersonalConsumer(AsyncWebsocketConsumer):
    """
    Handles WebSocket connections and messages for personal chat sessions.

    Methods:
        connect(): Handles the WebSocket connection initiation.
        disconnect(code): Handles the WebSocket connection termination.
        receive(text_data): Handles incoming WebSocket messages.
        user_online(event): Sends a message indicating a user has gone online.
        message_counter(event): Sends a message containing the count of unread messages.
        user_offline(event): Sends a message indicating a user has gone offline.
        set_online(user_id): Sets a user as online and retrieves IDs of their friends for notifications.
        set_offline(user_id): Sets a user as offline and retrieves IDs of their friends for notifications.
        count_unread_overall_msg(user_id): Counts the overall number of unread messages for a user.
    """
    async def connect(self):
        """
        Handles the WebSocket connection initiation.

        This method is called when a client attempts to establish a WebSocket connection.
        It extracts the room name from the URL route kwargs, constructs the room group name,
        and adds the channel to the corresponding group. If the user is authenticated, the
        connection is accepted, allowing communication via WebSocket. If the user is not
        authenticated, the connection is closed with a custom code indicating authentication failure.

        Raises:
            WebSocketError: If an error occurs during WebSocket connection initiation.

        """
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'personal__{self.room_name}'
        self.user = self.scope['user']

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        if self.scope["user"].is_authenticated:
            await self.accept()
        else:
            await self.close(code=4001)
            
    async def disconnect(self, code):
        """
        Handles the WebSocket connection termination.

        This method is called when a WebSocket connection is closed. It sets the user offline
        by calling the `set_offline` method, and removes the channel from the corresponding room
        group using `group_discard` method.

        Args:
            code (int): The status code indicating the reason for disconnection.

        Raises:
            WebSocketError: If an error occurs during WebSocket disconnection handling.

        """
        self.set_offline()
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
    async def receive(self, text_data):
        """
        Handles incoming WebSocket messages.

        This method is called when a message is received over the WebSocket connection.
        It parses the received JSON data to extract the message type and user ID. Depending
        on the message type, it either sets the user online or offline using `set_online`
        or `set_offline` methods, respectively. It then sends appropriate notifications to
        the relevant room groups indicating the user's online or offline status.

        Args:
            text_data (str): The received JSON data as a string.

        Raises:
            WebSocketError: If an error occurs during WebSocket message handling.

        """
        data = json.loads(text_data)
        msg_type = data.get('msg_type')
        user_id = data.get('user_id')
        
        if msg_type == MESSAGE_TYPE['WENT_ONLINE']:
            users_room_id = await self.set_online(user_id)
            for room_id in users_room_id:
                await self.channel_layer.group_send(
                    f'personal__{room_id}',
                    {
                    'type': 'user_online',
                    'user_name' : self.user.username
                    }
                )
        elif msg_type == MESSAGE_TYPE['WENT_OFFLINE']:
            users_room_id = await self.set_offline(user_id)
            for room_id in users_room_id:
                await self.channel_layer.group_send(
                    f'personal__{room_id}',
                    {
                    'type': 'user_offline',
                    'user_name' : self.user.username
                    }
                )
            
    async def user_online(self,event):
        """
        Sends a message indicating a user has gone online.

        This method is invoked when a user goes online, triggering a notification event.
        It sends a WebSocket message to the client containing information about the user
        who has gone online, including their username.

        Args:
            event (dict): A dictionary containing information about the online user event.

        Raises:
            WebSocketError: If an error occurs during WebSocket message handling.

        """
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['WENT_ONLINE'],
            'user_name' : event['user_name']
        }))
        
    async def message_counter(self, event):
        """
        Sends a message containing the count of unread messages.

        This method is invoked when a message counter event is triggered, typically after a user
        receives a new message. It calculates the overall number of unread messages for the current
        user by calling the `count_unread_overall_msg` method. Then, it sends a WebSocket message
        to the client containing the count of unread messages.

        Args:
            event (dict): A dictionary containing information about the message counter event.

        Raises:
            WebSocketError: If an error occurs during WebSocket message handling.

        """
        overall_unread_msg = await self.count_unread_overall_msg(event['current_user_id'])
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['MESSAGE_COUNTER'],
            'user_id': event['user_id'],
            'overall_unread_msg' : overall_unread_msg
        }))

    async def user_offline(self,event):
        """
        Sends a message indicating a user has gone offline.

        This method is invoked when a user goes offline, triggering a notification event.
        It sends a WebSocket message to the client containing information about the user
        who has gone offline, including their username.

        Args:
            event (dict): A dictionary containing information about the offline user event.

        Raises:
            WebSocketError: If an error occurs during WebSocket message handling.

        """
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['WENT_OFFLINE'],
            'user_name' : event['user_name']
        }))
    
    @database_sync_to_async
    def set_online(self,user_id):
        """
        Sets a user as online and retrieves IDs of their friends for notifications.

        This method is responsible for updating the online status of a user in the database
        and retrieving the IDs of their friends for sending online notifications. It marks the
        user as online by updating the `is_online` field in the `Profile` model. Then, it retrieves
        the chat sessions involving the current user and extracts the IDs of their friends based
        on the session participants.

        Args:
            user_id (int): The ID of the user to set as online.

        Returns:
            list: A list of user IDs representing friends of the current user.

        Raises:
            DatabaseError: If an error occurs while accessing or updating the database.

        """
        Profile.objects.filter(user__id = user_id).update(is_online = True)
        user_all_friends = ChatSession.objects.filter(Q(user1 = self.user) | Q(user2 = self.user))
        user_id = []
        for ch_session in user_all_friends:
            user_id.append(ch_session.user2.id) if self.user.username == ch_session.user1.username else user_id.append(ch_session.user1.id)
        return user_id

    @database_sync_to_async
    def set_offline(self,user_id):
        """
        Sets a user as offline and retrieves IDs of their friends for notifications.

        This method is responsible for updating the online status of a user in the database
        and retrieving the IDs of their friends for sending offline notifications. It marks the
        user as offline by updating the `is_online` field in the `Profile` model. Then, it retrieves
        the chat sessions involving the current user and extracts the IDs of their friends based
        on the session participants.

        Args:
            user_id (int): The ID of the user to set as offline.

        Returns:
            list: A list of user IDs representing friends of the current user.

        Raises:
            DatabaseError: If an error occurs while accessing or updating the database.

        """
        Profile.objects.filter(user__id = user_id).update(is_online = False)
        user_all_friends = ChatSession.objects.filter(Q(user1 = self.user) | Q(user2 = self.user))
        user_id = []
        for ch_session in user_all_friends:
            user_id.append(ch_session.user2.id) if self.user.username == ch_session.user1.username else user_id.append(ch_session.user1.id)
        return user_id

    @database_sync_to_async
    def count_unread_overall_msg(self,user_id):
        """
        Counts the overall number of unread messages for a user.

        This method asynchronously calculates the total number of unread messages for a given user.
        It queries the `ChatMessage` model to count the unread messages associated with the provided
        user ID.

        Args:
            user_id (int): The ID of the user for whom the unread messages are counted.

        Returns:
            int: The total number of unread messages for the specified user.

        Raises:
            DatabaseError: If an error occurs while accessing the database.

        """
        return ChatMessage.count_overall_unread_msg(user_id)
    

class ChatConsumer(AsyncWebsocketConsumer):
    """
    Handles WebSocket connections and messages for group chat sessions.

    Methods:
        connect(): Handles the WebSocket connection initiation.
        disconnect(code): Handles the WebSocket connection termination.
        receive(text_data): Handles incoming WebSocket messages.
        chat_message(event): Sends a message to the WebSocket group chat.
        msg_as_read(event): Sends a message indicating a specific message has been read.
        all_msg_read(event): Sends a message indicating all messages have been read.
        user_is_typing(event): Sends a message indicating a user is typing.
        user_not_typing(event): Sends a message indicating a user has stopped typing.
        save_text_message(msg_id, message): Asynchronously saves a text message to the database.
        msg_read(msg_id): Asynchronously marks a message as read in the database.
        read_all_msg(room_id, user): Asynchronously marks all messages in a room as read.
    """

    async def connect(self):
        """
        Handles the initiation of a WebSocket connection.

        This method is invoked when a client attempts to establish a WebSocket connection.
        It extracts the room name from the URL route parameters and sets up the room group
        name accordingly. The user associated with the connection is also determined from
        the scope. The method then adds the channel to the corresponding room group. If the
        user is authenticated, the connection is accepted; otherwise, an error message is sent
        to the client, and the connection is closed with a specified error code.

        Raises:
            WebSocketError: If an error occurs during WebSocket connection handling.

        """
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = self.room_name
        self.user = self.scope['user']

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        if self.scope["user"].is_authenticated:
            await self.accept()
        else:
            await self.accept()
            await self.send(text_data=json.dumps({
                "msg_type": MESSAGE_TYPE['ERROR_OCCURED'],
                "error_message": MESSAGE_ERROR_TYPE["UN_AUTHENTICATED"],
                "user": self.user.username,
            }))
            await self.close(code=4001)

    async def disconnect(self, code):
        """
        Handles the termination of a WebSocket connection.

        This method is invoked when a WebSocket connection is closed, either by the client
        or due to an error. It removes the channel from the associated room group, effectively
        unsubscribing the client from further messages in the group.

        Args:
            code (int): The close code associated with the disconnection.

        Raises:
            WebSocketError: If an error occurs during WebSocket disconnection handling.

        """
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        """
        Handles incoming WebSocket messages.

        This method is invoked when the WebSocket consumer receives a message from the client.
        It processes the received message, extracts the message type, message content, and user
        information. Depending on the message type, it performs different actions:

        - For text messages, it verifies the message length, generates a unique message ID, sends
          the message to the chat group, and updates message counters.
        - For message read events, it marks the specified message as read and notifies the chat group.
        - For all message read events, it marks all messages in the group as read and notifies the group.
        - For typing events, it notifies the group that a user is typing.
        - For not typing events, it notifies the group that a user has stopped typing.

        Args:
            text_data (str): The JSON-encoded text data received from the client.

        Raises:
            WebSocketError: If an error occurs during message processing or handling.

        """
        data = json.loads(text_data)
        message = data.get('message')
        msg_type = data.get('msg_type')
        user = data.get('user')

        if msg_type == MESSAGE_TYPE['TEXT_MESSAGE']:
            if len(message) <= MESSAGE_MAX_LENGTH:
                msg_id = uuid.uuid4()
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'user': user,
                        'msg_id' : str(msg_id)
                    }
                )
                current_user_id = await self.save_text_message(msg_id,message)
                await self.channel_layer.group_send(
                    f'personal__{current_user_id}',
                    {
                        'type': 'message_counter',
                        'user_id' : self.user.id,
                        'current_user_id' : current_user_id
                    }
                )
            else:
                await self.send(text_data=json.dumps({
                    'msg_type': MESSAGE_TYPE['ERROR_OCCURED'],
                    'error_message': MESSAGE_ERROR_TYPE["MESSAGE_OUT_OF_LENGTH"],
                    'message': message,
                    'user': user,
                    'timestampe': str(datetime.now()),
                }))
        elif msg_type == MESSAGE_TYPE['MESSAGE_READ']:
            msg_id = data['msg_id']
            await self.msg_read(msg_id)
            await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                    'type': 'msg_as_read',
                    'msg_id': msg_id,
                    'user' : user
                    }
                )  
        elif msg_type == MESSAGE_TYPE['ALL_MESSAGE_READ']:
            await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                    'type': 'all_msg_read',
                    'user' : user,
                    }
                )
            await self.read_all_msg(self.room_name[5:],user)
        elif msg_type == MESSAGE_TYPE['IS_TYPING']:
            await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                    'type': 'user_is_typing',
                    'user' : user,
                    }
                )
        elif msg_type == MESSAGE_TYPE["NOT_TYPING"]:
            await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                    'type': 'user_not_typing',
                    'user' : user,
                    }
                )

    # Receive message from room group
    async def chat_message(self, event):
        """
        Sends a chat message to the WebSocket client.

        This method is invoked when a chat message event is received from the channel layer.
        It formats the received event data into a JSON message containing the message type,
        message content, user information, timestamp, and message ID. The formatted message
        is then sent to the WebSocket client.

        Args:
            event (dict): The event data received from the channel layer containing information
                          about the chat message.

        Raises:
            WebSocketError: If an error occurs while sending the chat message to the client.

        """
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['TEXT_MESSAGE'],
            'message': event['message'],
            'user': event['user'],
            'timestampe': str(datetime.now()),
            'msg_id' : event["msg_id"]
        }))

    async def msg_as_read(self,event):
        """
        Sends a message indicating that a specific message has been read to the WebSocket client.

        This method is invoked when a message read event is received from the channel layer.
        It formats the received event data into a JSON message containing the message type,
        message ID, and user information indicating that the specified message has been read.
        The formatted message is then sent to the WebSocket client.

        Args:
            event (dict): The event data received from the channel layer containing information
                          about the message that has been read.

        Raises:
            WebSocketError: If an error occurs while sending the message read notification to the client.

        """
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['MESSAGE_READ'],
            'msg_id': event['msg_id'],
            'user' : event['user']
        }))

    async def all_msg_read(self,event):
        """
        Sends a message indicating that all messages in a chat room have been read to the WebSocket client.

        This method is invoked when an all message read event is received from the channel layer.
        It formats the received event data into a JSON message containing the message type and
        user information indicating that all messages in the chat room have been read.
        The formatted message is then sent to the WebSocket client.

        Args:
            event (dict): The event data received from the channel layer containing information
                          about the user who has read all messages.

        Raises:
            WebSocketError: If an error occurs while sending the all message read notification to the client.

        """
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['ALL_MESSAGE_READ'],
            'user' : event['user']
        }))

    async def user_is_typing(self,event):
        """
        Sends a message indicating that a user is typing to the WebSocket client.

        This method is invoked when a user typing event is received from the channel layer.
        It formats the received event data into a JSON message containing the message type
        and user information indicating that the specified user is currently typing.
        The formatted message is then sent to the WebSocket client.

        Args:
            event (dict): The event data received from the channel layer containing information
                          about the user who is typing.

        Raises:
            WebSocketError: If an error occurs while sending the user typing notification to the client.

        """
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['IS_TYPING'],
            'user' : event['user']
        }))

    async def user_not_typing(self,event):
        """
        Sends a message indicating that a user has stopped typing to the WebSocket client.

        This method is invoked when a user not typing event is received from the channel layer.
        It formats the received event data into a JSON message containing the message type
        and user information indicating that the specified user has stopped typing.
        The formatted message is then sent to the WebSocket client.

        Args:
            event (dict): The event data received from the channel layer containing information
                          about the user who has stopped typing.

        Raises:
            WebSocketError: If an error occurs while sending the user not typing notification to the client.

        """
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['NOT_TYPING'],
            'user' : event['user']
        }))

    @database_sync_to_async
    def save_text_message(self,msg_id,message):
        """
        Saves a text message to the database and updates message details.

        This method creates a new chat message instance with the provided message ID
        and saves it to the database. The message details include the message content,
        read status, timestamp, and user-specific read status. The method determines
        the appropriate user IDs based on the chat session associated with the WebSocket
        connection.

        Args:
            msg_id (str): The unique ID of the message to be saved.
            message (str): The content of the message to be saved.

        Returns:
            int: The user ID of the recipient of the message.

        Raises:
            ChatSession.DoesNotExist: If the associated chat session does not exist.
            ChatMessage.DoesNotExist: If the associated chat message does not exist.
            IntegrityError: If there is an integrity constraint violation when creating
                            the chat message instance.

        """
        session_id = self.room_name[5:]
        session_inst = ChatSession.objects.select_related('user1', 'user2').get(id=session_id)
        message_json = {
            "msg": message,
            "read": False,
            "timestamp": str(datetime.now()),
            session_inst.user1.username: False,
            session_inst.user2.username: False
        }
        ChatMessage.objects.create(id = msg_id,chat_session=session_inst, user=self.user, message_detail=message_json)
        return session_inst.user2.id if self.user == session_inst.user1 else session_inst.user1.id
    
    @database_sync_to_async
    def msg_read(self,msg_id):
        """
        Marks a message as read in the database.

        This method updates the read status of the specified message in the database
        to indicate that it has been read by the recipient user.

        Args:
            msg_id (str): The unique ID of the message to be marked as read.

        Returns:
            None

        Raises:
            ChatMessage.DoesNotExist: If the specified message does not exist.

        """
        return ChatMessage.meassage_read_true(msg_id)

    @database_sync_to_async
    def read_all_msg(self,room_id,user):
        """
        Marks all messages in a chat room as read in the database.

        This method updates the read status of all messages in the specified chat room
        to indicate that they have been read by the recipient user.

        Args:
            room_id (str): The ID of the chat room whose messages are to be marked as read.
            user (str): The username of the recipient user.

        Returns:
            None

        Raises:
            ChatSession.DoesNotExist: If the specified chat session does not exist.
            ChatMessage.DoesNotExist: If any of the associated chat messages do not exist.

        """
        return ChatMessage.all_msg_read(room_id,user)