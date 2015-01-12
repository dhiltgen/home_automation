#!/usr/bin/python
# Copyright (c) 2013-2015 Daniel Hiltgen

from pytz import timezone
import argparse
import datetime
import httplib
import logging
import os
import xml.etree.ElementTree as ET


log = logging.getLogger(__name__)


# TODO - Drive this from some configuration file
lon = "-122.11"
lat = "37.40"
my_timezone = timezone('US/Pacific')

server = "graphical.weather.gov"
url = "/xml/sample_products/browser_interface/ndfdXMLclient.php?lat=" + \
    lat + "&lon=" + lon + "&product=time-series&mint=mint&maxt=maxt"


def main():
    """
    Query the national weather service, and record their predictions in the DB
    """
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('--verbose', action="store_true",
                        help="Crank up the logging")
    parser.add_argument('--dry-run', action="store_true",
                        help="Don't actually save the data")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "home_automation.settings")
    from sensor_data.models import Prediction
    from django.db import transaction

    connection = httplib.HTTPConnection(server)
    connection.request("GET", url)
    docRoot = ET.fromstring(connection.getresponse().read())
    connection.close()
    mins = [n.text for n in docRoot.findall(
            "./data/parameters/temperature[@type='minimum']/value")]
    maxs = [n.text for n in docRoot.findall(
            "./data/parameters/temperature[@type='maximum']/value")]

    # If we query too early in the day we'll only get 6
    if len(mins) == 6:
        mins.append(None)
    elif len(mins) < 6:
        raise Exception("NWS only returned %d predictions" % (len(mins)))
    if len(maxs) == 6:
        maxs.append(None)
    elif len(maxs) < 6:
        raise Exception("NWS only returned %d predictions" % (len(mins)))

    ts = datetime.datetime.now().replace(tzinfo=my_timezone)

    with transaction.commit_on_success():
        r = Prediction(ts=ts,
                       min1=mins[0],
                       min2=mins[1],
                       min3=mins[2],
                       min4=mins[3],
                       min5=mins[4],
                       min6=mins[5],
                       min7=mins[6],
                       max1=maxs[0],
                       max2=maxs[1],
                       max3=maxs[2],
                       max4=maxs[3],
                       max5=maxs[4],
                       max6=maxs[5],
                       max7=maxs[6])
        log.debug("Predictions: %s", r)
        if not args.dry_run:
            r.save()


if __name__ == "__main__":
    main()
