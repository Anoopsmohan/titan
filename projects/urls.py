# -*- coding: utf-8 -*-
"""
    urls


    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import tornado.web

from .views import (OrganisationHandler, OrganisationsHandler, HomePageHandler,
    SlugVerificationHandler, ProjectsHandler, ProjectHandler,
    ProjectSlugVerificationHandler, TaskListsHandler, TaskListHandler,
    TaskHandler, TasksHandler, ProjectInvitationHandler, CommentHandler,
    CommentMailHandler, OrganisationInviteHandler,
    OrganisationUserRemoveHandler, GetingStartedHandler)

U = tornado.web.URLSpec

HANDLERS = [
    U(r'/', HomePageHandler, name="home"),
    U(r'/my-organisations/', OrganisationsHandler,
        name="projects.organisations"),
    U(r'/getting-started/', GetingStartedHandler,
        name="projects.welcome"),
    U(r'/([a-zA-Z0-9_-]+)', OrganisationHandler,
        name="projects.organisation"),
    U(r'/\+slug-check', SlugVerificationHandler,
        name="projects.organisations.slug-check"),
    U(r'/([a-zA-Z0-9_-]+)/invitation', OrganisationInviteHandler,
        name="projects.organisations.invitation"),
    U(r'/([a-zA-Z0-9_-]+)/remove', OrganisationUserRemoveHandler,
        name="projects.organisations.remove"),
    U(r'/([a-zA-Z0-9_-]+)/projects/', ProjectsHandler,
        name="projects.projects"),
    U(r'/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)', ProjectHandler,
        name="projects.project"),
    U(r'/([a-zA-Z0-9-_]+)/\+slug-check',
        ProjectSlugVerificationHandler,
        name="projects.project.slug-check"),
    U(r'/invitation/([a-zA-Z0-9-_\.]+)',
        ProjectInvitationHandler,
        name="projects.project.invitation"),
    U(r'/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)/tasklists', TaskListsHandler,
        name='projects.tasklists'),
    U(r'/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)/(\d+)',
        TaskListHandler, name='projects.tasklist'),
    U(r'/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)/(\d+)/tasks',
        TasksHandler, name='projects.tasks'),
    U(r'/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)/(\d+)/tasks/(\d+)',
        TaskHandler, name='projects.task'),
    U(r'/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)/(\d+)/tasks/new',
        TaskHandler, name='projects.task.new'),
    U(r'/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)/(\d+)/tasks/(\d+)/comment',
        CommentHandler, name='projects.task.comment'),
    U(r'/comment/mail/([a-zA-Z0-9\.-_]+)/([a-zA-Z0-9\.-_]+)/(\d+)/(\d+)',
        CommentMailHandler, name="projects.task.comment-email")
]
