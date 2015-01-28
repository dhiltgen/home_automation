#!/usr/bin/env python
# Copyright (c) 2013-2015 Daniel Hiltgen

#
# TODO - Get rid of this and load this from
#        some sort of configuration file
#

import os

data = [
    # Label, path, target, rate, spacing(Days)
    ('Back lawn (rear)', '/29.B72E08000000/PIO.0', '1.5', '4.0', 5),
    ('Back lawn (middle)', '/29.B72E08000000/PIO.1', '1.5', '4.0', 5),
    ('Back Lawn (front)', '/29.B72E08000000/PIO.4', '1.5', '4.0', 5),
    ('Blueberries', '/29.B72E08000000/PIO.2', '1.0', '6.5', 3),
    ('Roses', '/29.B72E08000000/PIO.3', '1.0', '6.5', 3),
    ('Garden', '/29.B72E08000000/PIO.5', '1.0', '6.5', 3),

    ('Entry', '/29.F6F307000000/PIO.5', '1.0', '4.0', 5),
    ('Front Lawn', '/29.F6F307000000/PIO.1', '1.0', '4.0', 5),
    ('Driveway', '/29.F6F307000000/PIO.0', '1.0', '4.0', 5),
    ('Fruit Trees', '/29.F6F307000000/PIO.4', '3.0', '6.5', 5),
    ('Street Ivy', '/29.F6F307000000/PIO.6', '1.0', '4.0', 5)
]


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "home_automation.settings")
    from sprinklers.models import Circuit

    for d in data:
        try:
            old = Circuit.objects.filter(path=d[1])[0]
            print 'Updating', d[0]
            old.label = d[0]
            old.target_wk = str(d[2])
            old.rate_hr = str(d[3])
            old.spacing_hr = int(d[4])*24
            old.save()
        except:
            print 'Creating', d[0]
            c = Circuit(label=d[0], path=d[1])
            c.target_wk = str(d[2])
            c.rate_hr = str(d[3])
            c.spacing_hr = int(d[4])*24
            c.save()
