from vrcpy import Client, objects
from vrcpy.errors import WebSocketError, WebSocketOpenedError, IntegretyError
from vrcpy.types import State
import threading
import websocket
import time
import json


class WSSClient(Client):
    def __init__(self, verify=True, reconnect=True):
        super().__init__(verify)

        self.ws = None
        self._wsthread = None

        self.reconnect = reconnect

    def login(self, username, password):
        super().login(username, password)
        if self.loggedIn:
            self.connect()

    def login2fa(self, username, password, code=None, verify=False):
        super().login2fa(username, password, code, verify)
        if self.loggedIn:
            self.connect()

    def verify2fa(self, code):
        super().verify2fa(code)
        if self.loggedIn:
            self.connect()

    def logout(self):
        super().logout()
        if not self.loggedIn:
            self.disconnect()

    def connect(self):
        if self.ws is not None:
            raise WebSocketOpenedError("There is already a websocket open!")

        auth = self.api.session.cookies.get("auth")

        # websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            "wss://pipeline.vrchat.cloud/?authToken="+auth,
            on_message=self._ws_message,
            on_error=self._ws_error,
            on_close=self._ws_close,
            on_open=self._ws_open)

        self._wsthread = threading.Thread(target=self.ws.run_forever)
        self._wsthread.daemon = True
        self._wsthread.start()

    def disconnect(self):
        if self.ws is None:
            return

        self.reconnect = False
        self.ws.close()

    def _do_function(self, function, *args):
        function(*args)

    def _ws_message(self, ws, message):
        message = json.loads(message)

        switch = {
            "friend-location": self._ws_friend_location,
            "friend-online": self._ws_friend_online,
            "friend-active": self._ws_friend_active,
            "friend-offline": self._ws_friend_offline,
            "friend-add": self._ws_friend_add,
            "friend-delete": self._ws_friend_delete,
            "friend-update": self._ws_friend_update,
            "notification": self._ws_notification
        }

        if message["type"] in switch:
            self._do_function(switch[message["type"]], json.loads(message["content"]))  # leaving this like that, so it doesn't give me stupid warnings
        else:
            self._ws_unhandled_event(message["type"], json.loads(message["content"]))

    def _ws_error(self, ws, error):
        raise WebSocketError(error)

    def _ws_close(self, ws):
        self.ws = None
        self._wssthread = None

        self.on_disconnect()

        if self.reconnect:
            time.sleep(2)
            self.connect()

    def _ws_open(self, ws):
        self.on_connect()

    def _update_friend(self, newUser, id):
        # Updates self.me friends lists
        # Returns old user

        oldUser = None

        for user in self.me.onlineFriends:
            if user.id == id:
                oldUser = user
                self.me.onlineFriends.remove(user)
                break

        if oldUser is None:
            for user in self.me.offlineFriends:
                if user.id == id:
                    oldUser = user
                    self.me.offlineFriends.remove(user)
                    break

        if newUser is not None:
            if newUser.state is State.Offline:
                self.me.offlineFriends.append(newUser)
            else:
                self.me.onlineFriends.append(newUser)

        self.me.friends = self.me.offlineFriends + self.me.onlineFriends
        return oldUser

    def _ws_friend_online(self, content):
        user = objects.User(self, content["user"])
        self._update_friend(user, user.id)
        self.on_friend_online(user)

    def _ws_friend_active(self, content):
        user = objects.User(self, content["user"])
        self._update_friend(user, user.id)
        self.on_friend_active(user)

    def _ws_friend_location(self, content):
        user = objects.User(self, content["user"])

        if content["location"] == "private":
            self.on_friend_location(user, None, None, None)
            return

        try:
            world = objects.World(self, content["world"])
        except IntegretyError:
            world = self.fetch_world(content["world"]["id"])

        instance = world.fetch_instance(content["instance"])
        location = objects.Location(self, content["location"])

        self._update_friend(user, user.id)
        self.on_friend_location(user, world, location, instance)

    def _ws_friend_offline(self, content):
        user = self.fetch_user_by_id(content["userId"])
        self._update_friend(user, user.id)
        self.on_friend_offline(user)

    def _ws_friend_add(self, content):
        user = objects.User(self, content["user"])
        self._update_friend(user, user.id)
        self.on_friend_add(user)

    def _ws_friend_delete(self, content):
        user = self._update_friend(None, content["userId"])
        self.on_friend_delete(user)

    def _ws_friend_update(self, content):
        user = objects.User(self, content["user"])
        self._update_friend(user, user.id)
        self.on_friend_update(user)

    def _ws_notification(self, content):
        self.on_notification(objects.Notification(self, content))

    def _ws_unhandled_event(self, event, content):
        self.on_unhandled_event(event, content)

    def event(self, func):
        """Decorator that overwrites class ws event hooks

        Example
        ---------

        @client.event
        def on_connect():
            print("Connected to wss pipeline.")

        """

        if func.__name__.startswith("on_") and hasattr(self, func.__name__):
            setattr(self, func.__name__, func)
            return func
        else:
            raise TypeError("Registered event must be a valid event function")

    def on_friend_online(self, friend):
        pass

    def on_friend_active(self, friend):
        pass

    def on_friend_offline(self, friend):
        pass

    def on_friend_location(self, friend, world, location, instance):
        pass

    def on_friend_add(self, friend):
        pass

    def on_friend_delete(self, friend):
        pass

    def on_friend_update(self, friend):
        pass

    def on_notification(self, notification):
        pass

    def on_unhandled_event(self, event, content):
        pass

    def on_disconnect(self):
        pass

    def on_connect(self):
        pass
