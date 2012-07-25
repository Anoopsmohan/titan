# -*- coding: utf-8 -*-
"""
    test_tasklist

    Test the TaskList API

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import unittest
from urllib import urlencode

from tornado import testing, options
from monstor.app import make_app
from titan.projects.models import (User, Project, Organisation, Team, TaskList,
    AccessControlList, Task)
from titan.settings import SETTINGS
from monstor.utils.web import slugify


class TestTaskList(testing.AsyncHTTPTestCase):
    """
    Test Tasklist
    """

    def get_app(self):
        options.options.database = 'test_tasklist'
        SETTINGS['xsrf_cookies'] = False
        application = make_app(**SETTINGS)
        return application

    def setUp(self):
        super(TestTaskList, self).setUp()
        user = User(name="Test User", email="test@example.com", active=True)
        user.set_password("password")
        user.save(safe=True)
        self.user = user

    def get_login_cookie(self):
        """
        Login and return the cookie required for making authenticated requests
        """
        response = self.fetch(
            '/login', method="POST", follow_redirects=False,
            body=urlencode({
                'email': 'test@example.com', 'password': 'password'
            })
        )
        return response.headers.get('Set-Cookie')

    def test_0010_tasklistshandler_get(self):
        """
        Test tasklists handler get method
        """
        organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
        organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()

        # User not logged in
        response = self.fetch(
            '/%s/%s/tasklists' % (organisation.slug, project.slug),
            method="GET",
            follow_redirects=False
        )
        self.assertEqual(response.code, 302)

        # User logged in and an existing organisation
        cookies = self.get_login_cookie()
        response = self.fetch(
            '/%s/%s/tasklists' % (organisation.slug, project.slug),
            method="GET",
            follow_redirects=False,
            headers={'Cookie': cookies}
        )
        self.assertEqual(response.code, 200)

        # User logged in and Organisation not existing
        cookies = self.get_login_cookie()
        response = self.fetch(
            '/an-invalid-organisation/%s/tasklists' % project.slug,
            method="GET",
            follow_redirects=False,
            headers={'Cookie': cookies}
        )
        self.assertEqual(response.code, 404)

    def test_0020_tasklists_post1(self):
        """
        Test post with logged in and invalid organisation slug
        """
        organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
        organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        response = self.fetch(
            '/an-invalid-organisation/%s/tasklists' % project.slug,
            method="POST",
            follow_redirects=False,
            body=urlencode({'name': "Version 0.1"}),
            headers={'Cookie': self.get_login_cookie()}
        )
        self.assertEqual(response.code, 404)

    def test_0030_tasklists_post2(self):
        """
        Test post with valid organisation slug and invalid
        project slug
        """
        organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
        organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        response = self.fetch(
            '/%s/an-invalid-project-slug/tasklists' % organisation.slug,
            method="POST",
            follow_redirects=False,
            body=urlencode({'name': "Version 0.1"}),
            headers={'Cookie': self.get_login_cookie()}
        )
        self.assertEqual(response.code, 200)

    def test_0040_tasklists_post3(self):
        """
        Test post with valid organisation slug and valid project slug
        """
        organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
        organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        response = self.fetch(
            '/%s/%s/tasklists' % (organisation.slug, project.slug),
            method="POST",
            follow_redirects=False,
            body=urlencode({'name': "Version 0.1"}),
            headers={'Cookie': self.get_login_cookie()}
        )
        self.assertEqual(response.code, 302)

    def test_0050_tasklist_get_1(self):
        """
        Test Task List which already exist
        """
        organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
        organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        tasklist = TaskList(name="version 01", project=project)
        tasklist.save()
        response = self.fetch(
            '/%s/%s/%s' % (organisation.slug, project.slug, tasklist.sequence),
            method="GET",
            follow_redirects=False,
            headers={'Cookie': self.get_login_cookie()}
        )
        self.assertEqual(response.code, 200)

    def test_0060_tasklist_get_2(self):
        """
        Test Task List which does not exist
        """
        organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
        organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        tasklist = TaskList(name="version 01", project=project)
        tasklist.save()
        response = self.fetch(
            '/%s/%s/5' % (organisation.slug, project.slug),
            method="GET",
            follow_redirects=False,
            headers={'Cookie': self.get_login_cookie()}
        )
        self.assertEqual(response.code, 404)

    def test_0070_tasklist_get_1(self):
        """
        Test Task List without logged in
        """
        organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
        organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        tasklist = TaskList(name="version 01", project=project)
        tasklist.save()
        response = self.fetch(
            '/%s/%s/%s' % (organisation.slug, project.slug, tasklist.sequence),
            method="GET",
            follow_redirects=False,
        )
        self.assertEqual(response.code, 302)

    def test_0080_tasklist_get_1(self):
        """
        Test Task List with wrong organisation slug
        """
        organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
        organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        tasklist = TaskList(name="version 01", project=project)
        tasklist.save()
        response = self.fetch(
            '/wrong-organisation/%s/%s' % (project.slug, tasklist.sequence),
            method="GET",
            follow_redirects=False,
            headers={'Cookie': self.get_login_cookie()}
        )
        self.assertEqual(response.code, 404)

    def test_0090_task_handler_get_1(self):
        """
        Try to render a particular task without being logged in
        """
        organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
        organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        tasklist = TaskList(name="version 01", project=project)
        tasklist.save()

        response = self.fetch(
            '/%s/%s/%s/tasks/new' % (
                organisation.slug, project.slug, tasklist.sequence
            ),
            method="GET",
            follow_redirects=False,
        )
        self.assertEqual(response.code, 302)

    def test_0100_task_handler_get_2(self):
        """
        Try to render a particular task without providing Task Id
        If 'task id' is not provided, then it will return create task form.
        """
        organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
        organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        tasklist = TaskList(name="version 01", project=project)
        tasklist.save()

        response = self.fetch(
            '/%s/%s/%s/tasks/new' % (
                organisation.slug, project.slug, tasklist.sequence
            ),
            method="GET",
            follow_redirects=False,
            headers={'Cookie': self.get_login_cookie()}
        )
        self.assertEqual(response.code, 200)

    def test_0110_task_handler_get_3(self):
        """
        Try to render a particular task with providing Task Id.
        If 'task id' is provided, then it will render a particular task.
        """
        organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
        organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        tasklist = TaskList(name="version 01", project=project)
        tasklist.save()
        task = Task(
            title="testing",
            status="new",
            assigned_to=self.user,
            task_list=tasklist
        )
        task.save()

        response = self.fetch(
            '/%s/%s/%s/tasks/%s' % (
                organisation.slug, project.slug, tasklist.sequence,
                task.sequence
            ),
            method="GET",
            follow_redirects=False,
            headers={'Cookie': self.get_login_cookie()}
        )
        self.assertEqual(response.code, 200)

    def test_0120_task_handler_post_1(self):
        """
        Test TaskHandler 'post' method
        """
        organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
        organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        tasklist = TaskList(name="version 01", project=project)
        tasklist.save()

        response = self.fetch(
            '/%s/%s/%s/tasks/new' % (
                organisation.slug, project.slug, tasklist.sequence
            ),
            method="POST",
            follow_redirects=False,
            body=urlencode({
                    "title": "testing",
                    "status": "new",
                    "assigned_to": str(self.user.id),
            }),
            headers={'Cookie': self.get_login_cookie()},
        )
        self.assertEqual(response.code, 302)

    def test_0130_task_handler_post_2(self):
        """
        Test TaskHandler 'post' method with wrong organisation slug
        """
        organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
	organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        tasklist = TaskList(name="version 01", project=project)
        tasklist.save()

        response = self.fetch(
            '/wrong-organisation/%s/%s/tasks/new' % (
                project.slug, tasklist.sequence
            ),
            method="POST",
            follow_redirects=False,
            body=urlencode({
                    "title": "testing",
                    "status": "new",
                    "assigned_to": str(self.user.id),
            }),
            headers={'Cookie': self.get_login_cookie()},
        )
        self.assertEqual(response.code, 404)

    def test_0140_task_handler_post_3(self):
        """
        Test TaskHandler 'post' method with wrong project slug
        """
	organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
	organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        tasklist = TaskList(name="version 01", project=project)
        tasklist.save()

        response = self.fetch(
            '/%s/wrong-project/%s/tasks/new' % (
                organisation.slug, tasklist.sequence
            ),
            method="POST",
            follow_redirects=False,
            body=urlencode({
                    "title": "testing",
                    "status": "new",
                    "assigned_to": str(self.user.id),
            }),
            headers={'Cookie': self.get_login_cookie()},
        )
        self.assertEqual(response.code, 403)

    def test_0150_task_handler_post_4(self):
        """
        Test TaskHandler 'post' method with wrong tasklist sequence
        """
	organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
	organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        tasklist = TaskList(name="version 01", project=project)
        tasklist.save()

        response = self.fetch(
            '/%s/wrong-project/4/tasks/new' % (
                organisation.slug
            ),
            method="POST",
            follow_redirects=False,
            body=urlencode({
                    "title": "testing",
                    "status": "new",
                    "assigned_to": str(self.user.id),
            }),
            headers={'Cookie': self.get_login_cookie()},
        )
        self.assertEqual(response.code, 403)

    def test_0160_task_handler_post_5(self):
        """
        Test TaskHandler 'post' method invalid form fields
        """
	organisation = Organisation(
            name="open labs", slug=slugify("open labs")
        )
	organisation.save()
        team = Team(
            name="Developers", organisation=organisation,
            members=[self.user]
        )
        team.save()
        acl = AccessControlList(team=team, role="admin")
        project = Project(
            name="titan", organisation=organisation, acl=[acl],
            slug=slugify('titan project')
        )
        project.save()
        tasklist = TaskList(name="version 01", project=project)
        tasklist.save()

        response = self.fetch(
            '/%s/%s/%s/tasks/new' % (
                organisation.slug, project.slug, tasklist.sequence
            ),
            method="POST",
            follow_redirects=False,
            body=urlencode({
                    "status": "new",
                    "assigned_to": str(self.user.id),
            }),
            headers={'Cookie': self.get_login_cookie()},
        )
        self.assertEqual(response.code, 200)

    def tearDown(self):
        """
        Drop the database after every test
        """
        from mongoengine.connection import get_connection
        get_connection().drop_database('test_tasklist')


if __name__ == '__main__':
    unittest.main()
