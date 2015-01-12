#!/usr/bin/python
# Copyright (c) 2013-2015 Daniel Hiltgen


import argparse
import logging
import os

log = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "home_automation.settings")
from sprinklers.models import Circuit


def main():
    """
    Start a sprinkler for a given duration
    """
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('--verbose', action="store_true",
                        help="Crank up the logging")
    parser.add_argument('--start',
                        help='The name of the sprinkler circuit')
    parser.add_argument('--duration',
                        help='how many minutes to water')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.start is None:
        log.info('Available circuits are %s',
                 ', '.join(["%r" % str(x.label)
                            for x in Circuit.objects.all()]))
        return

    circuit = Circuit.objects.filter(label=args.start)[0]
    log.debug("Starting %r for %r", circuit.label, args.duration)
    circuit.start_watering(args.duration)
    circuit.save()


if __name__ == "__main__":
    main()
