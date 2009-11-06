#
# Copyright (C) 2008 bpeck@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, config
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from beaker.server.widgets import myPaginateDataGrid
from beaker.server.xmlrpccontroller import RPCRoot
from beaker.server.helpers import *
from bexceptions import *
from upload import Uploader
#from turbogears.scheduler import add_interval_task

import cherrypy

from model import *
import string

class RecipeTasks(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    upload = Uploader(config.get("basepath.logs", "/var/www/beaker/logs"))

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def upload_file(self, task_id, path, name, size, md5sum, offset, data):
        """
        upload to task in pieces
        """
        try:
            recipetask = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))

        recipe_id = recipetask.recipe.id
        job_id = recipetask.recipe.recipeset.job.id
        recipetask_path = "%02d/%s/%s/%s/%s" % (int(str(job_id)[-2:]),
                                         job_id,
                                         recipe_id,
                                         task_id,
                                         path)
        return self.upload.uploadFile(recipetask_path,
                                      name,
                                      size,
                                      md5sum,
                                      offset,
                                      data)


    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def watchdogs(self, status='active'):
        """ Return all active/expired tasks for this lab controller
            The lab controllers login with host/fqdn
        """
        try:
            lab_controller = identity.current.user.user_name.split('/')[1]
        except IndexError:
            raise BX(_('Invalid login: %s, must log in as lab controller' % identity.current.user))
        try:
            labcontroller = LabController.by_name(lab_controller)
        except InvalidRequestError:
            raise BX(_('Invalid lab_controller: %s' % lab_controller))
        return [dict(  task_id = w.recipetask.id, 
                     recipe_id = w.recipe.id,
                        system = w.system.fqdn) for w in Watchdog.by_status(labcontroller, status)]

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def start(self, task_id, watchdog_override=None):
        """
        Set task status to Running
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        return task.start(watchdog_override)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def extend(self, task_id, kill_time):
        """
        Extend tasks watchdog by kill_time seconds
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        return task.extend(kill_time)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def stop(self, task_id, stop_type, msg=None):
        """
        Set task status to Completed
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        if stop_type not in task.stop_types:
            raise BX(_('Invalid stop_type: %s, must be one of %s' %
                             (stop_type, task.stop_types)))
        kwargs = dict(msg = msg)
        return getattr(task,stop_type)(**kwargs)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def result(self, task_id, result_type, path=None, score=None, summary=None):
        """
        Record a Result
        """
        try:
            task = RecipeTask.by_id(task_id)
        except InvalidRequestError:
            raise BX(_('Invalid task ID: %s' % task_id))
        if result_type not in task.result_types:
            raise BX(_('Invalid result_type: %s, must be one of %s' %
                             (result_type, task.result_types)))
        kwargs = dict(path=path, score=score, summary=summary)
        return getattr(task,result_type)(**kwargs)

    @expose(format='json')
    def to_xml(self, id):
        taskxml = RecipeTask.by_id(id).to_xml().toprettyxml()
        return dict(xml=taskxml)
