from pecan import expose, redirect
import wsmeext.pecan as wsme_pecan
import pecan
from pecan import rest, abort

import wsme.types as wtypes

from wsme.types import File


import zipfile
import tarfile

import glob
import os
import json
import uuid
import datetime
import shutil
import hmac
import hashlib

from io import BytesIO
from joulupukki.common.datamodel.build import Build, APIBuild
from joulupukki.common.datamodel.user import User
from joulupukki.common.datamodel.project import Project
from joulupukki.common.datamodel.job import Job
from joulupukki.api.controllers.v3.jobs import JobsController
from joulupukki.api.controllers.v3.download import DownloadController, OutputController
from joulupukki.common.carrier import Carrier



from joulupukki.common.distros import supported_distros, reverse_supported_distros



class BuildController(rest.RestController):
    def __init__(self, build_id=None):
        pecan.request.context['build_id'] = build_id
        self.id_ = build_id

    # curl -X GET http://127.0.0.1:8080/v1/builds/c1afd1d8-17ee-4858-8dd1-964cb065d141/
    @wsme_pecan.wsexpose(Build)
    def get(self):
        """Returns build status"""
        user = User.fetch(pecan.request.context['username'], sub_objects=False)
        if user is None:
            return None
        project_name = pecan.request.context['project_name']
        project = Project.fetch(user, project_name, sub_objects=False)
        if project is None:
            return None
        build_id = self.id_
        if self.id_ in ["latest"]:
            build_id = project.get_latest_build_id()
        build = Build.fetch(project, build_id, sub_objects=True)
        if build:
           return build
        return None

    # curl -X DELETE http://127.0.0.1:8080/v1/builds/c1afd1d8-17ee-4858-8dd1-964cb065d141/
    @pecan.expose()
    def delete(self):
        """Delete build and build folder"""
        build = get_build(self._id)
        if os.path.exists(os.path.join(pecan.conf.builds_path, self._id)):
            shutil.rmtree(os.path.join(pecan.conf.builds_path, self._id))
            return "Deleted"
        return "Doesn't exist"


    @pecan.expose()
    def _lookup(self, *remainder):
         return BuildSubController(), remainder





class BuildsController(rest.RestController):

    #curl -X GET  http://127.0.0.1:8080/v3/titilambert/myproject/builds/
    @wsme_pecan.wsexpose([Build])
    def get_all(self):
        """Returns all builds."""
        project_name = pecan.request.context['project_name']
        user = User.fetch(pecan.request.context['username'], sub_objects=False)
        if user is None:
            return user
        project = Project.fetch(user, project_name, sub_objects=False)
        if project is None:
            return None
        return project.get_builds()

    @pecan.expose()
    def _lookup(self, build_id, *remainder):
        return BuildController(build_id), remainder



class BuildSubController(rest.RestController):
    download = DownloadController()
    jobs = JobsController()
    output = OutputController()



class LaunchBuildController(rest.RestController):
    # curl -X POST -H "Content-Type: application/json" -i  -d '{"source_url": "/home/tcohen/projet_communautaire/kaji/meta/packages/shinken", "source_type": "local", "branch": "kaji"}' http://127.0.0.1:8080/v3/titilambert/shinken/build
    # curl -X POST -H "Content-Type: application/json" -i  -d '{"source_url": "/home/tcohen/projet_communautaire/kaji/meta/packages/shinken", "source_type": "local", "branch": "kaji", "forced_distro": "centos_7"}' http://127.0.0.1:8080/v3/titilambert/shinken/build
    # curl -X POST -H "Content-Type: application/json" -i  -d '{"source_url": "https://github.com/kaji-project/kaji.git", "source_type": "git", "branch": "kaji", "forced_distro": "centos_7", "snapshot": true}' http://127.0.0.1:8080/v3/titilambert/kaji/build
    @wsme_pecan.wsexpose(wtypes.text, body=APIBuild, status_code=201)
    def post(self, send_build):
        """ launch build """
        project_name = pecan.request.context['project_name']
        user = User.fetch(pecan.request.context['username'])
        project = Project.fetch(user.username, project_name)

        if project is None:
            # The project doesn't exist
            # We have to create it
            # TODO Maybe it's better to force users to create project before
            # they can create builds
            sent_project = {"name": project_name, "username": user.username}
            project = Project(sent_project, sub_objects=False)
            if not project.create():
                # Handle error
                return {"result": "Error creating %s project" % project_name}

        build = Build(send_build)
        build.username = user.username
        build.project_name = project.name
        build.create()
        carrier = Carrier(pecan.conf.rabbit_server, pecan.conf.rabbit_port,
                          pecan.conf.rabbit_db)
        carrier.declare_queue('builds.queue')
        # carrier.declare_builds()
        if not carrier.send_message(build.dumps(), 'builds.queue'):
            return None
        return {"result": {"build": int(build.id_)}}

class LaunchBuildGithubController(rest.RestController):
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
            carrier = Carrier(pecan.conf.rabbit_server, pecan.conf.rabbit_port,
                              pecan.conf.rabbit_db)
            carrier.declare_queue('builds.queue')
            # carrier.declare_builds()
            if not carrier.send_message(build.dumps(), 'builds.queue'):
                return None
            return {"result": {"build": int(build.id_)}}

        abort(403)
