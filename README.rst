==========
Joulupukki
==========



Joulupukki is a generic system to build and distribute packages from sources.

LICENCE AGPLv3



Installation
============



Install before joulupukki-common

After

::

  pip install -r requirements.txt
  python setup.py develop




Run it
======



How to use it
=============




Testing
=======



You may run all tests with ``tox`` or run the tests with a specific interpreter with ``tox -epy27``.

.. note:: Maybe you need to install tox: ``pip instal tox``

Documentation
=============

You can build the documentation ``tox -edocs``. The HTML documentation will be built in ``docs/build/html``.


Dev Env
=======

::

  apt-get install rpm
  virtualenv --system-site-packages env
  
  
Usage
=====

Syntax ::

  curl -s -X POST -H "Content-Type: application/json" -i  -d '{ "source_url": "GIT URL OR PATH", "source_type": "[git|local]", "branch": "BRANCHNAME", ["snapshot": "true|false"], ["forced_distro": "DISTRO"]}' http://SERVERURL/v3/users/USER/PACKAGENAME/build

Example ::

  curl -s -X POST -H "Content-Type: application/json" -i  -d '{ "source_url": "https://github.com/kaji-project/kaji-project.git", "source_type": "git", "branch": "kaji"}' http://joulupukki.example.com/v3/users/example/kaji/build
