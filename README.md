home_automation
===============

Nothing to see here (yet...)  Move along...


This is the very early stages of a home automation system for sprinklers
and environment sensors.  The system is built up using django on top of
1-wire based sensors (running on Raspberry PI's, but any linux box should
do)  Ultimately the goal is to have smart sprinklers that can use rain,
temp, and humidity information to tailor the frequency and duration of
the watering cycles.


python ./manage.py syncdb
python ./manage.py runserver
