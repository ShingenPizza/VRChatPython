import json
from typing import List

from vrcpy import types
from vrcpy.errors import IntegrityError, GeneralError


class BaseObject:
    objType = 'Base'

    def __init__(self, client):
        """
        :param client: Client object
        :type client: vrcpy.Client
        """
        self._restricted_names = {  # Set of keys that should not be overwritten by the data received from the API
            '_restricted_names',
            '_types',
            '_array_types',
            '_needs_decoding',
            '_dict',
            'client',
        }
        self._types = {}  # Dictionary of what keys have special types
        self._array_types = {}  # Dictionary of what keys are arrays with special types
        self._needs_decoding = set()  # Set of keys for which values are raw json strings that should be decoded first

        self.id = None
        self.client = client

        self._dict = {}  # Dictionary that is assigned

    def _assign(self, obj):
        self._objectIntegrity(obj)

        for key in obj:
            val = obj[key]
            if key in self._needs_decoding:
                val = json.JSONDecoder().decode(val)
            if key in self._types:
                setattr(self, key, self._types[key](self.client, val))
            elif key in self._array_types:
                setattr(self, key, [self._array_types[key](self.client, o) for o in val])
            else:
                setattr(self, key, val)

        self._dict = obj

    def _objectIntegrity(self, obj):
        for key in obj:
            if key in self._restricted_names:
                raise IntegrityError(f"{self.objType} object has key {key} found in _restricted_names. VRCpy needs an adjustment.")


class Avatar(BaseObject):
    objType = 'Avatar'

    def __init__(self, client, obj):
        super().__init__(client)

        self.name = None  # type: str
        self.description = None  # type: str
        self.version = None  # type: int
        self.releaseStatus = None  # type: str
        self.authorId = None  # type: str
        self.authorName = None  # type: str
        self.tags = []

        self._array_types.update({
            'unityPackages': UnityPackage,
        })

        self._assign(obj)

    def author(self):
        """
        Used to get author of the avatar
        :return: User object
        :rtype: User
        """
        resp = self.client.api.call(f'/users/{self.authorId}')
        return User(self.client, resp['data'])

    def favorite(self):
        """
        Used to favorite avatar
        :return: Favorite object
        :rtype: Favorite
        """
        resp = self.client.api.call('/favorites', 'POST', json={'type': types.FavoriteType.Avatar, 'favoriteId': self.id, 'tags': ['avatars1']})
        return Favorite(self.client, resp['data'])

    def select(self):
        """
        Selects this avatar to be used/worn
        """
        self.client.api.call(f'/avatars/{self.id}/select', 'PUT')


class LimitedUser(BaseObject):
    objType = 'LimitedUser'

    def __init__(self, client, obj=None):
        super().__init__(client)

        self.displayName = None  # type: str
        self.status = None  # type: str
        self.statusDescription = None  # type: str
        self.isFriend = None  # type: bool
        self.location = None  # type: Location
        self.instanceId = None  # type: Location

        self._types.update({
            'location': Location,
            'instanceId': Location,
        })

        if obj is not None:
            self._assign(obj)

    def fetch_full(self):
        """
        Used to get full version of this user
        :return: User object
        :rtype: User
        """
        resp = self.client.api.call(f'/users/{self.id}')
        return User(self.client, resp['data'])

    def public_avatars(self):
        """
        Used to get public avatars made by this user
        :return: list of Avatar objects
        :rtype: List[Avatar]
        """
        resp = self.client.api.call('/avatars', params={'userId': self.id})

        avatars = []
        for avatar in resp['data']:
            avatars.append(Avatar(self.client, avatar))

        return avatars

    def unfriend(self):
        """
        Used to unfriend this user
        """
        self.client.api.call(f'/auth/user/friends/{self.id}', 'DELETE')

    def friend(self):
        """
        Used to friend this user
        :return: Notification object
        :rtype: Notification
        """
        resp = self.client.api.call(f'/user/{self.id}/friendRequest', 'POST')
        return Notification(self.client, resp['data'])

    def favorite(self):
        """
        Used to favorite this user
        :return: Favorite object
        :rtype: Favorite
        """
        resp = self.client.api.call('/favorites', 'POST', params={'type': types.FavoriteType.Friend, 'favoriteId': self.id})
        return Favorite(self.client, resp['data'])


class User(LimitedUser):
    objType = 'User'

    def __init__(self, client, obj=None):
        super().__init__(client)

        self.state = None  # type: str
        self.allowAvatarCopying = None  # type: bool

        if obj is not None:
            self._assign(obj)


class CurrentUser(User):
    objType = 'CurrentUser'

    def __init__(self, client, obj):
        super().__init__(client)

        self.friends = []
        self.onlineFriends = []
        self.activeFriends = []
        self.offlineFriends = []

        self._types.update({
            'feature': Feature,
        })

        self._assign(obj)

    def fetch_full(self):
        return LimitedUser.fetch_full(self)

    def public_avatars(self):
        return LimitedUser.public_avatars(self)

    def unfriend(self):
        raise AttributeError("'CurrentUser' object has no attribute 'unfriend'")

    def friend(self):
        raise AttributeError("'CurrentUser' object has no attribute 'friend'")

    def avatars(self, releaseStatus=types.ReleaseStatus.All):
        """
        Used to get avatars by current user

        :param releaseStatus: One of types type.ReleaseStatus
        :type releaseStatus: str

        :return: list of Avatar objects
        :rtype: List[Avatar]
        """
        resp = self.client.api.call('/avatars', params={'releaseStatus': releaseStatus, 'user': 'me'})

        avatars = []
        for avatar in resp['data']:
            if avatar['authorId'] == self.id:
                avatars.append(Avatar(self.client, avatar))

        return avatars

    def update_info(self, email=None, status=None, statusDescription=None, bio=None, bioLinks=None):
        """
        Used to update current user info

        :param email: New email
        :type email: str

        :param status: New status
        :type status: str

        :param statusDescription: New website status
        :type statusDescription: str

        :param bio: New bio
        :type bio: str

        :param bioLinks: New links in bio
        :type bioLinks: List[str]

        :return: updated CurrentUser
        :rtype: CurrentUser
        """
        params = {'email': email, 'status': status, 'statusDescription': statusDescription, 'bio': bio, 'bioLinks': bioLinks}

        for p in params:
            if params[p] is None:
                params[p] = getattr(self, p)

        resp = self.client.api.call(f'/users/{self.id}', 'PUT', params=params)

        self.client.me = CurrentUser(self.client, resp['data'])
        return self.client.me

    def fetch_favorites(self, t, n=100):
        """
        Used to get favorites

        :param t: FavoriteType
        :type t: str

        :param n: Max number of favorites to return (Most that will ever return is 100)
        :type n: int

        :return: list of Favorite objects
        :rtype: List[Favorite]
        """
        resp = self.client.api.call('/favorites', params={'type': t, 'n': n})

        f = []
        for favorite in resp['data']:
            f.append(Favorite(self.client, favorite))

        return f

    def remove_favorite(self, favorite_id):
        """
        Used to remove a favorite via id

        :param favorite_id: ID of the favorite object
        :type favorite_id: str
        """
        self.client.api.call(f'/favorites/{favorite_id}', 'DELETE')

    def get_favorite(self, favorite_id):
        """
        Used to get favorite via id

        :param favorite_id: ID of the favorite object
        :type favorite_id: str

        :return: Favorite object
        :rtype: Favorite
        """
        resp = self.client.api.call(f'/favorites/{favorite_id}')
        return Favorite(self.client, resp)

    def favorite(self):
        raise AttributeError("'CurrentUser' object has no attribute 'favorite'")


class Feature(BaseObject):
    objType = 'Feature'

    def __init__(self, client, obj):
        super().__init__(client)

        self._assign(obj)


class PastDisplayName(BaseObject):
    objType = 'PastDisplayName'

    def __init__(self, client, obj):
        super().__init__(client)

        self.displayName = None  # type: str
        self.updated_at = None  # type: str

        self._assign(obj)


class LimitedWorld(BaseObject):
    objType = 'LimitedWorld'

    def __init__(self, client, obj=None):
        super().__init__(client)

        self.authorId = None  # type: str

        self._array_types.update({
            'unityPackages': UnityPackage,
        })

        if obj is not None:
            self._assign(obj)

    def author(self):
        """
        Used to get author of the world
        :return: User object
        :rtype: User
        """
        resp = self.client.api.call(f'/users/{self.authorId}')
        return User(self.client, resp['data'])

    def favorite(self):
        """
        Used to favorite this world object
        :return: Favorite object
        :rtype: Favorite
        """
        resp = self.client.api.call('/favorites', 'POST', params={'type': types.FavoriteType.World, 'favoriteId': self.id})
        return Favorite(self.client, resp['data'])

    def link(self):
        return f'https://vrchat.com/home/world/{self.id}'


class World(LimitedWorld):
    objType = 'World'

    def __init__(self, client, obj):
        super().__init__(client)

        self.name = None  # type: str
        self.description = None  # type: str
        self.authorName = None  # type: str
        self.releaseStatus = None  # type: str

        self._assign(obj)

    def fetch_instance(self, instance_id):
        """
        Used to get instance of this world via id

        :param instance_id: ID of instance
        :type instance_id: str

        :return: Instance object
        :rtype: Instance
        """
        resp = self.client.api.call(f'/instances/{self.id}:{instance_id}')
        return Instance(self.client, resp['data'])


class Location:
    objType = 'Location'

    def __init__(self, client, location):
        """
        :param client: Client object
        :type client: vrcpy.Client
        :param location: location string
        :type location: str
        """
        if not isinstance(location, str):
            raise TypeError(f"Expected string, got {type(location)}")

        self.nonce = None  # type: str
        self.type = 'public'  # type: str
        self.name = ''  # type: str
        self.worldId = None  # type: str
        self.userId = None  # type: str
        self.location = location  # type: str
        self.client = client

        if ':' in location:
            self.worldId, location = location.split(':')
        self.code = location

        try:
            if '~' in location:
                if location.count('~') == 2:
                    self.name, t, nonce = location.split('~')
                    self.type, self.userId = t[:-1].split('(')
                    self.nonce = nonce.split('(')[1][:-1]
                elif location.count('~') == 1:
                    self.name, self.type = location.split('~')  # Needs testing, https://github.com/vrchatapi/VRChatPython/issues/17
            else:
                self.name = location
        except Exception as e:  # https://github.com/vrchatapi/VRChatPython/issues/17
            raise GeneralError(f"Exception occured while trying to parse location string ({self.code})! Please open an issue on github! {e}")

    def fetch_world(self):
        return self.client.fetch_world(self.worldId)


class Instance(BaseObject):
    objType = 'Instance'

    def __init__(self, client, obj):
        super().__init__(client)

        self.worldId = None  # type: str
        self.location = None  # type: Location
        self.type = None  # type: str
        self.shortName = None  # type: str
        self.n_users = None  # type: int
        self.capacity = None  # type: int
        self.instanceId = None  # type: str
        self.name = None  # type: str

        self._types.update({
            'id': Location,
            'location': Location,
        })

        self._assign(obj)

    def world(self):
        """
        Used to get the world of this instance
        :return: World object
        :rtype: World
        """
        resp = self.client.api.call(f'/worlds/{self.worldId}')
        return World(self.client, resp['data'])

    def short_name(self):
        """
        Used to get shorturl of the instance
        :rtype: str
        """
        return f'https://vrchat.com/i/{self.shortName}'

    def join(self):
        """
        'Joins' the instance
        """
        self.client.api.call('/joins', 'PUT', json={'worldId': self.location.location})


class UnityPackage(BaseObject):
    objType = 'UnityPackage'

    def __init__(self, client, obj):
        super().__init__(client)

        self._assign(obj)


class Notification(BaseObject):
    objType = 'Notification'

    def __init__(self, client, obj):
        super().__init__(client)

        self.senderUserId = None  # type: str
        self.senderUsername = None  # type: str
        self.type = None  # type: str
        self.message = None  # type: str
        self.details = None  # type: str
        self.seen = None  # type: bool
        self.created_at = None  # type: str

        self._needs_decoding |= {
            'details',
        }
        self._types.update({
            'details': NotificationDetails,
        })

        self._assign(obj)

    def accept(self):
        return self.client.accept_notification(self.id)


class NotificationDetails(BaseObject):
    objType = 'NotificationDetails'

    def __init__(self, client, obj):
        super().__init__(client)

        # invite
        self.worldId = None  # type: str
        self.worldName = None  # type: str
        self.inviteMessage = None  # type: str

        # requestInvite
        self.requestMessage = None  # type: str

        self._types.update({
            'worldId': Location,
        })

        self._assign(obj)


class Favorite(BaseObject):
    objType = 'Favorite'

    def __init__(self, client, obj):
        super().__init__(client)

        self.type = None
        self.favoriteId = None

        self._assign(obj)
