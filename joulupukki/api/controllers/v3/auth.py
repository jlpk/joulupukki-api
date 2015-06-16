import httplib
from urlparse import urlparse, parse_qs
import urllib
import json

import pecan
import wsme.types as wtypes
import wsmeext.pecan as wsme_pecan
from pecan import rest

from joulupukki.common.datamodel.user import User
from joulupukki.api.libs import github
from joulupukki.api.libs import gitlab

class LoginController(rest.RestController):

    @wsme_pecan.wsexpose(unicode, unicode, unicode)
    def post(self, username, password=""):
        """Login using gitlab or github"""
        # Gitlab
        if username and password:
            return gitlab.login(username, password)
        # Github
        if username and password =="":
            return github.login(username)

        return none


class ActiveAuthController(rest.RestController):

    @wsme_pecan.wsexpose(wtypes.text)
    def get(self):
        """ Return active authentications
        Should be None, github ou gitlab
        """
        return {"result": {"active_auth": [pecan.conf.auth] }}

class AuthController(rest.RestController):

    login = LoginController()
    active = ActiveAuthController()

