import json as jsondecoder

import requests

from vrcpy.errors import (
    AlreadyFriendsError, GeneralError, IncorrectLoginError, InvalidTwoFactorAuth, NotFoundError, NotAuthenticated, NotFriendsError, OutOfDateError,
    RateLimitError, RequiresTwoFactorAuthError,
)


def raise_for_status(resp):
    if isinstance(resp['data'], bytes):
        resp['data'] = jsondecoder.loads(resp['data'].decode())

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

    def handle_404():
        if isinstance(resp['data'], bytes):
            try:
                msg = jsondecoder.loads(resp['data'].decode())['error']
            except Exception:
                msg = str(resp['data'].decode()).split('"error":"')[1].split('","')[0]
        else:
            msg = resp['data']['error']['message']

        raise NotFoundError(msg)

    def handle_429():
        raise RateLimitError("You are being rate-limited.")

    switch = {
        400: handle_400,
        401: handle_401,
        404: handle_404,
        429: handle_429,
    }

    if resp['status'] in switch:
        switch[resp['status']]()
    if resp['status'] != 200:
        raise GeneralError(f"Unhandled error occured: {resp['data']}")
    if 'requiresTwoFactorAuth' in resp['data']:
        raise RequiresTwoFactorAuthError("Account is 2FactorAuth protected.")


class Call:
    call_retries = 1

    def __init__(self, verify=True):
        self.verify = verify
        self.apiKey = None
        self.b64_auth = None
        self.session = None

    def set_auth(self, b64_auth):
        self.new_session()
        # Assume good b64_auth
        self.b64_auth = b64_auth

    def new_session(self):
        self.session = requests.Session()
        self.b64_auth = None

    def call(self, path, method='GET', headers=None, params=None, json=None, no_auth=False, verify=True, retries=None):
        if headers is None:
            headers = {}
        if params is None:
            params = {}
        if json is None:
            json = {}
        resp = None
        for tri in range(0, (retries or self.call_retries) + 1):
            try:
                resp = self._call_wrap(path, method, headers, params, json, no_auth, verify)
                break
            # Gosh darnit VRC team, why've you done this!
            except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as e:
                if tri == (retries or self.call_retries):
                    raise requests.exceptions.ConnectionError(f"{e} ({retries} retries)")

        return resp

    def _call_wrap(self, path, method='GET', headers=None, params=None, json=None, no_auth=False, verify=True):
        if headers is None:
            headers = {}
        if params is None:
            params = {}
        if json is None:
            json = {}
        headers['user-agent'] = ''

        if no_auth:
            return self._call(path, method, headers, params, json, verify)

        if self.b64_auth is None:
            raise NotAuthenticated("Tried to do authenticated request without setting b64 auth (Call.set_auth(b64_auth))!")
        headers['Authorization'] = f'Basic {self.b64_auth}'

        if self.apiKey is None:
            resp = self.session.get('https://api.vrchat.cloud/api/1/config', verify=self.verify)
            assert resp.status_code == 200

            j = resp.json()
            try:
                self.apiKey = j['apiKey']
            except Exception:
                raise OutOfDateError("This API wrapper is too outdated to function (https://api.vrchat.cloud/api/1/config doesn't contain apiKey)")

        path = f'https://api.vrchat.cloud/api/1{path}'

        for param in params:
            if isinstance(params[param], bool):
                params[param] = str(params[param]).lower()

        params['apiKey'] = self.apiKey
        resp = self.session.request(method, path, headers=headers, params=params, json=json, verify=self.verify)

        if resp.status_code != 200:
            try:
                json = resp.json()
            except Exception:
                json = None

            resp = {'status': resp.status_code, 'response': resp, 'data': json if json is not None else resp.content}

            if verify:
                raise_for_status(resp)
            return resp

        resp = {'status': resp.status_code, 'response': resp, 'data': resp.json()}

        if verify:
            raise_for_status(resp)
        return resp

    def _call(self, path, method='GET', headers=None, params=None, json=None, verify=True):
        if headers is None:
            headers = {}
        if params is None:
            params = {}
        if json is None:
            json = {}
        if self.apiKey is None:
            resp = requests.get('https://api.vrchat.cloud/api/1/config', headers=headers, verify=self.verify)
            assert resp.status_code == 200

            j = resp.json()
            try:
                self.apiKey = j['apiKey']
            except Exception:
                raise OutOfDateError("This API wrapper is too outdated to function (https://api.vrchat.cloud/api/1/config doesn't contain apiKey)")

        path = f'https://api.vrchat.cloud/api/1{path}'

        for param in params:
            if isinstance(params[param], bool):
                params[param] = str(params[param]).lower()

        params['apiKey'] = self.apiKey
        resp = requests.request(method, path, headers=headers, params=params, data=json, verify=self.verify)

        if resp.status_code != 200:
            try:
                json = resp.json()
            except Exception:
                json = None

            resp = {'status': resp.status_code, 'response': resp, 'data': json if json is not None else resp.content}

            if verify:
                raise_for_status(resp)
            return resp

        resp = {'status': resp.status_code, 'response': resp, 'data': resp.json()}

        if verify:
            raise_for_status(resp)
        return resp
