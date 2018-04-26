#l! /usr/bin/env python3
import os
from setuptools import setup, find_packages

user_conf_path = os.path.expanduser('~/.config/bookmark-archiver')

setup(
    name='bookmark-archiver',
    version='0.0.3',
    description='Your own personal Way-Back Machine',
    author='Nick Sweeting',
    url='https://pirate.github.io/bookmark-archiver/',
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'requests',
    ],
    extras_require={
        'dev':  ["pdbpp"],
        'server': ['Flask>=0.12.2'],
    },
    package_data={
        '': ['templates/*.html', 'archiver.conf'],
    },
    data_files=[
        ('/etc/bookmark-archiver', ['conf/archiver.conf']),
        (user_conf_path, ['conf/user.conf']),
    ],
    entry_points={
        'console_scripts': [
            'archive=bookmark_archiver.archive:main',
            'archive-config=bookmark_archiver.archive_config:main',
            'archive-server=bookmark_archiver.server:cli',
        ]
    },
    zip_safe=False
)
