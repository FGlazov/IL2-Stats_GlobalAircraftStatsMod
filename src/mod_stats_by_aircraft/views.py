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
from stats.views import (_get_rating_position, _get_squad, pilot_vlife, pilot_vlifes, online, mission, missions_list,
                         pilot_sortie_log, pilot_sortie, pilot_sorties, pilot_killboard, pilot_awards, pilot_rankings,
                         squad_rankings, squad, squad_pilots, pilot, main)
from .aircraft_mod_models import AircraftBucket, AircraftKillboard, SortieAugmentation

aircraft_sort_fields = ['total_sorties', 'total_flight_time', 'kd', 'khr', 'gkd', 'gkhr' 'accuracy',
                        'bomb_rocket_accuracy', 'plane_survivability','pilot_survivability', 'plane_lethality',
                        'pilot_lethality', 'elo', 'rating']
ITEMS_PER_PAGE = 20


# TODO Write actual new stats functions.

def all_aircraft(request):
    page = request.GET.get('page', 1)
    search = request.GET.get('search', '').strip()
    sort_by = get_sort_by(request=request, sort_fields=aircraft_sort_fields, default='-rating')
    all_aircraft = AircraftBucket.objects.filter(tour_id=request.tour.id).order_by(sort_by, 'id')

    # TODO: Implement search
    all_aircraft = Paginator(all_aircraft, ITEMS_PER_PAGE).page(page)

    return render(request, 'all_aircraft.html', {
        'all_aircraft': all_aircraft,
    })


def aircraft(request, aircraft_id):
    return render(request, 'aircraft.html')


def aircraft_killboard(request, aircraft_id):
    return render(request, 'aircraft_killboard.html')
