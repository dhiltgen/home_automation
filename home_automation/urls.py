from django.conf.urls import patterns, include, url
from django.views.generic import DetailView, ListView
from sprinklers.models import Circuit, detect_current_state
from sensor_data.views import CellarCurrent, OutsideCurrent, CellarSummary, \
    OutsideSummary, CellarDetail, OutsideDetail


# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

# Make sure we have current state from the sprinklers
detect_current_state()

urlpatterns = patterns(
    '',
    url(r'^$', 'sprinklers.views.summary', name='overview'),

    url(r'^circuits/$',
        ListView.as_view(
            queryset=Circuit.objects.order_by('label'),
            context_object_name='circuits',  # Default would be poll_list
            template_name='sprinklers/index.html'),
        name='circuits'),
    url(r'^circuits/(?P<pk>\d+)/$',
        DetailView.as_view(
            model=Circuit,
            template_name='sprinklers/detail.html'),
        name='circuit_details'),
    url(r'^circuits/(?P<circuit_id>\d+)/update/$', 'sprinklers.views.update'),

    url(r'^outside$', OutsideCurrent.as_view(), name='outside_current'),
    url(r'^outside/detail/'
        '(?P<days>\d+)$',
        OutsideDetail.as_view(), name='outside_detail'),
    url(r'^outside/summary/'
        '(?P<days>\d+)$',
        OutsideSummary.as_view(), name='outside_summary'),
    url(r'^outside/ytd/$',
        OutsideSummary.as_view(), name='outside_ytd'),

    url(r'^cellar$', CellarCurrent.as_view(), name='cellar_current'),
    url(r'^cellar/detail/'
        '(?P<days>\d+)$',
        CellarDetail.as_view(), name='cellar_detail'),
    url(r'^cellar/summary/'
        '(?P<days>\d+)$',
        CellarSummary.as_view(), name='cellar_summary'),
    url(r'^cellar/ytd/$',
        CellarSummary.as_view(), name='cellar_ytd'),

    url(r'^rain$', 'sensor_data.views.rain_data', name='rain_summary'),
    url(r'^rain/season/$', 'sensor_data.views.rain_data', name='rain_season'),
    url(r'^rain/'
        '(?P<days>\d+)$',
        'sensor_data.views.rain_data', name='rain_details'),
    url(r'^rain/ytd/$',
        'sensor_data.views.rain_ytd', name='rain_ytd'),
)
urlpatterns += patterns(
    '',
    url(r'^admin/', include(admin.site.urls)),
)
