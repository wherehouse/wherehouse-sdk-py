#!/bin/bash

###############################################################################
# https://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/
#
# Make sure you have a ~/.pypirc file that looks like:
#
# [distutils]
# index-servers =
#     pypi
#
# [pypi]
# repository: https://upload.pypi.org/legacy/
# username: dan_wherehouse
# password: <pw>
###############################################################################

python setup.py sdist bdist_wheel upload
