import base64
from typing import List
import urllib.parse

from vrcpy import objects
from vrcpy.errors import AlreadyLoggedInError
from vrcpy.request import Call


class Client:
    """
    Main client interface for VRC
    """

    def __init__(self, verify=True):
        """
        :param verify: If should verify ssl certificates on requests
        :type verify: bool
        """
        self.api = Call(verify)
        self.loggedIn = False
        self.me = None  # type: objects.CurrentUser

        self.needsVerification = False
        self.log_to_console = False

    def login(self, username=None, password=None, b64=None):
        """
        Used to initialize the client for use

        :param username: Username of VRC account
        :type username: str

        :param password: Password of VRC account
        :type password: str
        """
        if self.loggedIn:
            raise AlreadyLoggedInError("Client is already logged in")

        if b64 is None:
            if username is None or password is None:
                raise Exception("You have to provide either username and password directly, or a base64-encoded auth 'token'.")
            b64 = base64.b64encode(f'{username}:{password}'.encode()).decode()
        elif username is not None or password is not None:
            raise Exception("You have to provide either username and password directly, or a base64-encoded auth 'token'.")

        resp = self.api.call('/auth/user', headers={'Authorization': f'Basic {b64}'}, no_auth=True)

        self.api.set_auth(b64)
        self.api.session.cookies.set('auth', resp['response'].cookies['auth'])

        self.me = objects.CurrentUser(self, resp['data'])
        self.loggedIn = True

    def logout(self):
        """
        Closes client session, invalidates auth cookie
        """
        self.api.call('/logout', 'PUT')
        self.api.new_session()
        self.loggedIn = False

    def fetch_me(self):
        """
        Used to refresh client.me

        :return: CurrentUser object
        :rtype: objects.CurrentUser
        """
        resp = self.api.call('/auth/user')
        self.me = objects.CurrentUser(self, resp['data'])
        return self.me

    def fetch_friends(self, offline=False, n=0, offset=0):
        """
        Used to get friends of current user

        :param offline: Get offline friends instead of online friends
        :type offline: bool

        :param n: Number of friends to return (0 for all)
        :type n: int

        :param offset: Skip first <offset> friends
        :type offset: int

        :return: list of LimitedUser objects
        :rtype: List[objects.LimitedUser]
        """
        friends = []

        while True:
            newn = 100
            if n and n - len(friends) < 100:
                newn = n - len(friends)

            resp = self.api.call('/auth/user/friends', params={'offset': offset, 'offline': offline, 'n': newn})

            friends += [objects.LimitedUser(self, friend) for friend in resp['data']]

            if len(resp['data']) < 100:
                break

            offset += 100

        return friends

    def fetch_full_friends(self, offline=False, n=0, offset=0):
        """
        Used to get friends of current user
        !! This function uses possibly lot of calls, use with caution

        :param offline: Get offline friends instead of online friends
        :type offline: bool

        :param n: Number of friends to return (0 for all)
        :type n: int

        :param offset: Skip first <offset> friends
        :type offset: int

        :return: list of User objects
        :rtype: List[objects.User]
        """
        lfriends = self.fetch_friends(offline=offline, n=n, offset=offset)
        friends = []

        # Get friends
        for friend in lfriends:
            friends.append(friend.fetch_full())

        return friends

    def fetch_user_by_id(self, user_id):
        """
        Used to get a user via id

        :param user_id: UserId of the user
        :type user_id: str

        :return: User object
        :rtype: objects.User
        """
        resp = self.api.call(f'/users/{user_id}')
        return objects.User(self, resp['data'])

    def fetch_user_by_name(self, name):
        """
        Used to get a user via name

        :param name: Name of the user
        :type name: str

        :return: User object
        :rtype: objects.User
        """
        resp = self.api.call(f'/users/{urllib.parse.quote_plus(name)}/name')
        return objects.User(self, resp['data'])

    def fetch_avatar(self, avatar_id):
        """
        Used to get avatar via id

        :param avatar_id: AvatarId of the avatar
        :type avatar_id: str

        :return: Avatar object
        :rtype: objects.Avatar
        """
        resp = self.api.call(f'/avatars/{avatar_id}')
        return objects.Avatar(self, resp['data'])

    def list_avatars(self, user=None, featured=None, tag=None, userId=None, n=None, offset=None, order=None, releaseStatus=None, sort=None,
                     maxUnityVersion=None, minUnityVersion=None, maxAssetVersion=None, minAssetVersion=None, platform=None):
        """
        Used to get list of avatars

        :param user: Type of user (me, friends)
        :type user: str

        :param featured: If the avatars are featured
        :type featured: bool

        :param tag: List of tags the avatars have
        :type tag: str list

        :param userId: ID of the user that made the avatars
        :type userId: str

        :param n: Number of avatars to return
        :type n: int

        :param offset: Skip first <offset> avatars
        :type offset: int

        :param order: Sort <sort> by "descending" or "ascending" order
        :type order: str

        :param releaseStatus: ReleaseStatus of avatars
        :type releaseStatus: str

        :param sort: Sort by "created", "updated", "order", "_created_at", "_updated_at"
        :type sort: str

        :param maxUnityVersion: Max version of unity the avatars were uploaded from
        :type maxUnityVersion: str

        :param minUnityVersion: Min version of unity the avatars were uploaded from
        :type minUnityVersion: str

        :param maxAssetVersion: Max of 'asset version' of the avatars
        :type maxAssetVersion: str

        :param minAssetVersion: Min of 'asset version' of the avatars
        :type minAssetVersion: str

        :param platform: Unity platform avatars were uploaded from
        :type platform: str

        :return: list of Avatar objects
        :rtype: List[objects.Avatar]
        """
        p = {}

        if user:
            p['user'] = user
        if featured:
            p['featured'] = featured
        if tag:
            p['tag'] = tag
        if userId:
            p['userId'] = userId
        if n:
            p['n'] = n
        if offset:
            p['offset'] = offset
        if order:
            p['order'] = order
        if releaseStatus:
            p['releaseStatus'] = releaseStatus
        if sort:
            p['sort'] = sort
        if maxUnityVersion:
            p['maxUnityVersion'] = maxUnityVersion
        if minUnityVersion:
            p['minUnityVersion'] = minUnityVersion
        if maxAssetVersion:
            p['maxAssetVersion'] = maxAssetVersion
        if minAssetVersion:
            p['minAssetVersion'] = minAssetVersion
        if platform:
            p['platform'] = platform

        resp = self.api.call('/avatars', params=p)

        avatars = []
        for avatar in resp['data']:
            avatars.append(objects.Avatar(self, avatar))

        return avatars

    def fetch_world(self, world_id):
        """
        Used to get world via id

        :param world_id: ID of the world
        :type world_id: str

        :return: World object
        :rtype: objects.World
        """
        resp = self.api.call(f'/worlds/{world_id}')
        return objects.World(self, resp['data'])

    def fetch_notifications(self):
        """
        Used to get notifications

        :return: list of Notification objects
        :rtype: List[objects.Notification]
        """
        resp = self.api.call('/auth/user/notifications')
        return [objects.Notification(self, n) for n in resp['data']]
