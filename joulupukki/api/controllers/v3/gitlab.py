from pecan import expose
import pecan
from pecan import rest, abort

import hmac
import json
import hashlib

from joulupukki.common.datamodel.build import Build
from joulupukki.common.datamodel.user import User
from joulupukki.common.datamodel.project import Project
from joulupukki.common.carrier import Carrier
from joulupukki.api.libs import gitlab




class WebhookBuildController(rest.RestController):
    @expose()
    def post(self):
        """ launch build from gitlab webhook"""
        body = pecan.request.json
        # Get use
        if not body.get('user_id'):
            abort(403)

        # Get token
        token = pecan.request.GET.get('token')
        if token is None:
            abort(403)

        # Get project
        project = Project.fetch_from_token(token, False)
        if project is None:
            abort(403)
        if body.get('project_id') != project.gitlab_project_id:
            abort(403)

        if body.get('object_kind') not in ['push', 'tag']:
            abort(403)

        else:
            # If it's a TAG event we DON'T make snaphot
            snapshot = False
            if body.get('object_kind') == 'push':
                # If it's a PUSH event we make snapshot
                snapshot = True

            if not body.get('repository'):
                abort(403)
            repository = body.get('repository')
            project_name = repository.get('name')
            if project_name != project.name:
                abort(403)

            new_build = {"source_url": repository.get('git_http_url'),
                         "source_type": "gitlab",
                         "commit": body.get('after'),
                         # TODO Find how decide if is a snapshot or not
                         "snapshot": snapshot,
                         # TODO Check if branch ~= ref
                         "branch": body.get('ref'),
                         }
            build = Build(new_build)
            build.username = project.username
            build.project_name = project.name
            build.create()
            carrier = Carrier(
                pecan.conf.rabbit_server,
                pecan.conf.rabbit_port,
                pecan.conf.rabbit_user,
                pecan.conf.rabbit_password,
                pecan.conf.rabbit_vhost,
                pecan.conf.rabbit_db
            )
            carrier.declare_queue('builds.queue')
            # carrier.declare_builds()
            if not carrier.send_message(build.dumps(), 'builds.queue'):
                return None
            return json.dumps({"result": True, "build": int(build.id_)})

        abort(403)


class SyncReposController(rest.RestController):
    @expose()
    def get(self, username):
        """ launch build  from gitlab webhook"""
        access_token = pecan.request.GET.get('access_token')
        if access_token:
            # Check if this user exists in DB
            user = User.fetch(username)
            if user is None:
                # This user maybe a group
                data = gitlab.get_group(username, access_token)
                if data is not None:
                    url = "http://%s/groups/%s" % (pecan.conf.gitlab_url, 
                                                   data['name'])
                    # Save this new group
                    user = User({"username": data['name'],
                                 "name": data['name'],
                                 "gitlab_url": url,
                                 "gitlab_group": True,
                                 "id_gitlab": data['id'],
                                 })
                if not user.create():
                    return None
                else:
                    # if user doesn't exists and this is not a group
                    # This request is strange so 403
                    abort(403)
            else:
                # if not we need to create it
                gitlab_user = gitlab.get_user(user.id_gitlab, access_token)
                # Update user info
                # TODO Disabled for now
#                if gitlab_user:
#                    user.name = gitlab_user.get('name')
#                    user.email = gitlab_user.get('email')
#                    if not user.update():
#                        return None
            if user.gitlab_group:
                return gitlab.update_group_info_from_gitlab(user, access_token)
            else:
                return gitlab.update_user_info_from_gitlab(username, access_token)
        return None

class SyncOrgsController(rest.RestController):
    @expose()
    def get(self, username):
        access_token = pecan.request.GET.get('access_token')
        if access_token:
            gitlab.update_user_info_from_gitlab(username, access_token)
        return None

class ExternalServiceController(rest.RestController):
    build = WebhookBuildController()
    syncuserrepos = SyncReposController()
    syncuserorgs = SyncOrgsController()
