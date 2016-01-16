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
import tempfile
import json
import yaml

import click
import sh

from . import logger, utils


DEFAULT_MP_URL = 'http://github.com/cloudify-cosmo/cloudify-manager-blueprints/archive/{0}.tar.gz'  # NOQA
REPO_MODIFIERS = [
    'http://repository.cloudifysource.org/org',
    'http://www.getcloudify.org/spec',
]

lgr = logger.init()


class Clo():
    def __init__(self, tag=None, source=DEFAULT_MP_URL, verbose=False):
        if verbose:
            lgr.setLevel(logging.DEBUG)
        else:
            lgr.setLevel(logging.INFO)
        self.tag = tag
        self.source = DEFAULT_MP_URL.format(tag) if tag else source

    def create(self, tempdir='/tmp/tmpzNDry5', repo='http://10.0.2.2:8000/'):
        tempdir = tempdir or tempfile.mkdtemp()
        if not os.path.isdir(tempdir):
            os.makedirs(tempdir)
        lgr.debug('Using temp dir: {0}'.format(tempdir))

        mp_archive_path = os.path.join(tempdir, 'mp.tar.gz')
        if not os.path.isfile(mp_archive_path):
            utils.download_file(self.source, mp_archive_path)
        else:
            lgr.info('{0} already exists. Skipping...'.format(mp_archive_path))
        utils.untar(mp_archive_path, tempdir)
        mp_path = os.path.join(
            tempdir, 'cloudify-manager-blueprints-{0}'.format(self.tag))
        simple_mp_path = os.path.join(
            mp_path, 'simple-manager-blueprint.yaml')
        lgr.debug('Loading Blueprint: {0}'.format(simple_mp_path))

        with open(simple_mp_path) as f:
            content = f.read()
            urls = self._get_urls_from_file(content)
            urls = [u.strip("'").strip('"').rstrip('\n\r') for u in urls]
            lgr.debug(json.dumps(urls, indent=4))
            # should probably filter by url look here.
            new_content = content

        for url in urls:
            skip = False
            relative_path = self._get_relative_path_from_url(url).lstrip('/')
            filename = os.path.basename(relative_path)
            relative_dir = os.path.dirname(relative_path)
            resources_path = os.path.join('resources', relative_dir)
            tmp_destination_path = os.path.join(tempdir, resources_path)
            destination_file = os.path.join(os.path.join(
                tmp_destination_path, filename))
            if os.path.isfile(destination_file):
                lgr.info('{0} already exists. Skipping...'.format(
                    destination_file))
                skip = True
            if not skip and not os.path.isdir(tmp_destination_path):
                lgr.debug('Creating: {0}'.format(tmp_destination_path))
                os.makedirs(tmp_destination_path)
            if url.startswith(tuple(REPO_MODIFIERS)):
                if not skip:
                    utils.download_file(url, os.path.join(
                        tmp_destination_path, filename))
                new_url = repo + 'resources/' + relative_path
                lgr.debug('Replacing: {0}\nWith: {1}'.format(url, new_url))
                new_content = new_content.replace(url, new_url)

        yaml_content = yaml.safe_load(new_content)
        lgr.info(json.dumps(yaml_content, indent=4))

        with open(simple_mp_path, 'w') as f:
            f.write(yaml.dump(yaml_content, default_flow_style=True))

        with open(os.path.join(tempdir, 'metadata.json'), 'w') as f:
            f.write(json.dumps({'repo': repo}))

        utils.tar(tempdir, 'cloudify-offline.tar.gz')

    def serve(self, repo=''):
        """Runs a webserver serving the relevant files for bootstrapping.

        This runs a SimpleHTTPServer serving Cloudify's Resources.
        """
        if repo:
            self.modify(repo)
        self._run_http_server()

    def modify(self, repo):
        """This modifies a repository inside the manager blueprint.
        """
        tempdir = tempfile.mkdtemp()
        utils.untar(self.source, tempdir)
        metadata = self._getmeta(tempdir)
        mp_path = os.path.join(
            tempdir, 'cloudify-manager-blueprints-{0}'.format(self.tag))
        simple_mp_path = os.path.join(
            mp_path, 'simple-manager-blueprint.yaml')
        with open(simple_mp_path) as f:
            content = f.read()
            content = content.replace(metadata['repo'], repo)
        with open(simple_mp_path, 'w') as f:
            f.write(yaml.dump(content, default_flow_style=True))
        utils.tar(tempdir, 'cloudify-offline.tar.gz')

    def validate(self):
        """Validates resources inside the manager blueprint.
        """
        pass

    def _get_meta(self, path):
        with open(path, 'metadata.json') as f:
            return json.dumps(f.read())

    def _run_http_server(self, path):
        prev = os.getcwd()
        os.chdir(path)
        server = sh.Command('/usr/bin/python')
        server('-m', 'SimpleHTTPServer', _bg=True)
        os.chdir(prev)

    def _get_file_name_from_path(self, url_path):
        return os.path.dirname(url_path)

    def _get_relative_path_from_url(self, url):
        import urlparse
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
@click.option('-t', '--tag', default='3.3',
              help='cloudify-manager-blueprints repo tag.')
@click.option('-s', '--source', default=DEFAULT_MP_URL,
              help='Source URL, or local path of manager blueprints.')
@click.option('-v', '--verbose', default=False, is_flag=True)
def create(tag, source, verbose):
    """Creates an offline env for bootstrappin
    """
    logger.configure()
    packager = Clo(tag, source, verbose)
    packager.create()


main.add_command(create)
