#!/usr/bin/python
# Copyright (c) 2013-2015 Daniel Hiltgen

import argparse
import datetime
import glob
import logging
import os
import re

log = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "home_automation.settings")
from sensor_data.models import Sensor, Reading
from django.utils.timezone import utc


def main():
    """
    Process a queue of sensor readings and load them into the DB

    After each reading is succesfully processed, the file will
    be removed.  The files in the queue directory should abide
    by the following pattern.  <seconds_since_epoch>.<sensor name>
    and the content within the file will be read as a float.
    """

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('--verbose', action="store_true",
                        help="Crank up the logging")
    parser.add_argument('--dry-run', action="store_true",
                        help="Don't actually the queue, just show what "
                        "would happen")
    parser.add_argument('--queue', required=True,
                        help="The queue directory")
    # TODO - Add arguments to tweak the timezone which we interpret
    #        epoch from
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    log.debug('Known sensors: %r', [s.name for s in Sensor.objects.all()])

    for filename in glob.glob(args.queue + '/*'):
        m = re.search(r'(\d+)\.(.+)', filename)
        assert m, "Filename %r didn't match expected pattern" % (filename)
        # We assume the readings are reported with UTC Epoch times
        dt = datetime.datetime.fromtimestamp(int(m.group(1))).replace(
            tzinfo=utc)
        with open(filename, 'r') as fd:
            try:
                raw_val = fd.read().strip()
                val = float(raw_val)
            except:
                log.exception("Unable to process %r - %r",
                              filename, raw_val)
                continue
        log.debug("Processing %r = %r", filename, val)
        s = Sensor.objects.get(name=m.group(2))
        if args.dry_run:
            log.info('Would be storing reading: %r %r %r',
                     s.name, str(dt), val)
        else:
            r = Reading(sensor=s, ts=dt, value=val)
            r.save()
            os.unlink(filename)


if __name__ == "__main__":
    main()
