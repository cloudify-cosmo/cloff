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
import urlparse
import shutil

import click
import sh
import yaml

from . import logger, utils


DEFAULT_MP_URL = 'http://github.com/cloudify-cosmo/cloudify-manager-blueprints/archive/{0}.tar.gz'  # NOQA
REPO_MODIFIERS = [
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

    def create(self, tempdir='/tmp/tmpzNDry5', repo='http://10.0.2.2:8000/'):
        # tempdir = tempdir or tempfile.mkdtemp(prefix='cloudify-offline-')
        # if not os.path.isdir(tempdir):
        #     os.makedirs(tempdir)
        repo = repo + '/' if not repo.endswith('/') else repo
        tempdir = tempfile.mkdtemp(prefix='cloudify-offline-')
        lgr.debug('Using temp dir: {0}'.format(tempdir))

        # extract manager blueprints
        try:
            mp_archive_path = os.path.join(tempdir, 'mp.tar.gz')
            if not os.path.isfile(mp_archive_path):
                utils.download_file(self.source, mp_archive_path)
            else:
                lgr.info('{0} already exists. Skipping...'.format(
                    mp_archive_path))
            utils.untar(mp_archive_path, tempdir)
            os.remove(mp_archive_path)

            # load simple manager blueprint
            mp_path = os.path.join(
                tempdir, 'cloudify-manager-blueprints-{0}'.format(self.tag))
            simple_mp_path = os.path.join(
                mp_path, 'simple-manager-blueprint.yaml')
            lgr.debug('Loading Blueprint: {0}'.format(simple_mp_path))
            with open(simple_mp_path) as f:
                new_content = f.read()

            # get urls from blueprint
            urls = self._get_urls_from_file(new_content)
            urls = [u.strip("'").strip('"').rstrip('\n\r') for u in urls]
            # lgr.debug(json.dumps(urls, indent=4))

            for url in urls:
                skip = False
                relative_path = \
                    self._get_relative_path_from_url(url).lstrip('/')
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
                        file_path = os.path.join(
                            tmp_destination_path, filename)
                        utils.download_file(url, file_path)
                        # lgr.info('Downloading {0} to {1}'.format(
                        #     url, file_path))
                        # try:
                        #     with open(file_path, 'w') as f:
                        #         f.write('')
                        # except:
                        #     pass

                    new_url = repo + 'resources/' + relative_path
                    lgr.debug('Replacing: {0}\nWith: {1}'.format(url, new_url))
                    new_content = new_content.replace(url, new_url)

            yaml_content = yaml.safe_load(new_content)
            lgr.info(json.dumps(yaml_content, indent=4))

            with open(simple_mp_path, 'w') as f:
                f.write(yaml.dump(yaml_content, default_flow_style=False))

            with open(os.path.join(tempdir, 'metadata.json'), 'w') as f:
                f.write(json.dumps(
                    {'repo': repo, 'tag': self.tag}
                ))

            utils.tar(tempdir, 'cloudify-offline.tar.gz')
        finally:
            shutil.rmtree(tempdir)

    def serve(self, repo='', path=None):
        """Runs a webserver serving the relevant files for bootstrapping.

        This runs a SimpleHTTPServer serving Cloudify's Resources.
        """
        path = path or tempfile.mkdtemp(prefix='cloudify-offline-')
        lgr.info('Serving {0}'.format(path))
        if repo:
            self.modify(repo)
        utils.untar(self.source, path)
        path = os.path.join(path, os.listdir(path)[0])
        self._run_http_server(path)

    def _modify_repo(self, blueprint, replace, rwith):
        lgr.info('Editing {0}'.format(blueprint))
        with open(blueprint) as f:
            # read yaml also
            content = f.read()
            lgr.info('Replacing {0} with {1}.'.format(replace, rwith))
            content = content.replace(replace, rwith)
            yaml_content = yaml.safe_load(content)
        with open(blueprint, 'w') as f:
            f.write(yaml.dump(yaml_content, default_flow_style=False))

    def modify(self, repo):
        """This modifies a repository inside the manager blueprint.
        """
        repo = repo + '/' if not repo.endswith('/') else repo
        tempdir = tempfile.mkdtemp(prefix='cloudify-offline-')
        lgr.info('Running on {0}'.format(tempdir))
        try:
            utils.untar(self.source, tempdir)
            path = os.path.join(tempdir, os.listdir(tempdir)[0])
            metadata = self._get_meta(path)
            lgr.info(metadata)
            mp_path = os.path.join(
                path, 'cloudify-manager-blueprints-{0}'.format(
                    metadata['tag']))
            simple_mp_path = os.path.join(
                mp_path, 'simple-manager-blueprint.yaml')
            lgr.info('Editing {0}'.format(simple_mp_path))
            with open(simple_mp_path) as f:
                # read yaml also
                content = f.read()
                lgr.info('Replacing {0} with {1}.'.format(
                    metadata['repo'], repo))
                content = content.replace(metadata['repo'], repo)
                yaml_content = yaml.safe_load(content)
            with open(simple_mp_path, 'w') as f:
                f.write(yaml.dump(yaml_content, default_flow_style=False))
            try:
                shutil.remove(self.source)
            except:
                lgr.error('Could not remove original source {0}'.format(
                    self.source))
            utils.tar(path, 'cloudify-offline.tar.gz')
        finally:
            shutil.rmtree(tempdir)

    def validate(self):
        """Validates resources inside the manager blueprint via
        md5 verification and metadata comparison.
        """
        pass

    def _get_meta(self, path):
        with open(os.path.join(path, 'metadata.json')) as f:
            return json.loads(f.read())

    def _run_http_server(self, path):
        lgr.info('Serving {0}'.format(path))
        prev = os.getcwd()
        os.chdir(path)
        server = sh.Command('/usr/bin/python2')
        print server('-m', 'SimpleHTTPServer', _bg=True)
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
@click.option('-v', '--verbose', default=False, is_flag=True)
def create(source, tag, verbose):
    """Creates an offline env for bootstrappin
    """
    logger.configure()
    clo = Clo(source, tag, verbose)
    clo.create()


@click.command()
@click.argument('source')
@click.argument('repo')
# @click.option('-r', '--repo', default='http://testrepo:8000',
#               help='Repository to serve files in.')
@click.option('-v', '--verbose', default=False, is_flag=True)
def modify(source, repo, verbose):
    """Creates an offline env for bootstrappin
    """
    logger.configure()
    clo = Clo(source, verbose=verbose)
    clo.modify(repo)


@click.command()
@click.argument('source')
@click.option('-v', '--verbose', default=False, is_flag=True)
def serve(source, verbose):
    """Creates an offline env for bootstrappin
    """
    logger.configure()
    clo = Clo(source, verbose=verbose)
    clo.serve()


main.add_command(create)
main.add_command(modify)
main.add_command(serve)
