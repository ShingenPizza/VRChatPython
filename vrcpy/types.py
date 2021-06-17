class ReleaseStatus:
    Public = 'public'
    Private = 'private'
    Hidden = 'hidden'
    All = 'all'

    @staticmethod
    def check(rs):
        if rs in {'public', 'private', 'hidden', 'all'}:
            return True
        return False


class State:
    Online = 'online'
    Active = 'active'
    Offline = 'offline'

    @staticmethod
    def check(rs):
        if rs in {'online', 'active', 'offline'}:
            return True
        return False


class Status:
    Active = 'active'
    Join = 'join me'
    Ask = 'ask me'
    Busy = 'busy'
    Offline = 'offline'

    @staticmethod
    def check(rs):
        if rs in {'active', 'join me', 'ask me', 'busy', 'offline'}:
            return True
        return False


class DeveloperType:
    Null = 'none'
    Trusted = 'trusted'
    Developer = 'internal'
    Moderator = 'moderator'

    @staticmethod
    def check(rs):
        if rs in {'none', 'trusted', 'internal', 'moderator'}:
            return True
        return False


class InstanceType:
    Hidden = 'hidden'
    Friends = 'friends'
    Public = ''

    @staticmethod
    def check(rs):
        if rs in {'hidden', 'friends', ''}:
            return True
        return False


class NotificationType:
    FriendRequest = 'friendRequest'

    @staticmethod
    def check(rs):
        if rs in {'friendRequest'}:
            return True
        return False


class FavoriteType:
    World = 'world'
    Friend = 'friend'
    Avatar = 'avatar'

    @staticmethod
    def check(rs):
        if rs in {'world', 'friend', 'avatar'}:
            return True
        return False


class Region:
    US = 'us'
    EU = 'eu'
    JP = 'jp'

    @staticmethod
    def check(val):
        return val in {Region.US, Region.EU, Region.JP}
