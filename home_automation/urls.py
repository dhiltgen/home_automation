from django.conf.urls import patterns, include, url
from django.views.generic import DetailView, ListView
from sprinklers.models import Circuit, detect_current_state


# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

# Make sure we have current state from the sprinklers
detect_current_state()

urlpatterns = patterns('',
    url(r'^$', 'sprinklers.views.summary', name='overview'),
    url(r'^circuits/$',
        ListView.as_view(
        queryset=Circuit.objects.order_by('label'),
        context_object_name='circuits',  # Default would be poll_list
        template_name='sprinklers/index.html')),
    url(r'^circuits/(?P<pk>\d+)/$',
        DetailView.as_view(
        model=Circuit,
        template_name='sprinklers/detail.html'),
        name='circuit_details'),
    url(r'^circuits/(?P<circuit_id>\d+)/update/$', 'sprinklers.views.update'),
    url(r'^outside$', 'sensor_data.views.outside_current', name='outside_current'),
    url(r'^outside/detail/'
        '(?P<start_year>\d\d\d\d)-(?P<start_month>\d\d)-(?P<start_day>\d\d) '
        '(?P<start_hour>\d\d):(?P<start_minute>\d\d):(?P<start_second>\d\d)\+'
        '(?P<tz_hour>\d\d):(?P<tz_minute>\d\d)_(?P<active_link>\S+)$', 'sensor_data.views.outside_detail', name='outside_detail'),
    url(r'^outside/detail/'
        '(?P<start_year>\d\d\d\d)-(?P<start_month>\d\d)-(?P<start_day>\d\d) '
        '(?P<start_hour>\d\d):(?P<start_minute>\d\d):(?P<start_second>\d\d)\+'
        '(?P<tz_hour>\d\d):(?P<tz_minute>\d\d)$', 'sensor_data.views.outside_detail', name='outside_detail'),
    url(r'^outside/summary/'
        '(?P<start_year>\d\d\d\d)-(?P<start_month>\d\d)-(?P<start_day>\d\d) '
        '(?P<start_hour>\d\d):(?P<start_minute>\d\d):(?P<start_second>\d\d)\+'
        '(?P<tz_hour>\d\d):(?P<tz_minute>\d\d)_(?P<active_link>\S+)$', 'sensor_data.views.outside_summary', name='outside_summary'),
    url(r'^outside/summary/'
        '(?P<start_year>\d\d\d\d)-(?P<start_month>\d\d)-(?P<start_day>\d\d) '
        '(?P<start_hour>\d\d):(?P<start_minute>\d\d):(?P<start_second>\d\d)\+'
        '(?P<tz_hour>\d\d):(?P<tz_minute>\d\d)$', 'sensor_data.views.outside_summary', name='outside_summary'),
)
urlpatterns += patterns('',
    url(r'^admin/', include(admin.site.urls)),
)
