import os

data = [
    ('Back lawn (middle)', '/29.B72E08000000/PIO.1'),
    ('Back Lawn (front)', '/29.B72E08000000/PIO.4'),
    ('Blueberries', '/29.B72E08000000/PIO.2'),
    ('Roses', '/29.B72E08000000/PIO.3'),
    ('Garden', '/29.B72E08000000/PIO.5'),
    ('Entry', '/29.F6F307000000/PIO.4'),
    ('Front Lawn', '/29.F6F307000000/PIO.6'),
    ('Driveway', '/29.F6F307000000/PIO.1'),
    ('Fruit Trees', '/29.F6F307000000/PIO.5'),
    ('Unused', '/29.F6F307000000/PIO.0')
    ('Entry', '/29.F6F307000000/PIO.5'),
    ('Front Lawn', '/29.F6F307000000/PIO.1'),
    ('Driveway', '/29.F6F307000000/PIO.0'),
    ('Fruit Trees', '/29.F6F307000000/PIO.4'),
    ('Street Ivy', '/29.F6F307000000/PIO.6')
    # ('Entry', '/29.F6F307000000/PIO.4'),
    # ('Front Lawn', '/29.F6F307000000/PIO.6'),
    # ('Driveway', '/29.F6F307000000/PIO.1'),
    # ('Fruit Trees', '/29.F6F307000000/PIO.5'),
    # ('Unused', '/29.F6F307000000/PIO.0')
]


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "home_automation.settings")
    from sprinklers.models import Circuit

    for d in data:
       try:
           old = Circuit.objects.filter(path=d[1])[0]
            print 'Updating', d[0]
            old.label = d[0]
            old.save()
        except:
            print 'Creating', d[0]
            c = Circuit(label=d[0], path=d[1])
            c.save()
