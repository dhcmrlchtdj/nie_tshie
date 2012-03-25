#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import base64
import uuid

import tornado.wsgi

import view


handlers = [
    (r'/main(?:/([1-9]{1}\d*))?', view.Main),
    (r'/tags/([^/]+)(?:/([1-9]\d*))?', view.Filter),

    (r'/bookmark/new', view.New),
    (r'/bookmark/get/(.{4,})', view.Get),
    (r'/bookmark/set', view.Set),
    (r'/bookmark/del/(.{4,})', view.Del),

    (r'/dashboard', view.Dashboard),
    (r'/dashboard/move_tag', view.MoveTag),
    (r'/dashboard/delete_tag', view.DeleteTag),
    (r'/dashboard/input', view.Input),
    (r'/dashboard/output(?:/([^/]+))?', view.Output),

    (r'/.*', view.Redirect),
]

settings = {
    'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
    'cookie_secret': base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes),
    #'login_url': '/login',
    'autoescape': None,
    'xsrf_cookies': True,
    'debug': os.environ.get('SERVER_SOFTWARE', '').startswith('Development/'),
}

application = tornado.wsgi.WSGIApplication(handlers, **settings)


if __name__ == '__main__':
    import wsgiref.handlers
    def main():
        wsgiref.handlers.CGIHandler().run(application)
    main()

