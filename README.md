Home Automation
===============

This is a home automation system for sprinklers and environment sensors.
The system is built up using django on top of 1-wire based sensors
(running on Raspberry PI's, but any linux box should do.)

The watering cycles are designed to be "smart."  For each circuit we
establish the amount of water delivered per hour (typically inches/hour
but units are configurable.)  For typical lawn sprinklers, this can
be easily determined by placing a plastic cup on the lawn, and running
the circuit for 10 or 15 minutes, then measuing the amount of water in
the cup, and extrapolating the amount delivered in an hour.  Then look
up the recommended amount of water per week for your type of grass
(or plants) for you general climate.  Then pick how many days/hours to
wait between cycles.  For example, with lawns, deeper watering less
frequently will result in deeper root systems and more hearty lawns.
For vegitable gardens, young plants wont have deep root systems so you'll
need to water more frequenty.

Once watering rate, target amount per week, and time between cycles is
known, then the system can deliver the optimal amount of water for the
circuit.  Over time, you can tweak the goal based on how the plants look
(e.g., increase if they're getting brown, decrease if they're growing
too quickly.)

In addition, if a rain guage is wired up, the system will record rain
volume against each circuit so watering can be avoided when mother nature
takes care of it for us.


TODO
====

* Add temperature/humidity modifier for circuits - if temps are low, water
  less, if temps are high, water a bit more.
* Consolidate old historical temp/humidity sensor readings to just daily
  high/low to improve performance on low-power systems like RasberryPIs
* Convert initial bootstrap logic from hard-coded scripts to
  configuration driven
* Further decoupling of the 1-wire logic for sprinkler circuits
  so they can be driven by a remote instance of the app


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
    sudo -u postgres  psql -c "ALTER USER automation CREATEDB;"
    sudo -u postgres createdb -O automation home_automation

# Poke around in the raw DB:

    psql -h localhost -W home_automation automation
    \dt

# Run Tests

    python-coverage run --source='.' manage.py test
    python-coverage report -m

