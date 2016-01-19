########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

from setuptools import setup
import os
import codecs

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    # intentionally *not* adding an encoding option to open
    return codecs.open(os.path.join(here, *parts), 'r').read()


setup(
    name='clo',
    version='0.0.1',
    url='https://github.com/nir0s/club',
    author='Gigaspaces',
    author_email='cosmo-admin@gigaspaces.com',
    license='LICENSE',
    platforms='All',
    description='Simplifies Cloudify Offline Bootstrapping.',
    long_description=read('README.rst'),
    packages=['clo'],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'clo = clo.clo:main',
        ]
    },
    install_requires=[
        "click==6.2",
        "pyyaml==3.10",
        "sh==1.11",
        "retrying==1.3.3"
    ]
)
