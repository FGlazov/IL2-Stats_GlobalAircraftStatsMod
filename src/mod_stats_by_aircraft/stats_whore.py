import time
from stats.stats_whore import (stats_whore, cleanup, collect_mission_reports, update_status, update_general,
                               update_ammo, update_killboard, update_killboard_pvp, create_new_sortie, backup_log,
                               get_tour, update_fairplay, update_bonus_score, update_sortie, create_profiles)
from stats.rewards import reward_sortie, reward_tour, reward_mission, reward_vlife
from stats.logger import logger
from stats.online import update_online
from stats.models import LogEntry, Mission, PlayerMission, VLife, PlayerAircraft, Object, Score, Sortie
from users.utils import cleanup_registration
from django.conf import settings
from django.db.models import Q
from core import __version__
from .aircraft_mod_models import AircraftBucket, AircraftKillboard, SortieAugmentation
import sys
import django
import pytz
from datetime import datetime, timedelta
from types import MappingProxyType
from mission_report.report import MissionReport
from mission_report.statuses import LifeStatus
from collections import defaultdict
from django.db import transaction
import operator

MISSION_REPORT_BACKUP_PATH = settings.MISSION_REPORT_BACKUP_PATH
MISSION_REPORT_BACKUP_DAYS = settings.MISSION_REPORT_BACKUP_DAYS
MISSION_REPORT_DELETE = settings.MISSION_REPORT_DELETE
MISSION_REPORT_PATH = settings.MISSION_REPORT_PATH
NEW_TOUR_BY_MONTH = settings.NEW_TOUR_BY_MONTH
TIME_ZONE = pytz.timezone(settings.MISSION_REPORT_TZ)

WIN_BY_SCORE = settings.WIN_BY_SCORE
WIN_SCORE_MIN = settings.WIN_SCORE_MIN
WIN_SCORE_RATIO = settings.WIN_SCORE_RATIO
SORTIE_MIN_TIME = settings.SORTIE_MIN_TIME


def main():
    logger.info('IL2 stats {stats}, Python {python}, Django {django}'.format(
        stats=__version__, python=sys.version[0:5], django=django.get_version()))

    # TODO переделать на проверку по времени создания файлов
    processed_reports = []

    waiting_new_report = False
    online_timestamp = 0

    # ======================== MODDED PART BEGIN
    backfill_aircraft_by_stats = True
    backfill_log = True
    # ======================== MODDED PART END

    while True:
        new_reports = []
        for m_report_file in MISSION_REPORT_PATH.glob('missionReport*[[]0[]].txt'):
            if m_report_file.name not in processed_reports:
                new_reports.append(m_report_file)

        if len(new_reports) > 1:
            waiting_new_report = False
            # ======================== MODDED PART BEGIN
            backfill_log = True
            # ======================== MODDED PART END
            # обрабатываем все логи кроме последней миссии
            for m_report_file in new_reports[:-1]:
                stats_whore(m_report_file=m_report_file)
                cleanup(m_report_file=m_report_file)
                processed_reports.append(m_report_file.name)
            continue
        elif len(new_reports) == 1:
            m_report_file = new_reports[0]
            m_report_files = collect_mission_reports(m_report_file=m_report_file)
            online_timestamp = update_online(m_report_files=m_report_files, online_timestamp=online_timestamp)
            # если последний файл был создан более 2х минут назад - обрабатываем его
            if time.time() - m_report_files[-1].stat().st_mtime > 120:
                waiting_new_report = False
                # ======================== MODDED PART BEGIN
                backfill_log = True
                # ======================== MODDED PART END
                stats_whore(m_report_file=m_report_file)
                cleanup(m_report_file=m_report_file)
                processed_reports.append(m_report_file.name)
                continue
        # ======================== MODDED PART BEGIN
        elif backfill_aircraft_by_stats:
            work_done = process_old_sorties_batch_aircraft_stats(backfill_log)
            backfill_aircraft_by_stats = work_done
            backfill_log = False
            continue
        # ======================== MODDED PART END

        if not waiting_new_report:
            logger.info('waiting new report...')
        waiting_new_report = True

        # удаляем юзеров которые не активировали свои регистрации в течении определенного времени
        cleanup_registration()

        # в идеале новые логи появляются как минимум раз в 30 секунд
        time.sleep(30)


@transaction.atomic
def stats_whore(m_report_file):
    """
    :type m_report_file: Path
    """
    mission_timestamp = int(time.mktime(time.strptime(m_report_file.name[14:-8], '%Y-%m-%d_%H-%M-%S')))

    if Mission.objects.filter(timestamp=mission_timestamp).exists():
        logger.info('{mission} - exists in the DB'.format(mission=m_report_file.stem))
        return
    logger.info('{mission} - processing new report'.format(mission=m_report_file.stem))

    m_report_files = collect_mission_reports(m_report_file=m_report_file)

    real_date = TIME_ZONE.localize(datetime.fromtimestamp(mission_timestamp))
    real_date = real_date.astimezone(pytz.UTC)

    objects = MappingProxyType({obj['log_name']: obj for obj in Object.objects.values()})
    # classes = MappingProxyType({obj['cls']: obj['cls_base'] for obj in objects.values()})
    score_dict = MappingProxyType({s.key: s.get_value() for s in Score.objects.all()})

    m_report = MissionReport(objects=objects)
    m_report.processing(files=m_report_files)

    backup_log(name=m_report_file.name, lines=m_report.lines, date=real_date)

    if not m_report.is_correctly_completed:
        logger.info('{mission} - mission has not been completed correctly'.format(mission=m_report_file.stem))

    tour = get_tour(date=real_date)

    mission = Mission.objects.create(
        tour_id=tour.id,
        name=m_report.file_path.replace('\\', '/').split('/')[-1].rsplit('.', 1)[0],
        path=m_report.file_path,
        date_start=real_date,
        date_end=real_date + timedelta(seconds=m_report.tik_last // 50),
        duration=m_report.tik_last // 50,
        timestamp=mission_timestamp,
        preset=m_report.preset_id,
        settings=m_report.settings,
        is_correctly_completed=m_report.is_correctly_completed,
        score_dict=dict(score_dict),
    )
    if m_report.winning_coal_id:
        mission.winning_coalition = m_report.winning_coal_id
        mission.win_reason = 'task'
        mission.save()

    # собираем/создаем профили игроков и сквадов
    profiles, players_pilots, players_gunners, players_tankmans, squads = create_profiles(tour=tour,
                                                                                          sorties=m_report.sorties)

    players_aircraft = defaultdict(dict)
    players_mission = {}
    players_killboard = {}

    coalition_score = {1: 0, 2: 0}
    new_sorties = []
    for sortie in m_report.sorties:
        sortie_aircraft_id = objects[sortie.aircraft_name]['id']
        profile = profiles[sortie.account_id]
        if sortie.cls_base == 'aircraft':
            player = players_pilots[sortie.account_id]
        elif sortie.cls == 'aircraft_turret':
            player = players_gunners[sortie.account_id]
        elif sortie.cls in ('tank_light', 'tank_heavy', 'tank_medium', 'tank_turret'):
            player = players_tankmans[sortie.account_id]
        else:
            continue

        squad = squads[profile.squad_id] if profile.squad else None
        player.squad = squad

        new_sortie = create_new_sortie(mission=mission, sortie=sortie, profile=profile, player=player,
                                       sortie_aircraft_id=sortie_aircraft_id)
        update_fairplay(new_sortie=new_sortie)
        update_bonus_score(new_sortie=new_sortie)

        # не добавляем очки в сумму если было диско
        if not new_sortie.is_disco:
            coalition_score[new_sortie.coalition] += new_sortie.score

        new_sorties.append(new_sortie)
        # добавляем ссылку на запись в базе к объекту вылета, чтобы использовать в добавлении событий вылета
        sortie.sortie_db = new_sortie

    if not mission.winning_coalition and WIN_BY_SCORE:
        _coalition = sorted(coalition_score.items(), key=operator.itemgetter(1), reverse=True)
        max_coal, max_score = _coalition[0]
        min_coal, min_score = _coalition[1]
        # минимальное кол-во очков = 1
        min_score = min_score or 1
        if max_score >= WIN_SCORE_MIN and max_score / min_score >= WIN_SCORE_RATIO:
            mission.winning_coalition = max_coal
            mission.win_reason = 'score'
            mission.save()

    for new_sortie in new_sorties:
        _player_id = new_sortie.player.id
        _profile_id = new_sortie.profile.id

        player_mission = players_mission.setdefault(
            _player_id,
            PlayerMission.objects.get_or_create(profile_id=_profile_id, player_id=_player_id, mission_id=mission.id)[0]
        )

        player_aircraft = players_aircraft[_player_id].setdefault(
            new_sortie.aircraft.id,
            PlayerAircraft.objects.get_or_create(profile_id=_profile_id, player_id=_player_id,
                                                 aircraft_id=new_sortie.aircraft.id)[0]
        )

        vlife = VLife.objects.get_or_create(profile_id=_profile_id, player_id=_player_id, tour_id=tour.id, relive=0)[0]

        # если случилась победа по очкам - требуется обновить бонусы
        if mission.win_reason == 'score':
            update_bonus_score(new_sortie=new_sortie)

        update_sortie(new_sortie=new_sortie, player_mission=player_mission, player_aircraft=player_aircraft,
                      vlife=vlife)
        reward_sortie(sortie=new_sortie)

        vlife.save()
        reward_vlife(vlife)

        new_sortie.vlife_id = vlife.id
        new_sortie.save()

    # ===============================================================================
    mission.players_total = len(profiles)
    mission.pilots_total = len(players_pilots)
    mission.gunners_total = len(players_gunners)
    mission.save()

    for p in profiles.values():
        p.save()

    for p in players_pilots.values():
        p.save()
        reward_tour(player=p)

    for p in players_gunners.values():
        p.save()

    for p in players_tankmans.values():
        p.save()

    for aircrafts in players_aircraft.values():
        for a in aircrafts.values():
            a.save()

    for p in players_mission.values():
        p.save()
        reward_mission(player_mission=p)

    for s in squads.values():
        s.save()

    tour.save()

    for event in m_report.log_entries:
        params = {
            'mission_id': mission.id,
            'date': real_date + timedelta(seconds=event['tik'] // 50),
            'tik': event['tik'],
            'extra_data': {
                'pos': event.get('pos'),
            },
        }
        if event['type'] == 'respawn':
            params['type'] = 'respawn'
            params['act_object_id'] = event['sortie'].sortie_db.aircraft.id
            params['act_sortie_id'] = event['sortie'].sortie_db.id
        elif event['type'] == 'end':
            params['type'] = 'end'
            params['act_object_id'] = event['sortie'].sortie_db.aircraft.id
            params['act_sortie_id'] = event['sortie'].sortie_db.id
        elif event['type'] == 'takeoff':
            params['type'] = 'takeoff'
            params['act_object_id'] = event['aircraft'].sortie.sortie_db.aircraft.id
            params['act_sortie_id'] = event['aircraft'].sortie.sortie_db.id
        elif event['type'] == 'landed':
            params['act_object_id'] = event['aircraft'].sortie.sortie_db.aircraft.id
            params['act_sortie_id'] = event['aircraft'].sortie.sortie_db.id
            if event['is_rtb'] and not event['is_killed']:
                params['type'] = 'landed'
            else:
                if event['status'] == LifeStatus.destroyed:
                    params['type'] = 'crashed'
                else:
                    params['type'] = 'ditched'
        elif event['type'] == 'bailout':
            params['type'] = 'bailout'
            params['act_object_id'] = event['bot'].sortie.sortie_db.aircraft.id
            params['act_sortie_id'] = event['bot'].sortie.sortie_db.id
        elif event['type'] == 'damage':
            params['extra_data']['damage'] = event['damage']
            params['extra_data']['is_friendly_fire'] = event['is_friendly_fire']
            if event['target'].cls_base == 'crew':
                params['type'] = 'wounded'
            else:
                params['type'] = 'damaged'
            if event['attacker']:
                if event['attacker'].sortie:
                    params['act_object_id'] = event['attacker'].sortie.sortie_db.aircraft.id
                    params['act_sortie_id'] = event['attacker'].sortie.sortie_db.id
                else:
                    params['act_object_id'] = objects[event['attacker'].log_name]['id']
            if event['target'].sortie:
                params['cact_object_id'] = event['target'].sortie.sortie_db.aircraft.id
                params['cact_sortie_id'] = event['target'].sortie.sortie_db.id
            else:
                params['cact_object_id'] = objects[event['target'].log_name]['id']
        elif event['type'] == 'kill':
            params['extra_data']['is_friendly_fire'] = event['is_friendly_fire']
            if event['target'].cls_base == 'crew':
                params['type'] = 'killed'
            elif event['target'].cls_base == 'aircraft':
                params['type'] = 'shotdown'
            else:
                params['type'] = 'destroyed'
            if event['attacker']:
                if event['attacker'].sortie:
                    params['act_object_id'] = event['attacker'].sortie.sortie_db.aircraft.id
                    params['act_sortie_id'] = event['attacker'].sortie.sortie_db.id
                else:
                    params['act_object_id'] = objects[event['attacker'].log_name]['id']
            if event['target'].sortie:
                params['cact_object_id'] = event['target'].sortie.sortie_db.aircraft.id
                params['cact_sortie_id'] = event['target'].sortie.sortie_db.id
            else:
                params['cact_object_id'] = objects[event['target'].log_name]['id']

        l = LogEntry.objects.create(**params)
        if l.type == 'shotdown' and l.act_sortie and l.cact_sortie and not l.act_sortie.is_disco and not l.extra_data.get(
                'is_friendly_fire'):
            update_killboard_pvp(player=l.act_sortie.player, opponent=l.cact_sortie.player,
                                 players_killboard=players_killboard)

    for p in players_killboard.values():
        p.save()

    # ======================== MODDED PART BEGIN
    for sortie in new_sorties:
        process_aircraft_stats(sortie)
    # ======================== MODDED PART END
    logger.info('{mission} - processing finished'.format(mission=m_report_file.stem))


# ======================== MODDED PART BEGIN
# TODO: Make stats_reset also work with new tables.
def process_old_sorties_batch_aircraft_stats(backfill_log):
    if backfill_log:
        print("Placeholder, processing batch!")
        print(AircraftBucket.objects.count())

    return True


# This should be run after the other objects have been saved, otherwise it will not work.
def process_aircraft_stats(sortie):
    if not sortie.aircraft.cls_base == "aircraft":
        return

    bucket = (AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft))[0]
    if not sortie.is_not_takeoff:
        bucket.total_sorties += 1
        bucket.total_flight_time += 1

    bucket.kills += sortie.ak_total
    bucket.ground_kills += sortie.gk_total
    bucket.assists += sortie.ak_assist
    bucket.aircraft_lost += 1 if sortie.is_lost_aircraft else 0
    bucket.score += sortie.score
    bucket.deaths += 1 if sortie.is_dead else 0
    bucket.captures += 1 if sortie.is_captured else 0
    bucket.bailouts += 1 if sortie.is_bailout else 0
    bucket.ditches += 1 if sortie.is_ditched else 0
    bucket.landings += 1 if sortie.is_landed else 0
    bucket.in_flight += 1 if sortie.is_in_flight else 0
    bucket.crashes += 1 if sortie.is_crashed else 0
    bucket.shotdown += 1 if sortie.is_shotdown else 0

    if sortie.ammo['used_cartridges']:
        bucket.ammo_shot += sortie.ammo['used_cartridges']
    if sortie.ammo['hit_bullets']:
        bucket.ammo_hit += sortie.ammo['hit_bullets']
    if sortie.ammo['used_bombs']:
        bucket.bomb_rocket_shot += sortie.ammo['used_bombs']
    if sortie.ammo['hit_bombs']:
        bucket.bomb_rocket_shot += sortie.ammo['hit_bombs']
    if sortie.ammo['used_rockets']:
        bucket.bomb_rocket_shot += sortie.ammo['used_rockets']
    if sortie.ammo['hit_rockets']:
        bucket.bomb_rocket_shot += sortie.ammo['hit_rockets']

    if sortie.damage:
        bucket.sorties_plane_was_hit += 1
        bucket.plane_survivability_counter += 1 if not sortie.is_lost_aircraft else 0
        bucket.pilot_survivability_counter += 1 if not sortie.is_relive else 0

    for key in sortie.killboard_pvp:
        value = sortie.killboard_pvp[key]
        if key in bucket.killboard_planes:
            bucket.killboard_planes[key] += value
        else:
            bucket.killboard_planes[key] = value

    for key in sortie.killboard_pve:
        value = sortie.killboard_pve[key]
        if key in bucket.killboard_ground:
            bucket.killboard_ground[key] += value
        else:
            bucket.killboard_ground[key] = value

    events = (LogEntry.objects
              .select_related('act_object', 'act_sortie', 'cact_object', 'cact_sortie')
              .filter(Q(act_sortie_id=sortie.id) | Q(cact_sortie_id=sortie.id),
                      Q(type='shotdown') | Q(type='killed') | Q(type='damaged'),
                      act_object__cls_base='aircraft', cact_object__cls_base='aircraft',
                      act_sortie_id__isnull=False, cact_sortie_id__isnull=False))

    enemies_damaged = set()
    enemies_shotdown = set()
    enemies_killed = set()

    damaged_by = set()
    # Technically these following two need not be sets, but for code consistency we keep them like this.
    # (Can only be shotdown/killed by one enemy per sortie)
    shotdown_by = set()
    killed_by = set()

    for event in events:
        if event.act_sortie_id == sortie.id:  # We did the damaging/shooting down/killing
            enemy_plane_sortie_pair = (event.cact_object, event.cact_sortie_id)
            if event.type == 'damaged':
                enemies_damaged.add(enemy_plane_sortie_pair)
            elif event.type == 'shotdown':
                enemies_shotdown.add(enemy_plane_sortie_pair)
            elif event.type == 'killed':
                enemies_killed.add(enemy_plane_sortie_pair)
        else:  # The enemy plane damaged us/shot us down/killed us
            enemy_plane_sortie_pair = (event.act_object, event.act_sortie_id)
            if event.type == 'damaged':
                damaged_by.add(enemy_plane_sortie_pair)
            elif event.type == 'shotdown':
                shotdown_by.add(enemy_plane_sortie_pair)
            elif event.type == 'killed':
                killed_by.add(enemy_plane_sortie_pair)

    updated_killboards = set()
    for damaged_enemy in enemies_damaged:
        enemy_sortie = damaged_enemy[1]
        kb = get_killboard(damaged_enemy, sortie)
        updated_killboards.add(kb)

        if kb.aircraft_1 == sortie.aircraft:
            kb.aircraft_1_distinct_hits += 1
            bucket.distinct_enemies_hit += 1
            enemy_sortie_db = Sortie.objects.filter(id=enemy_sortie).get()
            if enemy_sortie_db.is_shotdown:
                bucket.plane_lethality_counter += 1
                if damaged_enemy not in shotdown_by:
                    kb.aircraft_1_assists += 1
            if enemy_sortie_db.is_dead:
                bucket.pilot_lethality_counter += 1
        else:
            kb.aircraft_2_distinct_hits += 1
            enemy_sortie_db = Sortie.objects.filter(id=enemy_sortie).get()
            if enemy_sortie_db.is_shotdown and damaged_enemy not in shotdown_by:
                kb.aircraft_2_assists += 1

    enemy_buckets_updated = set()
    for shotdown_enemy in enemies_shotdown:
        enemy_bucket = (AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=shotdown_enemy[0]))[0]
        bucket.elo, enemy_bucket.elo = calc_elo(bucket.elo, enemy_bucket.elo)
        enemy_buckets_updated.add(enemy_bucket)

        kb = get_killboard(shotdown_enemy, sortie)
        updated_killboards.add(kb)
        if kb.aircraft_1 == sortie.aircraft:
            kb.aircraft_1_shotdown += 1
        else:
            kb.aircraft_2_shotdown += 1

    for killed_enemy in enemies_killed:
        bucket.pilot_kills += 1
        kb = get_killboard(killed_enemy, sortie)
        updated_killboards.add(kb)
        if kb.aircraft_1 == sortie.aircraft:
            kb.aircraft_1_kills += 1
        else:
            kb.aircraft_2_kills += 1

    sortie_augmentation = (SortieAugmentation.objects.get_or_create(sortie=sortie))[0]
    sortie_augmentation.sortie_stats_processed = True

    for updated_killboard in updated_killboards:
        updated_killboard.save()

    for updated_enemy_bucket in enemy_buckets_updated:
        updated_enemy_bucket.save()

    bucket.update_derived_fields()
    bucket.save()

    sortie_augmentation.save()


def get_killboard(enemy, sortie):
    (enemy_aircraft, _) = enemy
    if sortie.aircraft.id < enemy_aircraft.id:
        kb_key = (sortie.aircraft, enemy_aircraft)
    else:
        kb_key = (enemy_aircraft, sortie.aircraft)

    return (AircraftKillboard.objects.get_or_create(aircraft_1=kb_key[0], aircraft_2=kb_key[1],
                                                                        tour=sortie.tour))[0]


def calc_elo(winner_rating, loser_rating):
    k = 15 # Low k factor (in chess ~30 is common), because there will be a lot of engagements.
    result = expected_result(winner_rating, loser_rating)
    new_winner_rating = winner_rating + k * (1 - result)
    new_loser_rating = loser_rating + k * (0 - (1 - result))
    return new_winner_rating, new_loser_rating


def expected_result(p1, p2):
    exp = (p2 - p1) / 400.0
    return 1 / ((10.0 ** (exp)) + 1)
# ======================== MODDED PART END
