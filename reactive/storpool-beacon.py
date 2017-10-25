"""
A Juju charm layer that installs the `storpool_beacon` service.
"""
from __future__ import print_function

from charms import reactive
from charmhelpers.core import hookenv, host

from spcharms import repo as sprepo
from spcharms import utils as sputils


def rdebug(s):
    """
    Pass the diagnostic message string `s` to the central diagnostic logger.
    """
    sputils.rdebug(s, prefix='beacon')


@reactive.when('storpool-repo-add.available', 'storpool-common.config-written')
@reactive.when_not('storpool-beacon.package-installed')
@reactive.when_not('storpool-beacon.stopped')
def install_package():
    """
    Install the `storpool_beacon` package.
    """
    rdebug('the beacon repo has become available and '
           'the common packages have been configured')
    if sputils.check_in_lxc():
        rdebug('running in an LXC container, not doing anything more')
        reactive.set_state('storpool-beacon.package-installed')
        return

    hookenv.status_set('maintenance',
                       'obtaining the requested StorPool version')
    spver = hookenv.config().get('storpool_version', None)
    if spver is None or spver == '':
        rdebug('no storpool_version key in the charm config yet')
        return

    hookenv.status_set('maintenance',
                       'installing the StorPool beacon packages')
    (err, newly_installed) = sprepo.install_packages({
        'storpool-beacon': spver,
    })
    if err is not None:
        rdebug('oof, we could not install packages: {err}'.format(err=err))
        rdebug('removing the package-installed state')
        return

    if newly_installed:
        rdebug('it seems we managed to install some packages: {names}'
               .format(names=newly_installed))
        sprepo.record_packages('storpool-beacon', newly_installed)
    else:
        rdebug('it seems that all the packages were installed already')

    rdebug('setting the package-installed state')
    reactive.set_state('storpool-beacon.package-installed')
    hookenv.status_set('maintenance', '')


@reactive.when('storpool-beacon.package-installed')
@reactive.when_not('storpool-beacon.beacon-started')
@reactive.when_not('storpool-beacon.stopped')
def enable_and_start():
    """
    Enable and start the `storpool_beacon` service.
    """
    if sputils.check_in_lxc():
        rdebug('running in an LXC container, not doing anything more')
        reactive.set_state('storpool-beacon.beacon-started')
        return

    rdebug('enabling and starting the beacon service')
    host.service_resume('storpool_beacon')
    reactive.set_state('storpool-beacon.beacon-started')


@reactive.when('storpool-beacon.beacon-started')
@reactive.when_not('storpool-beacon.package-installed')
@reactive.when_not('storpool-beacon.stopped')
def restart():
    """
    Trigger a restart of the `storpool_beacon` service.
    """
    reactive.remove_state('storpool-beacon.beacon-started')


@reactive.when('storpool-beacon.package-installed')
@reactive.when_not('storpool-common.config-written')
@reactive.when_not('storpool-beacon.stopped')
def reinstall():
    """
    Trigger a reinstallation of the `storpool_beacon` package.
    """
    reactive.remove_state('storpool-beacon.package-installed')


def reset_states():
    """
    Trigger a full reinstall-restart cycle.
    """
    rdebug('state reset requested')
    reactive.remove_state('storpool-beacon.package-installed')
    reactive.remove_state('storpool-beacon.beacon-started')


@reactive.hook('upgrade-charm')
def remove_states_on_upgrade():
    """
    Reinstall and restart upon charm upgrade.
    """
    rdebug('storpool-beacon.upgrade-charm invoked')
    reset_states()


@reactive.when('storpool-beacon.stop')
@reactive.when_not('storpool-beacon.stopped')
def remove_leftovers():
    """
    Clean up, disable the service, uninstall the packages.
    """
    rdebug('storpool-beacon.stop invoked')
    reactive.remove_state('storpool-beacon.stop')

    if not sputils.check_in_lxc():
        rdebug('stopping and disabling the storpool_beacon service')
        host.service_pause('storpool_beacon')

        rdebug('uninstalling any beacon-related packages')
        sprepo.unrecord_packages('storpool-beacon')

    rdebug('letting storpool-common know')
    reactive.set_state('storpool-common.stop')

    reset_states()
    reactive.set_state('storpool-beacon.stopped')
