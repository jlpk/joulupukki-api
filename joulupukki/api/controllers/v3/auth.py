import httplib
from urlparse import urlparse, parse_qs
import urllib
import json

import pecan
import wsmeext.pecan as wsme_pecan
from pecan import rest

from joulupukki.common.datamodel.user import User
from joulupukki.api.libs import github

class LoginController(rest.RestController):

    @wsme_pecan.wsexpose(unicode, unicode)
    def post(self, code):
        # Github or gitlab
        return github.login(code)


class AuthController(rest.RestController):

    login = LoginController()


