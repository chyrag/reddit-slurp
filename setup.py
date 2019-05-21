#!/usr/bin/env python3

from setuptools import setup, find_packages

# Package meta-data.
NAME = 'reddit-slurp'
DESCRIPTION = 'Slurp images from reddit channels.'
URL = 'https://github.com/chyrag/reddit-slurp'
EMAIL = 'chirag@kantharia.in'
AUTHOR = 'Chirag Kantharia'
REQUIRES_PYTHON = '>=3.6.0'
VERSION = '0.1.0'
LICENSE = 'Apache License'
CLASSIFIERS = [
    'Development Status :: 2 - Pre-Alpha',
    'Intended Audience :: End Users/Desktop',
    'Topic :: Internet',
    'License :: OSI Approved :: Apache Software License',
    'Programming Language :: Python :: 3'
]
REQUIRED = ['praw', 'docopt', 'bs4']

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    url=URL,
    author=AUTHOR,
    author_email=EMAIL,
    license=LICENSE,
    classifiers=CLASSIFIERS,
    install_requires=REQUIRED,
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'slurp=slurp:main',
        ],
    })
