# cloff
Cloudify Offline


Cloudify allows to create a tar file containing whatever you need to bootstrap Cloudify offline.

It:

* Downloads all relevant resources.
* Runs a webserver serving all of those resources.
* Modifies the manager blueprints to turn to the webserver when bootstrapping
