# -*- coding: utf-8 -*-
"""
    views

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import tornado
from tornado.options import options
from wtforms import (Form, TextField, StringField, SelectField,
    TextAreaField)
from monstor.utils.wtforms import (REQUIRED_VALIDATOR, TornadoMultiDict,
    EMAIL_VALIDATOR)
from monstor.utils.web import BaseHandler as MonstorBaseHandler
from monstor.utils.i18n import _
from raven.contrib.tornado import SentryMixin
from itsdangerous import URLSafeSerializer

from .models import (User, Organisation, Team, Project, AccessControlList,
    TaskList, Task, FollowUp)


class OrganisationMixin(object):
    """
    A mixin class
    """
    def find_organisations(self):
        """
        Returns a dictionary with key=organisation and values=list of projects
        the user participated under the organisation.
        """
        organisations = {}
        current_user = User.objects.with_id(self.current_user.id)
        for organisation in self.current_user.organisations:
            all_projects = Project.objects(organisation=organisation).all()
            projects = [
                project for project in all_projects for team in\
                    project.acl if current_user in team.team.members
            ]
            organisations[organisation] = projects
        return organisations

    def find_projects(self, organisation):
        """
        Returns a dictionary with key=user participated project and
        values=list of tasklists under the project
        """
        projects = {}
        current_user = User.objects.with_id(self.current_user.id)
        all_projects = Project.objects(organisation=organisation).all()
        user_projects = [
            project for project in all_projects for team in project.acl\
                if current_user in team.team.members
        ]
        for project in user_projects:
            projects[project] = TaskList.objects(project=project).all()
        return projects

    def find_tasklists(self, organisation, project_slug):
        """
        Returns a dictionary with key=tasklist and values=list of tasks
        """
        tasklists = {}
        project = Project.objects(
            organisation=organisation, slug=project_slug
        ).first()
        user_tasklists = TaskList.objects(project=project).all()
        for tasklist in user_tasklists:
            tasklists[tasklist] = Task.objects(task_list=tasklist).all()
        return tasklists

    def security_check(self, organisation_slug):
        """
        Verify that organisation is existing or not. if it is not existing
        raise HTTPError(404), else return 'organisation'
        """
        for organisation in self.current_user.organisations:
            if organisation.slug == organisation_slug:
                break
        else:
            raise tornado.web.HTTPError(404)
        return organisation


class BaseHandler(MonstorBaseHandler, SentryMixin):
    """
    Base handler for titan
    """
    pass


class GetingStartedHandler(BaseHandler):
    """
    Handle welcome page
    """
    def get(self):
        """
        render getting started page
        """
        user_orgs = self.current_user.organisations
        self.render('user/gettingstarted.html', organisations=user_orgs)


class HomePageHandler(BaseHandler, OrganisationMixin):
    """
    A home page handler
    """
    def get(self):
        organisations = {}
        if self.current_user:
            organisations = self.find_organisations()
        self.render('user/home.html', organisations=organisations)


class OrganisationForm(Form):
    """
    Generate Form for creating an organisation
    """
    name = TextField(_("Name"), [REQUIRED_VALIDATOR])
    slug = StringField(_("Slug"), [REQUIRED_VALIDATOR])


class TeamForm(Form):
    """
    Generate form for creating a new team under current organisation
    """
    name = StringField(_('Name'), [REQUIRED_VALIDATOR])


class SlugVerificationHandler(BaseHandler):
    """
    A handler that should help AJAX implementation of checking if a slug can
    be used for the organisation.
    """
    @tornado.web.authenticated
    def post(self):
        """
        Accept a string and check if any existing organisation uses that
        string as a slug.

        The return value is a 'true' or 'false' which are valid javascript
        literals which can be safely `eval`ed
        """
        slug = self.get_argument("slug")
        organisation = Organisation.objects(slug=slug).first()
        if not organisation:
            self.write('true')
        else:
            self.write('false')


class OrganisationsHandler(BaseHandler, OrganisationMixin):
    """
    A Collections Handler
    """

    @tornado.web.authenticated
    @tornado.web.addslash
    def get(self):
        """
        The organisations of the current user
        """
        if self.current_user:
            organisations = self.find_organisations()
        if self.is_xhr:
            self.write({
                'result': [
                    {
                        'id': o.id,
                        'name': o.name,
                    } for o in organisations
                ]
            })
        else:
            self.render(
                'projects/organisations.html',
                organisations=organisations,
                form=OrganisationForm()
            )
        return

    @tornado.web.authenticated
    @tornado.web.addslash
    def post(self):
        """
        Accept the form fields and create new organisation under current user.
        """
        current_user = User.objects.with_id(self.current_user.id)
        form = OrganisationForm(TornadoMultiDict(self))
        organisation = Organisation.objects(slug=form.slug.data).first()
        if organisation:
            self.flash(
                _(
                    "An organisation with the same short code already exists."
                ), 'Warning'
            )
        elif form.validate():
            organisation = Organisation(
                name=form.name.data,
                slug=form.slug.data
            )
            organisation.save()
            team = Team(
                name="Administrators", organisation=organisation,
                    members=[current_user]
            )
            team.save()
            self.flash(
                _("Created a new organisation %(name)s",
                    name=organisation.name
                ), "info"
            )
            self.redirect(
                self.reverse_url('projects.organisation', organisation.slug)
            )
            return
        organisations = self.find_organisations()
        self.flash(
            _("Something went wrong while submitting the form.\
                Please try again!"
            ), "warning"
        )
        self.render(
            "projects/organisations.html", form=form,
            organisations=organisations,
        )


class InvitationForm(Form):
    """
    Form used for inviting peoples to project
    """
    email = TextField(
        _('Email'), [EMAIL_VALIDATOR, REQUIRED_VALIDATOR]
    )


class RemoveForm(Form):
    """
    Form used for removing user from project
    """
    email_id = TextField(
        _('Email'), [EMAIL_VALIDATOR, REQUIRED_VALIDATOR]
    )


class OrganisationHandler(BaseHandler, OrganisationMixin):
    """
    An Element URI
    """

    @tornado.web.authenticated
    @tornado.web.removeslash
    def get(self, organisation_slug):
        """
        Render organisation page.

        :param organisation_slug: Slug of organisation. It is used to select
        the exact organisation from 'organisation' collection.
        """
        organisation = self.security_check(organisation_slug)
        if self.is_xhr:
            self.write({
                'id': organisation.id,
                'name': organisation.name,
            })
        else:
            organisations = self.current_user.organisations
            projects = self.find_projects(organisation)
            self.render(
                'projects/organisation.html',
                organisation=organisation,
                organisations=organisations,
                projects=projects,
                form=TeamForm(),
                invite_form=InvitationForm(),
                remove_form=RemoveForm()
            )
        return

    @tornado.web.authenticated
    def post(self, organisation_slug):
        """
        Add new team to current organisation.

        :param organisation_slug: Slug of organisation. It is used to select
        the exact organisation from 'organisation' collection.
        """
        current_user = User.objects.with_id(self.current_user.id)
        for organisation in current_user.organisations:
            if organisation.slug == organisation_slug:
                break
        else:
            raise tornado.web.HTTPError(404)

        form = TeamForm(TornadoMultiDict(self))
        admin_team = Team.objects(
            organisation=organisation, name="Administrators"
        ).first()

        if form.validate() and current_user in admin_team.members:
            team = Team(name=form.name.data,
                organisation=organisation,
                members=[current_user]
            )
            team.save()
            self.flash(
                _("A new team have been added to this organisation"), "info"
            )
            self.redirect(
                self.reverse_url('projects.organisation', organisation.slug)
            )
            return
        elif not form.validate():
            self.flash(
                _(
                    "Something went wrong while submitting the form."
                ), "warning"
            )
        else:
            self.flash(
                _("You have no permission for creating a team under this\
                 organisation.")
            )
        organisations = self.current_user.organisations
        projects = self.find_projects(organisation)
        self.render(
            'projects/organisation.html',
            organisation=organisation,
            organisations=organisations,
            projects=projects,
            form=TeamForm(),
            invite_form=InvitationForm(),
            remove_form=RemoveForm()
        )
        return


class OrganisationInviteHandler(BaseHandler, OrganisationMixin):
    """
    Handles Invitations to an organisation.
    """
    @tornado.web.authenticated
    def post(self, organisation_slug):
        """
        Accept email and add the user to the admin team of current
        organisation.

        :param organisation_slug: Slug of organisation. It is used to select
        the exact organisation from 'organisation' collection.
        """
        organisation = self.security_check(organisation_slug)
        user = User.objects(email=self.get_argument("email")).first()
        if user:
            team = Team.objects(
                organisation=organisation, name="Administrators"
            ).first()
            existing = [
                member for member in team.members\
                if member.email == user.email
            ]
            if existing:
                self.write("User already exist in this organisation!")
        else:
            self.write("Not implemented yet!")


class OrganisationUserRemoveHandler(BaseHandler, OrganisationMixin):
    """
    Handle removal of users from organisation, It automatically removes the
    user from all projects of this organisation.
    """
    @tornado.web.authenticated
    def post(self, organisation_slug):
        """
        Remove user from current organisation

        :param organisation_slug: Slug of organisation. It is used to select
        the exact organisation from 'organisation' collection.
        """
        organisation = self.security_check(organisation_slug)
        current_user = User.objects.with_id(self.current_user.id)
        user = User.objects(email=self.get_argument("email")).first()
        admin_team = Team.objects(
            organisation=organisation, name="Administrators"
        ).first()

        if current_user in admin_team.members:
            if not user:
                self.write("Not a valid email Id")
                return
            existing = Team.objects(organisation=organisation, members=user)
            if not existing:
                self.write("User does not exist in this organisation.")
                return
            if user == current_user:
                self.write("This is your own email Id! please check")
                return
            teams = Team.objects(organisation=organisation, members=user).all()
            for team in teams:
                if user in team.members:
                    del team.members[team.members.index(user)]
                    team.save()
            self.write("User removed from the current organisation")
            return
        else:
            self.write("You have no permission for deleting this user")


class ProjectForm(Form):
    """
    Generate form for creating a project
    """
    name = TextField("name", [REQUIRED_VALIDATOR])
    slug = StringField("slug", [REQUIRED_VALIDATOR])
    team = SelectField("team", [REQUIRED_VALIDATOR], choices=[])


class ProjectsHandler(BaseHandler, OrganisationMixin):
    """
    Handles projects
    """
    @tornado.web.authenticated
    @tornado.web.addslash
    def get(self, organisation_slug):
        """
        Projects under the current organisations

        :param organisation_slug: Slug of organisation. It is used to select
        the exact organisation from 'organisation' collection.

        """
        organisation = self.security_check(organisation_slug)
        projects = self.find_projects(organisation)
        if self.is_xhr:
            self.write({
                'result': [
                    {
                        'id': project.id,
                        'name': project.name,
                    } for project in projects
                ]
            })
        else:
            organisations = self.current_user.organisations
            form = ProjectForm()
            form.team.choices = [
                (unicode(team.id), team.name) for team in organisation.teams
            ]
            self.render(
                'projects/projects.html',
                projects=projects,
                form=form,
                organisation=organisation,
                organisations=organisations
            )
        return

    @tornado.web.authenticated
    def post(self, organisation_slug):
        """
        Accept the form fields and create a new project under the
        current Organisation

        :param organisation_slug: Slug of organisation. It is used to select
        the exact organisation from 'organisation' collection.
        """
        form = ProjectForm(TornadoMultiDict(self))
        current_user = User.objects.with_id(self.current_user.id)
        for organisation in current_user.organisations:
            if organisation.slug == organisation_slug:
                break
        else:
            raise tornado.web.HTTPError(404)

        projects = self.find_projects(organisation)
        organisations = self.current_user.organisations
        form.team.choices = [
            (unicode(team.id), team.name) for team in organisation.teams
        ]
        existing = Project.objects(
            slug=form.slug.data, organisation=organisation
        ).first()
        if existing:
            self.flash(
                _(
                    "A project with the same short code already exists with\
                    in current organisation."
                ), 'Warning'
            )
        elif form.validate():
            admin_team = Team.objects().with_id(form.team.data)
            if current_user not in admin_team.members:
                self.flash(
                    _(
                        "You are not an administrator. Only administrators can\
                         create projects"
                    ), 'warning'
                )
                self.render(
                    "projects/projects.html", form=form,
                    organisation=organisation, projects=projects
                )
                return
            acl_admin = AccessControlList(team=admin_team, role="admin")
            project = Project(
                name=form.name.data,
                acl=[acl_admin],
                slug=form.slug.data,
                organisation=organisation
            )
            project.save()
            self.flash(
                _(
                    "Created a new project %(name)s",
                    name=project.name
                ), "info"
            )
            self.redirect(
                self.reverse_url(
                    'projects.project', organisation.slug,
                    project.slug
                )
            )
            return
        self.flash(
            _(
                "Something went wrong while submitting the form.\
                Please try again!"
            ), "Error"
        )
        self.render(
            "projects/projects.html",
            form=form,
            organisation=organisation,
            organisations=organisations,
            projects=projects
        )


class ProjectSlugVerificationHandler(BaseHandler, OrganisationMixin):
    """
    A handler that should help AJAX implementation of checking if a slug can
    be used for the project under current organisation.
    """
    @tornado.web.authenticated
    def post(self, organisation_slug):
        """
        Accept a string and check if any existing project under current
        organisation uses that string as a slug.

        The return value is a 'true' or 'false' which are valid javascript
        literals which can be safely `eval`ed
        """
        project_slug = self.get_argument("project_slug")
        organisation = self.security_check(organisation_slug)
        project = Project.objects(
            slug=project_slug,
            organisation=organisation
        ).first()
        if not project:
            self.write('true')
        else:
            self.write('false')


class ProjectHandler(BaseHandler, OrganisationMixin):
    """
    Handle a particular project
    """
    @tornado.web.authenticated
    def get(self, organisation_slug, project_slug):
        """
        Render project page, It includes the options for inviting another
        user to the current project.

        :param organisation_slug: Slug of organisation. It is used to select
        the exact organisation from 'organisation' collection.
        :param project_slug: Slug of project. It is used to select the exact
        project from the 'project' collection.

        """
        organisation = self.security_check(organisation_slug)
        tasklists = self.find_tasklists(organisation, project_slug)
        organisations = self.current_user.organisations
        projects = self.find_projects(organisation)
        project = Project.objects(
            organisation=organisation, slug=project_slug
        ).first()
        if not project:
            raise tornado.web.HTTPError(404)

        # Response
        if self.is_xhr:
            self.write({
                'id': project.id,
                'name': project.name,
            })
        else:
            self.render(
                'projects/project.html',
                project=project,
                organisation=organisation,
                tasklists=tasklists,
                organisations=organisations,
                projects=projects,
                form=InvitationForm(),
            )
        return

    @tornado.web.authenticated
    def post(self, organisation_slug, project_slug):
        """
        Invite peoples to current project
        """
        organisation = self.security_check(organisation_slug)
        form = InvitationForm(TornadoMultiDict(self))
        current_user = User.objects.with_id(self.current_user.id)
        project = Project.objects(
            organisation=organisation, slug=project_slug
        ).first()
        tasklists = self.find_tasklists(organisation, project_slug)
        admin_team = Team.objects(
            organisation=organisation, name="Administrators"
        ).first()

        if form.validate() and current_user in admin_team.members:
            signer = URLSafeSerializer(
                self.application.settings["cookie_secret"]
            )
            invitation_key = signer.dumps(
                (organisation_slug, project_slug, form.email.data)
            )
            parts = []
            try:
                parts.append(
                    MIMEText(
                        self.render_string(
                            'emails/invitation-html.html',
                            invitation_key=invitation_key, project=project,
                        ), 'html'
                    )
                )
            except IOError:
                logging.warning('No HTML template emails/invitation-html.html')

            try:
                parts.append(
                    MIMEText(
                        self.render_string(
                            "emails/invitation-text.html",
                            invitation_key=invitation_key, project=project,
                        ), 'text'
                    )
                )
            except IOError:
                logging.warning("No TEXT template emails/invitation-text.html")
            if not parts:
                # Fallback to simple string replace since no templates
                # have been defined.
                parts.append(
                    MIMEText(
                        'To accept click: %s' %
                        self.reverse_url(
                            'projects.project.invitation',
                            invitation_key
                        ), 'text'
                    )
                )
            message = MIMEMultipart('alternative')
            message['Subject'] = _("Invitation")
            message['From'] = options.email_sender
            message['To'] = form.email.data
            for part in parts:
                message.attach(part)
            self.send_mail(
                options.email_sender, form.email.data, message.as_string()
            )
            self.flash(_("Invitation sent"))
        elif not form.validate():
            self.flash(
                _("Something went wrong while submitting the form.\
                    Please try again."
                ), "Error"
            )
        else:
            self.flash(
                _("You have no permission for inviting another users\
                    in to this project"
                ),"info"
            )
        organisations = self.current_user.organisations
        projects = self.find_projects(organisation)
        self.render(
                "projects/project.html",
                form=form,
                organisation=organisation,
                project=project,
                tasklists=tasklists,
                organisations=organisations,
                projects=projects
        )
        return


class ProjectInvitationHandler(BaseHandler):
    """
    Add user to current project
    """
    @tornado.web.authenticated
    def get(self, invitation_key):
        """
        Accept the invitation key and add the user to current user.

        :param invitation_key: It includes the organisation_slug,
        project_slug and email. Extract these values from invitation_key
        and add the user to exact project.
        """
        signer = URLSafeSerializer(self.application.settings["cookie_secret"])
        invitation_key = signer.loads(invitation_key)
        user = User.objects(email=invitation_key[2]).first()
        project = Project.objects(slug=invitation_key[1]).first()
        organisation = Organisation.objects(slug=invitation_key[0]).first()
        team = [
            team.team for team in project.acl if team.role == "admin"
        ][0]

        if user and user not in team.members:
            team.reload()
            team.members.append(user)
            team.save()
            self.flash(
                _("You are added to this project"), "info"
            )
            self.redirect(
                self.reverse_url(
                    "projects.project", organisation.slug, project.slug
                )
            )
            return
        elif not user:
            self.flash(
                _(
                    'Invalid invitation key!'
                ), 'error'
            )
        else:
            self.flash(
                _(
                    "User already existing on current project"
                ),"info"
            )
        self.redirect(
            self.reverse_url("projects.organisations")
        )


class TaskListForm(Form):
    """
    Generate form for creating a new form.
    """
    name = StringField('Name', [REQUIRED_VALIDATOR])


class TaskListsHandler(BaseHandler, OrganisationMixin):
    """
    Handle the task lists under the Project
    """
    @tornado.web.authenticated
    def get(self, organisation_slug, project_slug):
        """
        Render Task lists under the current project, also provide the options
        for creating a new tasklist.

        :param organisation_slug: Slug of organisation. It is used to select
        the exact organisation from 'organisation' collection.

        :param project_slug: Slug of project. It is used to select the exact
        project from the 'project' collection.
        """
        organisation = self.security_check(organisation_slug)
        project = Project.objects(slug=project_slug).first()
        tasklists = self.find_tasklists(organisation, project_slug)
        if self.is_xhr:
            self.write({
                'result': [
                    {
                        'id': tasklist.id,
                        'name': tasklist.name,
                    } for tasklist in tasklists
                ]
            })
        else:
            organisations = self.current_user.organisations
            projects = self.find_projects(organisation)
            self.render(
                "projects/task_lists.html",
                tasklists=tasklists,
                form=TaskListForm(),
                organisation=organisation,
                project=project,
                organisations=organisations,
                projects=projects
            )
        return

    @tornado.web.authenticated
    def post(self, organisation_slug, project_slug):
        """
        Accept the form fields and create a new lasklist under the project.

        :param organisation_slug: Slug of organisation. It is used to select
            the exact organisation from 'organisation' collection.

        :param project_slug: Slug of project. It is used to select the exact
            project from the 'project' collection.
        """
        organisation = self.security_check(organisation_slug)
        form = TaskListForm(TornadoMultiDict(self))
        project = Project.objects(slug=project_slug).first()

        if form.validate() and project:
            tasklist = TaskList(name=form.name.data, project=project)
            tasklist.save()
            self.flash(
                _("Created a new task list %(name)s", name=tasklist.name),
                'Info'
            )
            self.redirect(
                self.reverse_url(
                    'projects.tasklist', organisation.slug, project.slug,
                    tasklist.sequence
                )
            )
            return
        tasklists = self.find_tasklists(organisation, project_slug)
        organisations = self.current_user.organisations
        projects = self.find_projects(organisation)

        self.flash(
            _(
                "Something went wrong while creating the task list! Try Again"
            ), 'error'
        )
        self.render('projects/task_lists.html',
            form=form,
            organisation=organisation,
            project=project,
            tasklists=tasklists,
            organisations=organisations,
            projects=projects
        )


class TaskForm(Form):
    """
    Generate form for creating a task under current tasklist
    """
    title = StringField("Title", [REQUIRED_VALIDATOR])
    status = SelectField("Status", [REQUIRED_VALIDATOR], default="new",
        choices=[
            ('new', 'New'),
            ('progress', 'Progress'),
            ('hold', 'Hold'),
            ('resolved', 'Resolved'),
        ]
    )


class TaskListHandler(BaseHandler, OrganisationMixin):
    """
    Handles a particular tasklist
    """
    @tornado.web.authenticated
    def get(self, organisation_slug, project_slug, tasklist_sequence):
        """
        Render tasklist page.

        :param organisation_slug: Slug of organisation. It is used to select
        the exact organisation from 'organisation' collection.

        :param project_slug: Slug of project. It is used to select the exact
            project from the 'project' collection.

        :param tasklist_sequence: An incremental Id is assigned with each
        tasklist. This tasklist id used to select the exact tasklist from the
        'tasklist'  collection.
        """
        organisation = self.security_check(organisation_slug)
        project = Project.objects(
            slug=project_slug,
            organisation=organisation
        ).first()
        tasklist = TaskList.objects(
            project=project,
            sequence=tasklist_sequence
        ).first()
        if not tasklist:
            raise tornado.web.HTTPError(403)
        if self.is_xhr:
            self.write({
                'id': tasklist.id,
                'name': tasklist.name,
            })
        else:
            organisations = self.current_user.organisations
            projects = self.find_projects(organisation)
            tasklists = self.find_tasklists(organisation, project_slug)
            self.render(
                'projects/task_list.html',
                tasklist=tasklist,
                project=project,
                organisation=organisation,
                organisations=organisations,
                projects=projects,
                tasklists=tasklists,
                form=TaskForm()
            )
        return


class CommentForm(Form):
    """
    Form to add comments to ticket.
    """
    comment = TextAreaField("comment", [REQUIRED_VALIDATOR])
    status = SelectField('status', [REQUIRED_VALIDATOR],
        choices=[
            ('new', 'New'),
            ('in-progress', 'In Progress'),
            ('hold', 'Hold'),
            ('resolved', 'Resolved'),
        ]
    )
    assigned_to = SelectField(
        "Assigned to", [REQUIRED_VALIDATOR],
        choices=[]
    )


class TasksHandler(BaseHandler, OrganisationMixin):
    """
    Handle all tasks
    """
    @tornado.web.authenticated
    def get(self, organisation_slug, project_slug, tasklist_sequence):
        """
        Display All tasks under the current tasklist.

        :param organisation_slug: Slug of organisation. It is used to select
        the exact organisation from 'organisation' collection.

        :param project_slug: Slug of project. It is used to select the exact
        project from the 'project' collection.

        :param tasklist_sequence: An incremental Id is assigned with each
        tasklist. This tasklist id used to select the exact tasklist from the
        'tasklist'  collection.
        """
        organisation = self.security_check(organisation_slug)
        project = Project.objects(
            slug=project_slug,
            organisation=organisation
        ).first()
        organisations = self.current_user.organisations
        tasklist = TaskList.objects(
            project=project, sequence=tasklist_sequence
        ).first()
        tasklists = self.find_tasklists(organisation, project_slug)
        projects = self.find_projects(organisation)
        self.render(
            'projects/tasks.html',
            organisation=organisation,
            project=project,
            tasklist=tasklist,
            tasklists=tasklists,
            organisations=organisations,
            projects=projects
        )
        return


class TaskHandler(BaseHandler, OrganisationMixin):
    """
    Handle the tasks under the current task list
    """
    @tornado.web.authenticated
    def get(self, organisation_slug, project_slug, tasklist_sequence,
            task_sequence=None):
        """
        Render specified task or create task form.

        :param organisation_slug: Slug of organisation. It is used to select
        the exact organisation from 'organisation' collection.

        :param project_slug: Slug of project. It is used to select the exact
        project from the 'project' collection.

        :param tasklist_sequence: An incremental Id is assigned with each
        tasklist. This tasklist id used to select the exact tasklist from the
        'tasklist'  collection.

        :param task_ID: An incremental Id is assigned with each task.
        This task id used to select the exact tasklist from the
        'task'  collection.

        If task_sequence=None, it returns create new task form, else it returns
        the corresponding task.
        """
        organisation = self.security_check(organisation_slug)
        project = Project.objects(
            slug=project_slug, organisation=organisation
        ).first()
        tasklist = TaskList.objects(
            project=project,
            sequence=tasklist_sequence
        ).first()
        tasks = Task.objects(task_list=tasklist).all()
        organisations = self.current_user.organisations
        projects = self.find_projects(organisation)
        if task_sequence:
            task = Task.objects(
                task_list=tasklist, sequence=task_sequence
            ).first()
            if self.is_xhr:
                self.write({
                    'id': task.id,
                    'title': task.title,
                    'message': task.message,
                    'status': task.status,
                    'assigned_to': task.assigned_to,
                    'due_date': task.due_date,
                    'watchers': task.watchers,
                    'task_list': task.task_list,
                    'follow_ups': task.follow_ups,
                    'sequence': task.sequence
                })
            else:
                comment_form = CommentForm()
                team = [
                    team.team if team.role == "admin" else ''\
                        for team in project.acl
                ][0]
                comment_form.assigned_to.choices = [
                    (unicode(user.id), user.name) for user in team.members
                ]
                self.render(
                    'projects/task.html',
                    task=task,
                    organisation=organisation,
                    project=project,
                    tasklist=tasklist,
                    form=comment_form,
                    organisations=organisations,
                    projects=projects,
                    tasks=tasks
                )
            return
        else:
            task_form = TaskForm()
            self.render(
                'projects/task_list.html',
                form=task_form,
                organisation=organisation,
                project=project,
                tasklist=tasklist,
                tasks=tasks,
                organisations=organisations,
                projects=projects
            )
        return

    @tornado.web.authenticated
    def post(self, organisation_slug, project_slug, tasklist_sequence):
        """
        Create a new task

        :param organisation_slug: Slug of organisation. It is used to select
        the exact organisation from 'organisation' collection.

        :param project_slug: Slug of project. It is used to select the exact
        project from the 'project' collection.

        :param tasklist_sequence: An incremental Id is assigned with each
        tasklist. This tasklist id used to select the exact tasklist from the
        'tasklist'  collection.
        """
        organisation = self.security_check(organisation_slug)
        project = Project.objects(
            slug=project_slug, organisation=organisation
        ).first()

        tasklist = TaskList.objects(
            project=project, sequence=tasklist_sequence
        ).first()
        if project == None or tasklist == None:
            raise tornado.web.HTTPError(403)
        form = TaskForm(TornadoMultiDict(self))
        if form.validate() and tasklist:
            task = Task(
                title=form.title.data,
                status=form.status.data,
                task_list=tasklist,
                follow_ups=[],
            )
            task.save()
            self.flash(
                _("A new task has been created successfully."), "Info"
            )
            self.redirect(
                self.reverse_url(
                    "projects.task",
                    organisation_slug,
                    project_slug,
                    tasklist_sequence,
                    task.sequence
                )
            )
            return
        else:
            tasklists = self.find_tasklists(organisation, project_slug)
            organisations = self.current_user.organisations
            projects = self.find_projects(organisation)
            self.flash(
                _(
                    "Something went wrong while creating a new task! Try Again"
                ), "warning"
            )
            self.render(
                "projects/task_list.html",
                form=form,
                organisation=organisation,
                project=project,
                tasklist=tasklist,
                tasklists=tasklists,
                projects=projects,
                organisations=organisations
            )
            return


class CommentHandler(BaseHandler, OrganisationMixin):
    """
    Task Comment Handler
    """
    @tornado.web.authenticated
    def post(self, organisation_slug, project_slug, tasklist_sequence,
            task_sequence):
        """
        Add a new comment

        :param organisation_slug: Slug of organisation. It is used to select
        the exact organisation from 'organisation' collection.

        :param project_slug: Slug of project. It is used to select the exact
        project from the 'project' collection.

        :param tasklist_sequence: An incremental Id is assigned with each
        tasklist. This tasklist id used to select the exact tasklist from the
        'tasklist'  collection.

        :param task_sequence: An incremental Id is assigned with each task.
        This task id used to select the exact tasklist from the
        'task'  collection.
        """
        organisation = self.security_check(organisation_slug)
        project = Project.objects(
            slug=project_slug,
            organisation=organisation
        ).first()
        tasklist = TaskList.objects(
            project=project, sequence=tasklist_sequence
        ).first()
        form = CommentForm(TornadoMultiDict(self))
        team = [
            team.team if team.role == "admin" else ''\
            for team in project.acl
        ][0]
        form.assigned_to.choices = [
            (unicode(user.id), user.name) for user in team.members
        ]
        task = Task.objects(task_list=tasklist, sequence=task_sequence).first()
        if form.validate():
            assigned_user = User.objects().with_id(form.assigned_to.data)
            comment = FollowUp(
                message=form.comment.data,
                to_status=form.status.data,
                to_assignee=assigned_user
            )
            if not task.follow_ups:
                task.follow_ups = [comment]
            else:
                task.follow_ups.append(comment)
                task.assigned_to = assigned_user
            task.save()

            parts = []
            try:
                parts.append(
                    MIMEText(
                        self.render_string(
                            'emails/comment_mail-html.html',
                            organisation_slug=organisation_slug,
                            project_slug=project_slug,
                            tasklist_sequence=tasklist_sequence,
                            task_sequence=task_sequence,
                            project=project,
                            task=task,
                            user=assigned_user,
                            message=form.comment.data,
                            assigner=self.current_user.name
                        ), 'html'
                    )
                )
            except IOError:
                logging.warning(
                    'No HTML template emails/comment_mail-html.html'
                )

            try:
                parts.append(
                    MIMEText(
                        self.render_string(
                            "emails/comment_mail-text.html",
                            organisation_slug=organisation_slug,
                            project_slug=project_slug,
                            tasklist_sequence=tasklist_sequence,
                            task_sequence=task_sequence,
                            project=project,
                            task=task,
                            user=assigned_user
                        ), 'text'
                    )
                )
            except IOError:
                logging.warning(
                    "No TEXT template emails/comment_mail-text.html"
                )
            if not parts:
                # Fallback to simple string replace since no templates
                # have been defined.
                parts.append(
                    MIMEText(
                        'To view click: %s' %
                        self.reverse_url(
                            'projects.task.comment-email',
                            organisation_slug=organisation_slug,
                            project_slug=project_slug,
                            tasklist_sequence=tasklist_sequence,
                            task_sequence=task_sequence,
                        ), 'text'
                    )
                )
            message = MIMEMultipart('alternative')
            message['Subject'] = _("Task Assigned to you")
            message['From'] = options.email_sender
            message['To'] = assigned_user.email
            for part in parts:
                message.attach(part)
            self.send_mail(
                options.email_sender, assigned_user.email, message.as_string()
            )
            self.flash(
                _(
                    "Your comment has been added to the task."
                ), "Info"
            )
            self.redirect(
                self.reverse_url(
                    "projects.task",
                    organisation_slug,
                    project_slug,
                    tasklist_sequence,
                    task.sequence
                )
            )
            return
        else:
            organisations = self.current_user.organisations
            projects = self.find_projects(organisation)
            tasks = Task.objects(task_list = tasklist).all()
            self.flash(
                _(
                    "Something went wrong while adding new comment! Try Again"
                ), "warning"
            )
            self.render(
                'projects/task.html',
                task=task,
                organisation=organisation,
                project=project,
                tasklist=tasklist,
                form=form,
                organisations=organisations,
                projects=projects,
                tasks=tasks
            )
            return


class CommentMailHandler(BaseHandler):
    """
    Handles comment email link
    """
    @tornado.web.authenticated
    def get(self, organisation_slug, project_slug, tasklist_sequence,
        task_sequence):
        """
        Accept comment key and handle operations.

        """
        for organisation in self.current_user.organisations:
            if organisation.slug == organisation_slug:
                break
        else:
            raise tornado.web.HTTPError(404)
        self.redirect(
            self.reverse_url(
                "projects.task",
                organisation.slug,
                project_slug,
                tasklist_sequence,
                task_sequence
            )
        )
        return
