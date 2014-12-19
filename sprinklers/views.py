# Create your views here.
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
#from django.template import RequestContext
from django.core.urlresolvers import reverse
from sprinklers.models import Circuit
from sensor_data.models import Sensor, Reading, Prediction
import sensor_data.cumulative as cumulative


#def index(request):
#    circuits = Circuit.objects.all().order_by('label')
#    return render_to_response('sprinklers/index.html',
#                              { 'circuits': circuits })


#def details(request, circuit_id):
#    c = get_object_or_404(Circuit, pk=circuit_id)
#    return render_to_response('sprinklers/detail.html', { 'circuit': c },
#                              context_instance=RequestContext(request))

def update(request, circuit_id):
    c = get_object_or_404(Circuit, pk=circuit_id)
    print 'XXX POST details:', request.POST
    if request.POST['action'] == 'start':
        c.start_watering(request.POST['duration'])
    elif request.POST['action'] == 'stop':
        c.stop_watering()
    else:
        raise Exception("Raise someting better...")
    c.save()
    return HttpResponseRedirect(reverse('circuit_details', args=(c.id,)))


def summary(request):
    results = dict()
    results['circuits'] = Circuit.objects.all().order_by('label')
    sensors = []
    for sensor in Sensor.objects.all().order_by('name'):
        if sensor.sensor_type == 'R':
            sensor.units = ' inches (this season)'
            start = cumulative.get_season_start()
            old = Reading.objects.order_by('ts').filter(
                sensor_id=sensor.id).filter(ts__gt=start)[0]
            latest = Reading.objects.filter(
                sensor_id=sensor.id).latest('ts')
            latest.value = float(latest.value - old.value) * 0.01
            sensors.append(dict(metadata=sensor, reading=latest))
        else:
            if 'fahrenheit' in sensor.units:
                sensor.units = u"\xb0F"
            elif 'percent' in sensor.units:
                sensor.units = "%"
            sensors.append(dict(
                metadata=sensor, reading=Reading.objects.filter(
                    sensor_id=sensor.id).latest('ts')))
    prediction = Prediction.objects.latest('ts')

    results['sensors'] = sensors
    results['prediction'] = prediction
    return render_to_response('overview.html', results)
