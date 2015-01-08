Home Automation
===============

This is the very early stages of a home automation system for sprinklers
and environment sensors.  The system is built up using django on top of
1-wire based sensors (running on Raspberry PI's, but any linux box should
do)  Ultimately the goal is to have smart sprinklers that can use rain,
temp, and humidity information to tailor the frequency and duration of
the watering cycles.


TODO
====

* Convert to using class based views
 * https://docs.djangoproject.com/en/1.7/topics/class-based-views/intro/
* Unit tests
* More sprinkler smarts
* Consolidate old historical readings to high/low for each day


# Wipe old data

    python ./manage.py flush

# sync up the DB schema

    python ./manage.py syncdb

# Load the known sprinkler circuits

    python ./loadCircuits.py

# Migrate data from the old DB

    python ./migrateData.py

# Run the server and see what happens...

    python ./manage.py runserver

# Dump historical data out to migrate between systems

    python ./manage.py dumpdata --indent 4 > dump.json
    python ./manage.py loaddata dump.json

# Create the user

    sudo -u postgres createuser -D -A -P automation
    sudo -u postgres createdb -O automation home_automation

# Poke around in the raw DB:

    psql -h localhost -W home_automation automation
    \dt

# Occasionally:

    python manage.py collectstatic

