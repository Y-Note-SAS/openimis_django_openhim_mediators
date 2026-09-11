import base64

import urllib3


class Auth:
    def __init__(self, options):
        self.options = options

    def authenticate(self):
        # The OpenHIM "token" authentication strategy is deprecated and only
        # works for accounts that have a token passport with a salt. The Core
        # API is authenticated with HTTP Basic auth (Core user email +
        # password), so no challenge/salt round-trip is needed here.
        if not self.options['verify_cert']:
            urllib3.disable_warnings(
                urllib3.exceptions.InsecureRequestWarning
            )
        return {}

    def gen_auth_headers(self):
        credentials = "{}:{}".format(
            self.options['username'],
            self.options['password'],
        )
        token = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        return {'Authorization': 'Basic {}'.format(token)}
