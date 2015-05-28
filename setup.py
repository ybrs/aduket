#!/usr/bin/env python

from setuptools import setup, find_packages

VERSION = '0.1'
DESCRIPTION = 'simply create app servers (restfulish)'

setup(
    name='aduket',
    version=VERSION,
    description=DESCRIPTION,
    author='ybrs',
    license='MIT',
    url="http://github.com/ybrs/aduket",
    author_email='aybars.badur@gmail.com',
    packages=['aduket'],
    install_requires=['pymongo', 'inflection', 'mongomodels', 'flask', 'Flask-Cors'],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)