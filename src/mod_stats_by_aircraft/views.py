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

# TODO Write actual new stats functions.

def all_aircraft(request):
    return render(request, 'all_aircraft.html')