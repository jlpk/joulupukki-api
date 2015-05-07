from pecan import expose
import pecan
from pecan import rest, abort

import hmac
import hashlib

from joulupukki.common.datamodel.build import Build
from joulupukki.common.datamodel.user import User
from joulupukki.common.datamodel.project import Project
from joulupukki.common.carrier import Carrier





class WebhookBuildController(rest.RestController):
    @expose()
    def post(self):
        """ launch build  from github webhook"""
        body = pecan.request.json
        # Get user
        if not body.get('sender'):
            abort(403)

        user = User.fetch(body.get('sender').get('login'))
        if user is None:
            abort(403)
        # Check signature
        signature = pecan.request.headers.get('X-Hub-Signature')
        sha_name, signature = signature.split("=")
        if sha_name != 'sha1':
            abort(403)
        mac = hmac.new(user.token.encode("utf-8"), pecan.request.text, digestmod=hashlib.sha1)
        if not hmac.compare_digest(mac.hexdigest(), signature):
            abort(403)

        if pecan.request.headers.get('X-Github-Event') == 'ping':
            return {"result": True , "event": "ping"}

        if pecan.request.headers.get('X-Github-Event') == 'push':
            if not body.get('repository'):
                abort(403)
            repository = body.get('repository')
            project_name = repository.get('name')
            if not project_name:
                abort(403)

            project = Project.fetch(user.username, project_name)
            if project is None:
                # Error project doesn't exits
                # Maybe We should create it
                return {"result": False , "error": "project not found"}
            new_build = {"source_url": repository.get('clone_url'),
                         "source_type": "github",
                         "commit": repository.get('commit'),
                         # TODO Find how decide if is a snapshot or not
                         "snapshot": True,
                         # TODO Check if branch ~= ref
                         "branch": repository.get('ref'),
                         }
            build = Build(send_build)
            build.username = user.username
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
            return {"result": {"build": int(build.id_)}}

        abort(403)
