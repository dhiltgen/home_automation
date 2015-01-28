import subprocess
import logging


# TODO - Decouple this so it can active remote sprinklers


log = logging.getLogger(__name__)


# Python 2.6 on the Pi's lacks check_output
# Remove this once uwsgi on rpi syncs up to python 2.7
def check_output(*popenargs, **kwargs):
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        error = subprocess.CalledProcessError(retcode, cmd)
        error.output = output
        raise error
    return output


def get_state(path):
    """
    Query the known sensor, and update their current state from live data
    """
    if path == '':
        log.debug("Empty circuit path, doing no-op")
        return 0
    return int(check_output(['/usr/bin/owread', path]))


def stop(path):
    if path == '':
        log.debug("Empty circuit path, doing no-op")
        return
    subprocess.check_call(['/usr/bin/owwrite', path, '0'])


def start(path):
    if path == '':
        log.debug("Empty circuit path, doing no-op")
        return
    subprocess.check_call(['/usr/bin/owwrite', path, '1'])
