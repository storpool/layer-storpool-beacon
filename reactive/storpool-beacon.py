from __future__ import print_function

import pwd
import os
import tempfile
import time
import subprocess

from charmhelpers.core import templating

from charms import reactive
from charms.reactive import helpers as rhelpers
from charmhelpers.core import hookenv

from spcharms import repo as sprepo

def rdebug(s):
	with open('/tmp/storpool-charms.log', 'a') as f:
		print('{tm} [beacon] {s}'.format(tm=time.ctime(), s=s), file=f)

@reactive.when('storpool-repo-add.available', 'storpool-config.config-written')
@reactive.when_not('storpool-beacon.package-installed')
def install_package():
	rdebug('the beacon repo has become available and we do have the configuration')
	hookenv.status_set('maintenance', 'installing the StorPool beacon packages')
	(err, newly_installed) = sprepo.install_packages({
		'storpool-beacon': '16.02.25.744ebef-1ubuntu1',
	})
	if err is not None:
		rdebug('oof, we could not install packages: {err}'.format(err=err))
		rdebug('removing the package-installed state')
		return

	if newly_installed:
		rdebug('it seems we managed to install some packages: {names}'.format(names=newly_installed))
		sprepo.record_packages(newly_installed)
	else:
		rdebug('it seems that all the packages were installed already')

	rdebug('setting the package-installed state')
	reactive.set_state('storpool-beacon.package-installed')
	hookenv.status_set('maintenance', '')

@reactive.when('storpool-config.config-written', 'storpool-beacon.package-installed')
@reactive.when('storpool-beacon.start-beacon')
@reactive.when_not('storpool-beacon.beacon-started')
def hmf():
	rdebug('FIXME: try to start the beacon?')

@reactive.when('storpool-beacon.package-installed')
@reactive.when_not('storpool-config.config-written')
def reinstall():
	reactive.remove_state('storpool-beacon.package-installed')

@reactive.hook('stop')
def remove_leftovers():
	rdebug('storpool-beacon.stop invoked')
	reactive.remove_state('storpool-beacon.package-installed')
	rdebug('FIXME: disable a service or something?')
