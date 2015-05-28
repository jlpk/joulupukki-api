import httplib
from urlparse import urlparse, parse_qs
import urllib
import json

import pecan

from joulupukki.common.datamodel.user import User
from joulupukki.common.datamodel.project import Project

def login(username, password):
    """ Get username and access token from github """
    gitlab_userdata = get_access_token(username, password)
    if gitlab_userdata is None:
        return None
    access_token = gitlab_userdata.get('private_token')

    if access_token:
        # Check if this user exists in DB
        # if not we need to create it
        user = User.fetch_from_gitlab_token(access_token)
        # Save this new user
        if user is None:
            user = User({"username": gitlab_userdata['username'],
                         "name": gitlab_userdata['name'],
    #                         "gitlab_url": data['html_url'],
                         "email": gitlab_userdata['email'],
                         "token_gitlab": access_token,
                         "id_gitlab": gitlab_userdata['id'],
                         })
            if not user.create():
                return None

        update_user_info_from_gitlab(user.username, user.token_gitlab)
        return {"access_token": access_token,
                "username": user.username}
    return None




def get_access_token(username, password):

    url = pecan.conf.gitlab_url

    # Handle https and http
    if gitlab_secure:
        conn = httplib.HTTPSConnection(url)
    else:
        conn = httplib.HTTPConnection(url)

    params = urllib.urlencode({"login": username,
                               "password": password
                              })
    conn.request("POST", "/api/v3/session", params)
    response = conn.getresponse()
    data = json.load(response)
    access_token = data.get("private_token")

    if access_token is not None:
        return data
    return None


def get_user_from_token(access_token):
    # FIXME for gitlab
    url = pecan.conf.gitlab_url
    # Handle https and http
    if gitlab_secure:
        conn = httplib.HTTPSConnection(url)
    else:
        conn = httplib.HTTPConnection(url)

    headers = {}
    headers['Authorization'] = "token " + access_token
    params = urllib.urlencode({
                               "client_id": pecan.conf.github_id,
                               "client_secret": pecan.conf.github_secret,
                              })

    conn.request("GET", "/api/v3/user", params, headers)
    response = conn.getresponse()
    return json.loads(response.read())


def get_user(user_id, access_token):
    url = pecan.conf.gitlab_url

    # Handle https and http
    if gitlab_secure:
        conn = httplib.HTTPSConnection(url)
    else:
        conn = httplib.HTTPConnection(url)

    params = urllib.urlencode({
                               "private_token": access_token
                              })
    url = "/api/v3/users/" + str(user_id) + "?" + params
    conn.request("GET", url)
    response = conn.getresponse()
    if response.status >= 400:
        return None
    return json.load(response)

def get_group(group_name, access_token):
    url = pecan.conf.gitlab_url

    # Handle https and http
    if gitlab_secure:
        conn = httplib.HTTPSConnection(url)
    else:
        conn = httplib.HTTPConnection(url)

    params = urllib.urlencode({
                               "private_token": access_token
                              })
    url = "/api/v3/groups/" + group_name + "?" + params
    conn.request("GET", url)
    response = conn.getresponse()
    if response.status >= 400:
        return None
    return json.load(response)


def get_user_repos(user_id, access_token):
    url = pecan.conf.gitlab_url

    # Handle https and http
    if gitlab_secure:
        conn = httplib.HTTPSConnection(url)
    else:
        conn = httplib.HTTPConnection(url)

    params = urllib.urlencode({
                               "private_token": access_token
                              })
    url = "/api/v3/projects?" + params
    conn.request("GET", url)
    response = conn.getresponse()
    repos = json.load(response)
    repos = [r for r in repos if r.get('namespace').get('id') == user_id]
    return repos


def get_group_repos(group_id, access_token):
    url = pecan.conf.gitlab_url

    # Handle https and http
    if gitlab_secure:
        conn = httplib.HTTPSConnection(url)
    else:
        conn = httplib.HTTPConnection(url)

    params = urllib.urlencode({
                               "private_token": access_token
                              })
    url = "/api/v3/groups/" + str(group_id) + "?" + params
    conn.request("GET", url)
    response = conn.getresponse()
    group = json.load(response)
    return group.get('projects')



def get_user_orgs(user_id, access_token):
    
    url = pecan.conf.gitlab_url

    # Handle https and http
    if gitlab_secure:
        conn = httplib.HTTPSConnection(url)
    else:
        conn = httplib.HTTPConnection(url)

    params = urllib.urlencode({
                               "private_token": access_token
                              })
    url = "/api/v3/groups?" + params
    conn.request("GET", url)
    response = conn.getresponse()
    groups = json.load(response)
    # FIXME filter group with user_id (is this user member?)
    return groups




def update_user_info_from_gitlab(username, access_token):
    user = User.fetch(username, with_password=False)
    # TODO handle better access
#    user = User.fetch_from_github_token(access_token)
#    if user is None or user.username != username:
#        return False
    # Get data from github
    gl_user = get_user(user.id_gitlab, access_token)
    gl_repos = get_user_repos(user.id_gitlab, access_token)
    gl_orgs = get_user_orgs(username, access_token)

    # Update user data
    user.email = gl_user['email']
    #user.github_url = gh_user['html_url']
    user.name = gl_user['name']
    user.orgs = [org['name'] for org in gl_orgs]
    # Update repos and create it if not exists
    for repo in gl_repos:
        project = Project.fetch(user.username, repo['name'])
        if project is None:
            project = Project({"name": repo['name'],
                               "description": repo['description'],
                               "username": user.username,
                               "enabled": False,
                               "gitlab_project_id": repo['id'],
                               "url": repo['web_url'],
                               })
            project.create()
        # TODO get Project status (webhook) (enable) from gitlab
        # Save project
        project.update()
    # Update user orgs
    user._save()
    return True



def update_group_info_from_gitlab(group, access_token):
    # TODO handle better access
#    user = User.fetch_from_github_token(access_token)
#    if user is None or user.username != username:
#        return False
    # Get data from gitlab
    gl_repos = get_group_repos(group.id_gitlab, access_token)

    # Update repos and create it if not exists
    for repo in gl_repos:
        project = Project.fetch(group.username, repo['name'])
        if project is None:
            project = Project({"name": repo['name'],
                               "description": repo['description'],
                               "username": group.username,
                               "enabled": False,
                               "gitlab_project_id": repo['id'],
                               "url": repo['web_url'],
                               })
            project.create()
        # TODO get Project status (enable) from gitlab
        # Save project
        project.update()
    return True


def toggle_project_webhook(user, project, access_token):
    # TODO put in confg
    webhook_url = pecan.conf.api_url + "/v3/externalservice/build"
    webhook_url += "?token=" + project.token
    
    url = pecan.conf.gitlab_url
    # Get webhook
    # Handle https and http
    if gitlab_secure:
        conn = httplib.HTTPSConnection(url)
    else:
        conn = httplib.HTTPConnection(url)

    auth_params = urllib.urlencode({
                               "private_token": access_token
                              })
    url = "/".join(("/api/v3/projects", str(project.gitlab_project_id), "hooks"))
    url += "?" + auth_params
    conn.request("GET", url)
#    conn.request("GET", url)
    response = conn.getresponse()
    hooks = json.load(response)

    new_state = True
    hook_id = None
    if response.status >= 400:
        return None
    for hook in hooks:
        if hook.get('id') == project.gitlab_hook_id:
            new_state = False
            hook_id = str(hook.get('id'))
    # Prepare params
    params = urllib.urlencode({
              "id": project.gitlab_project_id,
              "url": webhook_url,
              "push_events": 1,
              "issues_events": 0,
              "merge_requests_events": 0,
              "tag_push_events": 1,
              "private_token": access_token,
              })
    # Set url depending of create/update
    if hook_id is None:
        # CREATING Webhook
        url = "/".join(("/api/v3/projects", str(project.gitlab_project_id), "hooks"))
        url += "?" + auth_params
        conn.request("POST", url, params)
    else:
        # DELETING Webhook
        url = "/".join(("/api/v3/projects", str(project.gitlab_project_id), "hooks", hook_id))
        url += "?" + auth_params
        conn.request("DELETE", url)
    # Create/Update webhook
    response = conn.getresponse()
    data = json.load(response)

    if response.status >= 400:
        return None
    # Save project on mongodb
    project.enabled = new_state
    project.gitlab_hook_id = data.get("id")
    project.update()

    return new_state

