import httplib
from urlparse import urlparse, parse_qs
import urllib
import json

import pecan
import wsmeext.pecan as wsme_pecan
from pecan import rest

from joulupukki.common.datamodel.user import User
from joulupukki.api.libs import github
from joulupukki.api.libs import gitlab

class LoginController(rest.RestController):

    @wsme_pecan.wsexpose(unicode, unicode)
    def post(self, code):
        # Github
        return github.login(code)

    @wsme_pecan.wsexpose(unicode, unicode, unicode)
    def post(self, username, password):
        # Gitlab
        if username and password:
            return gitlab.login(username, password)
        return none


class AuthController(rest.RestController):

    login = LoginController()


