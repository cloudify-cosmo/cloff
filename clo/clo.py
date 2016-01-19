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

# https://gist.github.com/tamirko/accef7c7df76f9581056

# 3rd party sha1's
# https://download.elastic.co/elasticsearch/elasticsearch/elasticsearch-1.6.0.noarch.rpm.sha1.txt
# https://download.elastic.co/logstash/logstash/packages/centos/logstash-1.5.0-1.noarch.rpm.sha1.txt


import logging
import os
import re
import tempfile
import json
import urlparse
import shutil
import sys
import hashlib

import click
import sh
import yaml
from retrying import retry

from . import logger, utils


DEFAULT_MP_URL = 'http://github.com/cloudify-cosmo/cloudify-manager-blueprints/archive/{0}.tar.gz'  # NOQA
FILE_SERVER_MODIFIERS = [
    'http://repository.cloudifysource.org/org',
    'http://www.getcloudify.org/spec',
]

lgr = logger.init()


class Clo():
    def __init__(self, source=DEFAULT_MP_URL, tag=None, verbose=False):
        if verbose:
            lgr.setLevel(logging.DEBUG)
        else:
            lgr.setLevel(logging.INFO)
        self.tag = tag
        self.source = source.format(tag) if tag else source

    def _get_simple_manager_blueprint(self, tmp):
            manager_blueprints_archive = os.path.join(tmp, 'mp.tar.gz')
            if not os.path.isfile(manager_blueprints_archive):
                utils.download_file(self.source, manager_blueprints_archive)
            else:
                lgr.info('{0} already exists. Skipping...'.format(
                    manager_blueprints_archive))
            utils.untar(manager_blueprints_archive, tmp)
            os.remove(manager_blueprints_archive)

            # load simple manager blueprint
            manager_blueprints = os.path.join(
                tmp,
                'cloudify-manager-blueprints-{0}'.format(self.tag))
            simple_manager_blueprint_path = os.path.join(
                manager_blueprints, 'simple-manager-blueprint.yaml')
            lgr.debug('Loading Blueprint: {0}'.format(
                simple_manager_blueprint_path))
            return simple_manager_blueprint_path

    def create(self, file_server='http://10.0.2.2:8000/'):
        tmp = tempfile.mkdtemp(prefix='cloudify-offline-')
        if not os.path.isdir(tmp):
            os.makedirs(tmp)
        lgr.debug('Using temp dir: {0}'.format(tmp))

        try:
            simple_manager_blueprint_path = \
                self._get_simple_manager_blueprint(tmp)
            with open(simple_manager_blueprint_path) as f:
                content = f.read()

            urls = self._get_urls_from_file(content)
            # meh. need to strip some stuff here as no one is perfect in
            # writing yaml
            urls = [u.strip("'").strip('"').rstrip('\n\r') for u in urls]

            def _handle_url(url):
                relative_path = \
                    self._get_relative_path_from_url(url).lstrip('/')
                destination_dir = os.path.join(
                    tmp, 'resources', os.path.dirname(relative_path))
                destination_path = os.path.join(
                    destination_dir, os.path.basename(relative_path))
                if os.path.isfile(destination_path):
                    lgr.warn('{0} already exists. Skipping...'.format(
                        destination_path))
                    return
                # only handle url with relevant prefix (i.e, manager resources)
                if url.startswith(tuple(FILE_SERVER_MODIFIERS)):
                    if not os.path.isdir(destination_dir):
                        lgr.debug('Creating: {0}'.format(destination_dir))
                        os.makedirs(destination_dir)
                    self._download_manager_resource(url, destination_path)

            for url in urls:
                _handle_url(url)
            self._modify_file_server(
                simple_manager_blueprint_path, content, file_server)
            with open(os.path.join(tmp, 'metadata.json'), 'w') as f:
                f.write(json.dumps(
                    {'file_server': file_server, 'tag': self.tag}))
            utils.tar(tmp, 'cloudify-offline.tar.gz')
        finally:
            shutil.rmtree(tmp)

    @retry(stop_max_attempt_number=5)
    def _download_manager_resource(self, url, destination_path):
        utils.download_file(url, destination_path)
        md5_file_path = destination_path + '.md5'
        utils.download_file(url + '.md5', md5_file_path)
        # unfortunately, not all resources currently have md5 checksum files.
        # one all do, we'll remove this and fail if the md5 file is not found.
        if os.path.isfile(md5_file_path):
            if self._validate_md5_checksum(destination_path, md5_file_path):
                return True

    def serve(self, serve_under=None, file_server='',
              python_exec=sys.executable):
        """Runs a webserver serving the relevant files for bootstrapping.

        This runs a SimpleHTTPServer serving Cloudify's Resources.
        """
        serve_under = \
            serve_under or tempfile.mkdtemp(prefix='cloudify-offline-')
        # this should be done in a single step. currently, it will untar,
        # modify, tar and then untar again for serving. what a waste. eh.
        if file_server:
            self.modify(file_server)
        utils.untar(self.source, serve_under)
        self._run_http_server(os.path.join(
            serve_under, os.listdir(serve_under)[0]), python_exec)

    def _fix_file_server(self, file_server):
        return file_server + '/' if not file_server.endswith('/') \
            else file_server

    def _modify_file_server(self, blueprint_path, content, file_server):
        lgr.info('Editing {0}'.format(blueprint_path))
        file_server = self._fix_file_server(file_server)
        lgr.info('Applying server: {0} to all resource urls.'.format(
            file_server))
        content = re.sub(
            r'{0}'.format('|'.join(FILE_SERVER_MODIFIERS)),
            file_server + 'resources', content)
        yaml_content = yaml.safe_load(content)
        lgr.debug(json.dumps(yaml_content, indent=2))

        with open(blueprint_path, 'w') as f:
            f.write(yaml.dump(yaml_content, default_flow_style=False))

    def modify(self, file_server):
        """This modifies the file server inside the manager blueprint.
        """
        file_server = self._fix_file_server(file_server)
        serve_under = tempfile.mkdtemp(prefix='cloudify-offline-')
        lgr.info('Running on {0}'.format(serve_under))
        try:
            utils.untar(self.source, serve_under)
            path = os.path.join(serve_under, os.listdir(serve_under)[0])
            metadata = self._get_meta(path)
            lgr.info(metadata)
            # from here on, this can definitely be consolidated as it is also
            # done under `create`
            manager_blueprints = os.path.join(
                path, 'cloudify-manager-blueprints-{0}'.format(
                    metadata['tag']))
            simple_manager_blueprint_path = os.path.join(
                manager_blueprints, 'simple-manager-blueprint.yaml')
            lgr.info('Editing {0}'.format(simple_manager_blueprint_path))
            with open(simple_manager_blueprint_path) as f:
                # read yaml also
                content = f.read()
                lgr.info('Replacing {0} with {1}.'.format(
                    metadata['file_server'], file_server))
                content = content.replace(metadata['file_server'], file_server)
                yaml_content = yaml.safe_load(content)
            with open(simple_manager_blueprint_path, 'w') as f:
                f.write(yaml.dump(yaml_content, default_flow_style=False))
            try:
                shutil.remove(self.source)
            except:
                lgr.error('Could not remove original source {0}'.format(
                    self.source))
            utils.tar(path, 'cloudify-offline.tar.gz')
        finally:
            shutil.rmtree(serve_under)

    def validate(self):
        """Validates resources inside the manager blueprint via
        md5 verification and metadata comparison.
        """
        raise NotImplementedError()

    def _validate_md5_checksum(self, resource_path, md5_checksum_file_path):
        lgr.info('Validating md5 checksum for {0}'.format(resource_path))
        with open(md5_checksum_file_path) as checksum_file:
            original_md5 = checksum_file.read().rstrip('\n\r').split()[0]

        with open(resource_path) as file_to_check:
            data = file_to_check.read()
            # pipe contents of the file through
            md5_returned = hashlib.md5(data).hexdigest()

        if original_md5 == md5_returned:
            return True
        else:
            lgr.error('md5 checksum validation failed! '
                      'Original checksum: {0} '
                      'Calculated checksum: {1}.'.format(
                          original_md5, md5_returned))
            return False

    def _get_meta(self, path):
        with open(os.path.join(path, 'metadata.json')) as f:
            return json.loads(f.read())

    def _run_http_server(self, serve_under, python_exec):
        lgr.info('Serving {0}'.format(serve_under))
        prev = os.getcwd()
        os.chdir(serve_under)
        server = sh.Command(python_exec)
        server('-m', 'SimpleHTTPServer', _bg=True)
        os.chdir(prev)

    def _get_file_name_from_path(self, url_path):
        return os.path.dirname(url_path)

    def _get_relative_path_from_url(self, url):
        return urlparse.urlparse(url).path

    def _get_urls_from_file(self, content):
        # specifically look for the relevant bucket/cdn
        return re.findall(r'(\'?https?://[^\s\'\""]+\'?)', content)

    def _get_file_name_from_url(self, url):
        return url.split('/')[-1]

    def _get_file_extension_from_url(self, url):
        return os.path.splitext(url.split('/')[-1])[1]

    def _get_sub_bucket(self, url):
        return url.split('/')[-2]


@click.group()
def main():
    pass


@click.command()
@click.option('-s', '--source', default=DEFAULT_MP_URL.format('3.3'),
              help='Source URL, or local path of manager blueprints.')
@click.option('-t', '--tag', default='3.3',
              help='cloudify-manager-blueprints repo tag.')
@click.option('--file-server', required=True,
              help='Server the resources will be served on '
                   '(e.g. http://10.10.10.10:8000).')
@click.option('-v', '--verbose', default=False, is_flag=True)
def create(source, tag, file_server, verbose):
    """Creates an offline env for bootstrappin
    """
    logger.configure()
    clo = Clo(source, tag, verbose)
    clo.create(file_server=file_server)


@click.command()
@click.argument('source')
@click.argument('server')
@click.option('-v', '--verbose', default=False, is_flag=True)
def modify(source, server, verbose):
    """Creates an offline env for bootstrappin
    """
    logger.configure()
    clo = Clo(source, verbose=verbose)
    clo.modify(server)


@click.command()
@click.argument('source')
@click.option('-u', '--serve-under', default='',
              help='Path under which the files will be served.')
@click.option('--file-server',
              help='Server the resources will be served on '
                   '(e.g. http://10.10.10.10:8000). This defaults to whatever '
                   'is already defined in the blueprint.')
@click.option('-v', '--verbose', default=False, is_flag=True)
def serve(source, serve_under, file_server, verbose):
    """Creates an offline env for bootstrappin
    """
    logger.configure()
    clo = Clo(source, verbose=verbose)
    clo.serve(serve_under, file_server)


main.add_command(create)
main.add_command(modify)
main.add_command(serve)
