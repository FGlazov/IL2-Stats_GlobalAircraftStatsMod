from datetime import timedelta

from django.conf import settings
from django.db.models import Q, Sum
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from mission_report.constants import Coalition

from stats.helpers import Paginator, get_sort_by, redirect_fix_url
from stats.models import (Player, Mission, PlayerMission, PlayerAircraft, Sortie, KillboardPvP,
                          Tour, LogEntry, Profile, Squad, Reward, PlayerOnline, VLife)
from stats import sortie_log
from stats.views import *
from .aircraft_mod_models import AircraftBucket, AircraftKillboard, compute_float

aircraft_sort_fields = ['total_sorties', 'total_flight_time', 'kd', 'khr', 'gkd', 'gkhr', 'accuracy',
                        'bomb_rocket_accuracy', 'plane_survivability', 'pilot_survivability', 'plane_lethality',
                        'pilot_lethality', 'elo', 'rating']
aircraft_killboard_sort_fields = ['kills', 'assists', 'deaths', 'kdr', 'plane_survivability', 'pilot_survivability',
                                  'plane_lethality', 'pilot_lethality']
ITEMS_PER_PAGE = 20


def all_aircraft(request):
    page = request.GET.get('page', 1)
    search = request.GET.get('search', '').strip()
    sort_by = get_sort_by(request=request, sort_fields=aircraft_sort_fields, default='-rating')
    buckets = AircraftBucket.objects.filter(tour_id=request.tour.id, filter_type='NO_FILTER').order_by(sort_by, 'id')
    if search:
        buckets = buckets.filter(aircraft__name__icontains=search)

    buckets = Paginator(buckets, ITEMS_PER_PAGE).page(page)

    return render(request, 'all_aircraft.html', {
        'all_aircraft': buckets,
    })


def aircraft(request, aircraft_id):
    bucket = find_aircraft_bucket(aircraft_id, request.GET.get('tour'))
    if bucket is None:
        # TODO: Create this html.
        return render(request, 'aircraft_does_not_exist.html')

    return render(request, 'aircraft.html', {
        'aircraft_bucket': bucket,
    })


def aircraft_killboard(request, aircraft_id):
    tour_id = request.GET.get('tour')
    bucket = find_aircraft_bucket(aircraft_id, tour_id)
    if bucket is None:
        return render(request, 'aircraft_does_not_exist.html')
    aircraft_id = int(aircraft_id)

    unsorted_killboard = (AircraftKillboard.objects
                          .select_related('aircraft_1', 'aircraft_2')
                          .filter(Q(aircraft_1_id=aircraft_id) | Q(aircraft_2_id=aircraft_id),
                                  # Edge case: Killboards with only assists/distinct hits. Look strange.
                                  Q(aircraft_1_shotdown__gt=0) | Q(aircraft_2_shotdown__gt=0),
                                  tour__id=tour_id,
                                  ))

    killboard = []
    for k in unsorted_killboard:
        if k.aircraft_1.id == aircraft_id:
            killboard.append(
                {'aircraft': k.aircraft_2,
                 'kills': k.aircraft_1_shotdown,
                 'deaths': k.aircraft_2_shotdown,
                 'kdr': compute_float(k.aircraft_1_shotdown, k.aircraft_2_shotdown),
                 'plane_survivability': round(
                     100.0 - compute_float((k.aircraft_2_shotdown + k.aircraft_2_assists) * 100,
                                           k.aircraft_2_distinct_hits), 2),
                 'pilot_survivability': round(
                     100.0 - compute_float((k.aircraft_2_kills + k.aircraft_2_pk_assists) * 100,
                                           k.aircraft_2_distinct_hits), 2),
                 'plane_lethality': compute_float((k.aircraft_1_shotdown + k.aircraft_1_assists) * 100,
                                                  k.aircraft_1_distinct_hits),
                 'pilot_lethality': compute_float((k.aircraft_1_kills + k.aircraft_1_pk_assists) * 100,
                                                  k.aircraft_1_distinct_hits),
                 'url': k.get_aircraft_url(2),
                 }
            )
        else:
            killboard.append(
                {'aircraft': k.aircraft_1,
                 'kills': k.aircraft_2_shotdown,
                 'deaths': k.aircraft_1_shotdown,
                 'kdr': compute_float(k.aircraft_2_shotdown, k.aircraft_1_shotdown),
                 'plane_survivability': round(
                     100.0 - compute_float((k.aircraft_1_shotdown + k.aircraft_1_assists) * 100,
                                           k.aircraft_1_distinct_hits), 2),
                 'pilot_survivability': round(
                     100.0 - compute_float((k.aircraft_1_kills + k.aircraft_1_pk_assists) * 100,
                                           k.aircraft_1_distinct_hits), 2),
                 'plane_lethality': compute_float((k.aircraft_2_shotdown + k.aircraft_2_assists) * 100,
                                                  k.aircraft_2_distinct_hits),
                 'pilot_lethality': compute_float((k.aircraft_2_kills + k.aircraft_2_pk_assists) * 100,
                                                  k.aircraft_2_distinct_hits),
                 'url': k.get_aircraft_url(1),
                 }
            )

    _sort_by = get_sort_by(request=request, sort_fields=aircraft_killboard_sort_fields, default='-kdr')
    sort_reverse = True if _sort_by.startswith('-') else False
    sort_by = _sort_by.replace('-', '')
    killboard = sorted(killboard, key=lambda x: x[sort_by], reverse=sort_reverse)

    return render(request, 'aircraft_killboard.html', {
        'aircraft_bucket': bucket,
        'killboard': killboard,
    })


def find_aircraft_bucket(aircraft_id, tour_id, bucket_filter='NO_FILTER'):
    if tour_id:
        try:
            bucket = (AircraftBucket.objects.select_related('aircraft', 'tour')
                      .get(aircraft=aircraft_id, tour_id=tour_id, filter_type=bucket_filter))
        except AircraftBucket.DoesNotExist:
            bucket = None
    else:
        try:
            bucket = (AircraftBucket.objects.select_related('aircraft', 'tour')
                      .filter(aircraft=aircraft_id, filter_type=bucket_filter)
                      .order_by('-id'))[0]
        except IndexError:
            raise Http404
    return bucket
