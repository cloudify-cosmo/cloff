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

import os
import urllib
import tarfile
import zipfile
import sys
from contextlib import closing

from . import logger


DEFAULT_INDEX_SOURCE_URL = 'https://pypi.python.org/pypi/{0}/json'
IS_VIRTUALENV = hasattr(sys, 'real_prefix')

PLATFORM = sys.platform
IS_WIN = (os.name == 'nt')
IS_DARWIN = (PLATFORM == 'darwin')
IS_LINUX = (PLATFORM == 'linux2')

PROCESS_POLLING_INTERVAL = 0.1

lgr = logger.init()


def download_file(url, destination):
    def url_exists():
        import urllib2
        try:
            urllib2.urlopen(url)
            return True
        except:
            lgr.warn('{0} does not exist. Skipping...'.format(url))
            return False
    if not url_exists():
        return
    lgr.info('Downloading {0} to {1}...'.format(url, destination))
    final_url = urllib.urlopen(url).geturl()
    if final_url != url:
        lgr.debug('Redirected to {0}'.format(final_url))
    f = urllib.URLopener()
    f.retrieve(final_url, destination)


def zip(source, destination):
    lgr.info('Creating zip archive: {0}...'.format(destination))
    with closing(zipfile.ZipFile(destination, 'w')) as zip:
        for root, dirs, files in os.walk(source):
            for f in files:
                zip.write(os.path.join(root, f))


def unzip(archive, destination):
    lgr.debug('Extracting zip {0} to {1}...'.format(archive, destination))
    with closing(zipfile.ZipFile(archive, "r")) as zip:
        zip.extractall(destination)


def tar(source, destination):
    lgr.info('Creating tar.gz archive: {0}...'.format(destination))
    with closing(tarfile.open(destination, "w:gz")) as tar:
        tar.add(source, arcname=os.path.basename(source))


def untar(archive, destination):
    """Extracts files from an archive to a destination folder.
    """
    lgr.debug('Extracting tar.gz {0} to {1}...'.format(archive, destination))
    with closing(tarfile.open(name=archive)) as tar:
        files = [f for f in tar.getmembers()]
        tar.extractall(path=destination, members=files)
