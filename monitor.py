#!/usr/bin/python

import argparse
import glob
import json
import logging
import os
import subprocess
import sys
import time

log = logging.getLogger(__name__)


def main():
    """
    Read one or more sensors, queue, and upload to one or more servers.

    ssh must be configured to use public key based login (not passwords.)
    Once the config has been set up, this can be added to crontab with
    something like "*/5 * * * * /usr/bin/python <this script>"
    """
    home = os.environ.get('HOME', ".")
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('--conf', default=home+"/sensors.json",
                        help="The local json config file for this system")
    parser.add_argument('--verbose', action="store_true",
                        help="Turn on verbose output")
    args = parser.parse_args()

    # Get UTC epoch time
    now = time.mktime(time.gmtime(time.time()))
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if not os.path.exists(args.conf):
        print 'ERROR: No configuration exists - creating template\n'
        print 'Please edit %r for your local configuration' % (args.conf)
        conf = dict(
            sensors=[
                dict(
                    name="Example Sensor Name",
                    path="/26.489A21010000/temperature",
                ),
            ],
            servers=[
                dict(
                    port="22",
                    host="servername",
                    local_queue="/path/to/local/queue",
                    remote_queue="/path/to/remote/queue",
                ),
            ],
        )
        with open(args.conf, "w") as fd:
            fd.write(json.dumps(conf,
                                sort_keys=True,
                                indent=4, separators=(',', ': ')))

        sys.exit(1)

    with open(args.conf, "r") as fd:
        conf = json.loads(fd.read())

    # Gather the readings...
    for sensor in conf['sensors']:
        sensor['val'] = str(subprocess.check_output([
            'owread', '-F', sensor['path']])).strip()
        log.debug("Sensor %r current reading %r", sensor['name'],
                  sensor['val'])

    # Now update each servers queues
    for server in conf['servers']:
        if not os.path.exists(server['local_queue']):
            os.makedirs(server['local_queue'])
        for sensor in conf['sensors']:
            filename = server['local_queue'] + '/%d.%s' % (
                int(now), sensor['name'])
            with open(filename, "w") as reading:
                reading.write(str(sensor['val']))

    # And finally drain the queues
    for server in conf['servers']:
        # Clearly not as efficient as bulk upload, but
        # by doing one at a time we simplify keeping
        # everything in sync
        for reading_filename in glob.glob(server['local_queue'] + "/*"):
            try:
                output = subprocess.check_output([
                    "scp", "-P", str(server['port']),
                    reading_filename,
                    "%s:%s/" % (server['host'], server['remote_queue'])])
                if output:
                    log.info(output)
                os.unlink(reading_filename)
            except subprocess.CalledProcessError as e:
                log.warning("Failed to upload %r - %s", reading_filename,
                            e.output)
                log.warning("Will try again later")


if __name__ == "__main__":
    main()
