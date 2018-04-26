import os
import json
from datetime import datetime

from flask import render_template, send_from_directory

from . import config

def get_json_file():
    if config.config._sections['archive']['html folder'] == '%(dir)s/html' \
            and config.ARCHIVE_DIR == '':
        json_file = os.path.join('html', 'index.json')
    else:
        json_file = os.path.join(config.HTML_FOLDER, 'index.json')
    return json_file


def get_archive_folder():
    if config.config._sections['archive']['html folder'] == '%(dir)s/html' \
            and config.config._sections['archive']['archive folder'] == '%(html folder)s/archive' \
            and config.ARCHIVE_DIR == '':
        archive_folder = os.path.join('html', 'archive')
    else:
        archive_folder = os.path.join(config.ARCHIVE_FOLDER, 'archive')
    return archive_folder


def index():
    json_file = get_json_file()
    try:
        with open(json_file) as f:
            json_data = json.load(f)
    except FileNotFoundError as e:
        json_data = {
            'num_links': 0,
            'updated': None,
            'links': [],
        }
    return render_template(
        'bookmark_archiver/index.html',
        time_updated=
            datetime.fromtimestamp(float(json_data['updated']))
            if json_data['updated'] else None,
        num_links=json_data['num_links'],
        entries=json_data['links'],
        git_sha=config.GIT_SHA,
        short_git_sha=config.GIT_SHA[:7] if config.GIT_SHA else '',
        footer_info=config.FOOTER_INFO,
    )
