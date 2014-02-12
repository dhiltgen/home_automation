#!/usr/bin/python


# Start a sprinkler for a given duration

import argparse
import logging
import os
import sys

log = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "home_automation.settings")
from sprinklers.models import Circuit


def main():
    parser = argparse.ArgumentParser(description="Start sprinklers")
    parser.add_argument('--start',
                        help='The name of the sprinkler circuit')
    parser.add_argument('--duration',
                        help='how many minutes to water')

    args = parser.parse_args()

    if args.start is None:
        print 'Available circuits are',
        print ', '.join([x.label for x in Circuit.objects.all()])
        sys.exit(0)

    circuit = Circuit.objects.filter(label=args.start)[0]
    circuit.start_watering(args.duration)
    circuit.save()


if __name__ == "__main__":
    #logging.basicConfig(level=logging.DEBUG)
    main()
