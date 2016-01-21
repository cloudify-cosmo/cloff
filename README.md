# Cloff

Simplifies Cloudify Offline Bootstrapping


Cloff creates a tar file containing whatever you need to bootstrap Cloudify offline.

It:

* Downloads all relevant resources.
* Runs a webserver serving all of those resources.
* Modifies manager blueprints to turn to the webserver when bootstrapping.

Note that currently, only the simple manager blueprint is modified.


## Installation

```
pip install http://github.com/cloudify-cosmo/wagon/archive/master.tar.gz
```


## Usage

### Create a cloff tar.gz archive

```shell
cloff create --help
```

#### Examples

```shell
# create an archive by retrieving the latest non-prerelease version from PyPI.
wagon create -s flask
# create an archive by retrieving the package from PyPI and keep the downloaded wheels (kept under <cwd>/plugin) and exclude the cloudify-plugins-common and cloudify-rest-client packages from the archive.
wagon create -s cloudify-script-plugin==1.2 --keep-wheels -v --exclude cloudify-plugins-common --exclude cloudify-rest-client
# create an archive by retrieving the source from a URL and creating wheels from requirement files found within the archive. Then, validation of the archive takes place. The created archive will be in zip format.
wagon create -s http://github.com/cloudify-cosmo/cloudify-script-plugin/archive/1.2.tar.gz -r --validate --format zip
# create an archive by retrieving the source from a local path and output the tar.gz file to /tmp/<PACKAGE>.tar.gz (defaults to <cwd>/<PACKAGE>.tar.gz) and provides explicit Python versions supported by the package (which usually defaults to the first two digits of the Python version used to create the archive.)
wagon create -s ~/packages/cloudify-script-plugin/ -o /tmp/ --pyver 33 --pyver 26 --pyver 27
# pass additional args to `pip wheel` (NOTE that conflicting arguments are not handled by wagon.)
wagon create -s http://github.com/cloudify-cosmo/cloudify-script-plugin/archive/1.2.zip -a '--retries 5'
```

### Serve Resources

```shell
cloff serve --help
```

#### Examples

```shell
# install a package from a local archive tar file and upgrade if already installed. Also, ignore the platform check which would force a package (whether it is or isn't compiled for a specific platform) to be installed.
wagon install -s ~/tars/cloudify_script_plugin-1.2-py27-none-any.wgn --upgrade --ignore-platform
# install a package from a url into an existing virtualenv.
wagon install -s http://me.com/cloudify_script_plugin-1.2-py27-none-any-none-none.wgn --virtualenv my_venv -v
# pass additional args to `pip install` (NOTE that conflicting arguments are not handled by wagon.)
wagon install -s http://me.com/cloudify_script_plugin-1.2-py27-none-any-none-none.wgn -a '--no-cache-dir'
```

Note that `--pre` is appended to the installation command to enable installation of prerelease versions.

#### Installing Manually

While wagon provides a generic way of installing wagon created archives, you might not want to use the installer as you might not wish to install wagon on your application servers. Installing the package manually via pip is as easy as running (for example):

```shell
tar -xzvf http://me.com/cloudify_script_plugin-1.2-py27-none-any-none-none.wgn
pip install --no-index --find-links cloudify-script-plugin/wheels cloudify-script-plugin
```


### Validate Packages

```sheel
wagon validate --help
```

The `validate` function provides shallow validation of a Wagon archive. Basically, it checks that some keys in the metadata are found, that all required wheels for a package are present and that the package is installable. It obviously does not check for a package's functionality.

This shallow validation should, at the very least, allow a user to be sure that a Wagon archive is not corrupted.

Note that the `--validate` flag provided with the `create` function uses this same validation method.

#### Examples

```shell
# validate that an archive is a wagon compatible package
wagon validate -s ~/tars/cloudify_script_plugin-1.2-py27-none-any-none-none.wgn
# validate from a url
wagon validate -s http://me.com/cloudify_script_plugin-1.2-py27-none-any-none-none.wgn
```


### Show Metadata

```sheel
wagon showmeta --help
```

Given a Wagon archive, this will print its metadata.

#### Examples

```shell
wagon showmeta -s http://me.com/cloudify_script_plugin-1.2-py27-none-any-none-none.wgn
```


## Testing

NOTE: Running the tests require an internet connection

```shell
git clone git@github.com:cloudify-cosmo/cloff.git
cd cloff
pip install tox
tox
```

## Contributions..

..are always welcome.