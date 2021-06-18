
from time import sleep

import requests

from vrcpy.errors import (
    AlreadyFriendsError, GeneralError, IncorrectLoginError, InvalidTwoFactorAuth, NotFoundError, NotAuthenticated, NotFriendsError, OutOfDateError,
    RateLimitError, RequiresTwoFactorAuthError, MissingCredentials,
)


def raise_for_status(resp):
    def handle_400():
        if 'error' in resp['data']:
            if resp['data']['error']['message'] == 'These users are not friends':
                raise NotFriendsError("These users are not friends")
            elif resp['data']['error']['message'] == '"Users are already friends!"':
                raise AlreadyFriendsError("Users are already friends!")
        elif 'verified' in resp['data']:
            raise InvalidTwoFactorAuth("2FactorAuth code is invalid.")

    def handle_401():
        if 'requiresTwoFactorAuth' in resp['data']['error']['message'] or 'Requires Two-Factor Authentication' in resp['data']['error']['message']:
            raise RequiresTwoFactorAuthError("Account is 2FactorAuth protected.")
        elif 'Invalid Username or Password' in resp['data']['error']['message']:
            raise IncorrectLoginError(resp['data']['error']['message'])
        elif 'Missing Credentials' in resp['data']['error']['message']:
            raise MissingCredentials(resp['data']['error']['message'])
        else:
            raise NotAuthenticated(resp['data']['error']['message'])

    def handle_404():
        if isinstance(resp['data'], bytes):
            msg = str(resp['data'].decode()).split('"error":"')[1].split('","')[0]
        else:
            msg = resp['data']['error']['message']

        raise NotFoundError(msg)

    def handle_429():
        raise RateLimitError("You are being rate-limited.")

    def handle_502():
        raise requests.exceptions.ConnectionError("Bad Gateway.")

    def handle_503():
        try:
            raise requests.exceptions.ConnectionError(f"503 Service Temporarily Unavailable - {resp['data']['error']['message']}")
        except Exception:
            raise requests.exceptions.ConnectionError("503 Service Temporarily Unavailable")

    def handle_504():
        raise requests.exceptions.ConnectionError("Gateway Time-out.")

    switch = {
        400: handle_400,
        401: handle_401,
        404: handle_404,
        429: handle_429,
        502: handle_502,
        503: handle_503,
        504: handle_504,
    }

    if resp['status'] in switch:
        switch[resp['status']]()
    if resp['status'] != 200:
        raise GeneralError(f"Unhandled error occured: {resp['data']}")
    if 'requiresTwoFactorAuth' in resp['data']:
        raise RequiresTwoFactorAuthError("Account is 2FactorAuth protected.")


class Call:
    call_retries = 3
    retry_sleep = 10
    user_agent = 'vrcpy modified by ShingenPizza'

    def __init__(self, verify=True):
        self.verify = verify
        self.apiKey = None
        self.authenticated = False
        self.session = None

    def set_auth(self, auth):
        self.new_session()
        self._get_api_key_call()
        self.set_auth_cookie(auth)

    def set_auth_login(self, auth):
        self.new_session()
        self.set_auth_cookie(auth)

    def set_auth_cookie(self, auth):
        self.session.cookies.set('auth', auth)
        self.authenticated = True

    def new_session(self):
        self.session = requests.Session()
        self.authenticated = False

    def call(self, path, method='GET', headers=None, params=None, json=None, authenticate=False, verify=True, retries=None, retry_sleep=None):
        if headers is None:
            headers = {}
        if params is None:
            params = {}
        if json is None:
            json = {}
        headers.setdefault('User-Agent', self.user_agent)
        retries = retries or self.call_retries
        retry_sleep = retry_sleep or self.retry_sleep
        resp = None
        for attempt in range(retries + 1):
            try:
                if authenticate:
                    resp = self._auth_call(path, method=method, headers=headers, params=params, json=json, verify=verify)
                else:
                    resp = self._call(path, method=method, headers=headers, params=params, json=json, verify=verify)
                break
            # Gosh darnit VRC team, why've you done this!
            except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as e:
                if attempt >= retries:
                    raise requests.exceptions.ConnectionError(f"{e} ({retries} retries)")
                sleep(retry_sleep)

        return resp

    def _call(self, path, method='GET', headers=None, params=None, json=None, verify=True):
        if not self.authenticated:
            raise NotAuthenticated("Tried to do authenticated request without logging in or setting auth (Client.set_auth(auth))!")

        if self.apiKey is None:
            raise Exception("not known apiKey")

        if headers is None:
            headers = {}
        if params is None:
            params = {}
        if json is None:
            json = {}

        path = f'https://api.vrchat.cloud/api/1{path}'

        for param in params:
            if isinstance(params[param], bool):
                params[param] = str(params[param]).lower()

        params['apiKey'] = self.apiKey
        resp = self.session.request(method, path, headers=headers, params=params, json=json, verify=self.verify)

        try:
            resp_data = resp.json()
        except Exception:
            resp_data = resp.content

        resp = {'status': resp.status_code, 'response': resp, 'data': resp_data}

        if verify:
            raise_for_status(resp)
        return resp

    def _auth_call(self, path, method='GET', headers=None, params=None, json=None, verify=True):
        if self.apiKey:
            raise Exception("trying to auth while knowing apiKey")

        if headers is None:
            headers = {}
        if params is None:
            params = {}
        if json is None:
            json = {}

        self._get_api_key_call()

        path = f'https://api.vrchat.cloud/api/1{path}'

        for param in params:
            if isinstance(params[param], bool):
                params[param] = str(params[param]).lower()

        params['apiKey'] = self.apiKey
        resp = requests.request(method, path, headers=headers, params=params, data=json, verify=self.verify)

        try:
            resp_data = resp.json()
        except Exception:
            resp_data = resp.content

        resp = {'status': resp.status_code, 'response': resp, 'data': resp_data}

        if verify:
            raise_for_status(resp)
        return resp

    def _get_api_key_call(self):
        resp = requests.get('https://api.vrchat.cloud/api/1/config', headers={'User-Agent': self.user_agent}, verify=self.verify)
        if resp.status_code != 200:
            raise requests.exceptions.ConnectionError(f"_get_api_key_call() response code {resp.status_code}")

        j = resp.json()
        try:
            self.apiKey = j['apiKey']
        except Exception:
            raise OutOfDateError("This API wrapper is too outdated to function (https://api.vrchat.cloud/api/1/config doesn't contain apiKey)")
