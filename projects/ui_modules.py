# -*- coding: utf-8 -*-
"""
    uimodules

    UI modules for rendering various components

    :copyright: (c) 2011-2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import tornado.web

# pylint: disable=W0221
# -- Arguments number different overridden method

class FormField(tornado.web.UIModule):
    """
    A Form Field
    """

    def render(self, field, class_="", **kwargs):
        """
        :param field: wtform.Field instance of any type
        :param class_ : CSS class
        :param **kwargs: Any values
        """
        if field.flags.required and "required" not in class_:
            class_ += " required "
        if field.description:
            kwargs['rel'] = 'popover'
            kwargs['data-original-title'] = field.label.text
            kwargs['data-content'] = field.description
        return self.render_string(
            "ui_modules/form-field.html", field=field, class_=class_,
            kwargs=kwargs
        )


UI_MODULES = {
    'FormField': FormField,
}
