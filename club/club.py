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

import logging
import os
import re
# import sys
# import shutil
import tempfile
# import json
import yaml

import click

from . import logger, utils


DEFAULT_MP_URL = 'http://github.com/cloudify-cosmo/cloudify-manager-blueprints/archive/master.tar.gz'  # NOQA
WAGONS_PATH = 'wagons'
YAMLS_PATH = 'yamls'
COMPONENTS_PATH = 'components'
CLOUDIFY_RESOURCES_PATH = 'cloudify'
AGENTS_PATH = 'agents'


lgr = logger.init()


# download manager blueprints repo
# get all resource links from manager blueprint
# download all resources to corresponding directories
# if flag provided to set url for webserver containing the resources:
# change all blueprint resource links to provided webserver address
# create tar.gz from downloaded resources and the modified blueprints

CLOUDIFY_RESOURCES = [
    'rest_service_rpm_source_url',
    'management_worker_rpm_source_url',
    'amqpinflux_rpm_source_url',
    'cloudify_resources_url',
    'webui_source_url',
    'grafana_source_url',
]

COMPONENTS = [
    'pip_source_rpm_url',
    'java_source_url',
    'erlang_source_url',
    'rabbitmq_source_url',
    'elasticsearch_source_url',
    'elasticsearch_curator_rpm_source_url',
    'logstash_source_url',
    'nginx_source_url',
    'influxdb_source_url',
    'langohr_source_url',
    'daemonize_source_url',
    'riemann_source_url',
    'nodejs_source_url',
]


class Club():
    def __init__(self, source, verbose=False):
        """Source depends on the context in which
        the class is instantiated.

        When using `create`, source can be a path to a local setup.py
        containing directory; a URL to a GitHub like package archive, a
        name of a PyPI package in the format: PACKAGE_NAME==PACKAGE_VERSION
        or a versionless PyPI PACKAGE_NAME.

        When using `install` or `validate`, source can be either a path
        to a local or a URL based Wagon archived tar.gz file.
        """
        if verbose:
            lgr.setLevel(logging.DEBUG)
        else:
            lgr.setLevel(logging.INFO)
        self.source = source

    def create(self):
        tempdir = tempfile.mkdtemp()
        lgr.info('Using temp dir: {0}'.format(tempdir))
        temp_components_path = os.path.join(tempdir, COMPONENTS_PATH)
        temp_resources_path = os.path.join(tempdir, CLOUDIFY_RESOURCES_PATH)
        temp_yamls_path = os.path.join(tempdir, YAMLS_PATH)
        temp_wagons_path = os.path.join(tempdir, WAGONS_PATH)
        os.makedirs(temp_components_path)
        os.makedirs(temp_resources_path)
        os.makedirs(temp_yamls_path)
        os.makedirs(temp_wagons_path)
        mp_archive_path = os.path.join(tempdir, 'mp.tar.gz')
        utils.download_file(self.source, mp_archive_path)
        utils.untar(mp_archive_path, tempdir)
        mp_path = os.path.join(tempdir, 'cloudify-manager-blueprints-master')
        simple_mp_path = os.path.join(
            mp_path, 'simple-manager-blueprint.yaml')
        lgr.info('Loading Blueprint: {0}'.format(simple_mp_path))
        with open(simple_mp_path) as f:
            data = yaml.safe_load(f)
        agent_packages = data['inputs']['agent_package_urls']['default']
        agent_packages = [agent_packages[a] for a in agent_packages.keys()]

        # # dsl_resources = data['inputs']['dsl_resources']['default']
        # lgr.info(json.dumps(data, indent=4, sort_keys=True))
        # plugin_resources = data['inputs']['plugin_resources']['default']
        # components = [data['inputs'][c]['default'] for c in COMPONENTS]
        # # cloudify_resources = [data['inputs'][r]['default'] for r in CLOUDIFY_RESOURCES]
        # # dsl_resources = [dsl_resources.get('source_path') for r in dsl_resources]

        with open(simple_mp_path) as f:
            urls = self._get_urls_from_file(f.read())
        for url in urls:
            lgr.info('Placing URL {0}'.format(url))
            ext = self._get_file_extension_from_url(url)
            lgr.info('Extension {0}'.format(ext))
            subbucket = self._get_sub_bucket(url)
            if url in agent_packages:
                utils.download_file(url, AGENTS_PATH)
            elif ext == '.wgn':
                utils.download_file(url, WAGONS_PATH)
            elif ext in ['.yaml', '.yml']:
                utils.download_file(url, YAMLS_PATH)
            elif subbucket == 'components':
                utils.download_file(url, COMPONENTS_PATH)
            elif ext in ['.rpm', '.tar.gz']:
                utils.download_file(url, CLOUDIFY_RESOURCES_PATH)
            urls.remove(url)

    def _get_urls_from_file(self, content):
        # specifically look for the relevant bucket/cdn
        return re.findall(r'(https?://[^\s]+)', content)

    def _get_file_extension_from_url(self, url):
        return os.path.splitext(url.split('/')[-1])[1]

    def _get_sub_bucket(self, url):
        return url.split('/')[-2]


@click.group()
def main():
    pass


@click.command()
@click.option('-s', '--source', required=True, default=DEFAULT_MP_URL,
              help='Source URL, or local path to manager blueprints.')
@click.option('-v', '--verbose', default=False, is_flag=True)
def create(source, verbose):
    """Creates an offline env for bootstrappin
    """
    logger.configure()
    packager = Cloff(source, verbose)
    packager.create()


main.add_command(create)
