#!/usr/bin/env python3
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
import logging
import os
import sys

try:
    from flask import Flask, send_from_directory
    from flask.cli import FlaskGroup
    import click
except ImportError:
    print(
        '[X] Please install required package to use the server: '
        'pip install bookmark-archiver[server]'
    )
    raise SystemExit(1)


# permanent env config
os.environ['BOOKMARK_ARCHIVER_USE_DEFAULT_CONFIG'] = 'True'
os.environ['BOOKMARK_ARCHIVER_CHG_ROOT_FOLDER'] = 'False'


def create_app(script_info=None):
    """create app."""
    app = Flask(__name__)
    # logging
    log_file = 'bookmark_archiver.log'
    file_handler = TimedRotatingFileHandler(log_file, 'midnight')
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter('<%(asctime)s> <%(levelname)s> %(message)s'))
    app.logger.addHandler(file_handler)
    # reloader
    reloader = app.config['TEMPLATES_AUTO_RELOAD'] = \
        bool(os.getenv('BOOKMARK_ARCHIVER_RELOADER')) or app.config['TEMPLATES_AUTO_RELOAD']
    if reloader:
        app.jinja_env.auto_reload = True
    # app config
    app.config['SECRET_KEY'] = os.getenv('BOOKMARK_ARCHIVER_SECRET_KEY') or os.urandom(24)
    app.config['WTF_CSRF_ENABLED'] = False
    # debug
    debug = app.config['DEBUG'] = bool(os.getenv('BOOKMARK_ARCHIVER_DEBUG')) or app.config['DEBUG']
    if debug:
        app.config['DEBUG'] = True
        app.config['LOGGER_HANDLER_POLICY'] = 'debug'
        logging.basicConfig(level=logging.DEBUG)
        # pprint.pprint(app.config)
        print('Log file: {}'.format(log_file))


    @app.shell_context_processor
    def shell_context():
        return {'app': app}

    @app.template_filter('from_timestamp')
    def datetime_from_timestamp(s):
        if not s:
            return
        return datetime.fromtimestamp(float(s))

    from . import views
    json_file = views.get_json_file()
    # import is here to avoid program asking to create default config when no config exist
    # routing
    app.add_url_rule('/', 'index', views.index)  # NOQA
    app.add_url_rule(
        '/index.json', 'index_json',
        lambda : send_from_directory(
            os.path.dirname(os.path.abspath(json_file)),
            os.path.basename(json_file)
        )
    )
    app.add_url_rule('/archive/<timestamp>/<filename>', 'link_index', views.link_index)  # NOQA
    app.add_url_rule('/archive/<timestamp>', 'link_index', views.link_index)  # NOQA
    return app


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """This is a management script for application."""
    pass


if __name__ == '__main__':
    cli()
