#!/usr/bin/python


# Query the national weather service, and record their predictions in the DB


import datetime
import httplib
import xml.etree.ElementTree as ET
from pytz import timezone

lon="-122.11"
lat="37.40"
server="graphical.weather.gov"
url="/xml/sample_products/browser_interface/ndfdXMLclient.php?lat="+lat+"&lon="+lon+"&product=time-series&mint=mint&maxt=maxt"

import os
import sys
import datetime

pacific = timezone('US/Pacific')

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "home_automation.settings")
    from sensor_data.models import Sensor, Reading, Prediction
    from django.utils.timezone import utc
    from django.db import transaction


    connection = httplib.HTTPConnection(server)
    connection.request("GET", url)
    docRoot = ET.fromstring(connection.getresponse().read())
    connection.close()
    mins = []
    maxs = []
    for node in docRoot.findall("./data/parameters/temperature[@type='minimum']/value"):
        mins.append(node.text)

    for node in docRoot.findall("./data/parameters/temperature[@type='maximum']/value"):
        maxs.append(node.text)

    # Should probably harden to just fill in blanks if it's short...
    assert(len(mins) >= 7)
    assert(len(maxs) >= 7)

    when = datetime.datetime.now().replace(tzinfo=pacific)

    with transaction.commit_on_success():
        r = Prediction(when=when,
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
        r.save()

