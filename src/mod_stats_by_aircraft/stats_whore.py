import time
from stats.stats_whore import (stats_whore, cleanup, collect_mission_reports, update_status, update_general,
                               update_ammo, update_killboard)
from stats.logger import logger
from stats.online import update_online
from users.utils import cleanup_registration
from django.conf import settings
from core import __version__
from . import aircraft_mod_models
import sys
import django


MISSION_REPORT_PATH = settings.MISSION_REPORT_PATH


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


def update_sortie(new_sortie, player_mission, player_aircraft, vlife):
    player = new_sortie.player

    if not player.date_first_sortie:
        player.date_first_sortie = new_sortie.date_start
        player.date_last_combat = new_sortie.date_start
    player.date_last_sortie = new_sortie.date_start

    if not vlife.date_first_sortie:
        vlife.date_first_sortie = new_sortie.date_start
        vlife.date_last_combat = new_sortie.date_start
    vlife.date_last_sortie = new_sortie.date_start

    # если вылет был окончен диско - результаты вылета не добавляться к общему профилю
    if new_sortie.is_disco:
        player.disco += 1
        player_mission.disco += 1
        player_aircraft.disco += 1
        vlife.disco += 1
        return
    # если вылет игнорируется по каким либо причинам
    elif new_sortie.is_ignored:
        return

    # если в вылете было что-то уничтожено - считаем его боевым
    if new_sortie.score:
        player.date_last_combat = new_sortie.date_start
        vlife.date_last_combat = new_sortie.date_start

    vlife.status = new_sortie.status
    vlife.aircraft_status = new_sortie.aircraft_status
    vlife.bot_status = new_sortie.bot_status

    # TODO проверить как это отработает для вылетов стрелков
    if not new_sortie.is_not_takeoff:
        player.sorties_coal[new_sortie.coalition] += 1
        player_mission.sorties_coal[new_sortie.coalition] += 1
        vlife.sorties_coal[new_sortie.coalition] += 1

        if player.squad:
            player.squad.sorties_coal[new_sortie.coalition] += 1

        if new_sortie.aircraft.cls_base == 'aircraft':
            if new_sortie.aircraft.cls in player.sorties_cls:
                player.sorties_cls[new_sortie.aircraft.cls] += 1
            else:
                player.sorties_cls[new_sortie.aircraft.cls] = 1

            if new_sortie.aircraft.cls in vlife.sorties_cls:
                vlife.sorties_cls[new_sortie.aircraft.cls] += 1
            else:
                vlife.sorties_cls[new_sortie.aircraft.cls] = 1

            if player.squad:
                if new_sortie.aircraft.cls in player.squad.sorties_cls:
                    player.squad.sorties_cls[new_sortie.aircraft.cls] += 1
                else:
                    player.squad.sorties_cls[new_sortie.aircraft.cls] = 1

    update_general(player=player, new_sortie=new_sortie)
    update_general(player=player_mission, new_sortie=new_sortie)
    update_general(player=player_aircraft, new_sortie=new_sortie)
    update_general(player=vlife, new_sortie=new_sortie)
    if player.squad:
        update_general(player=player.squad, new_sortie=new_sortie)

    update_ammo(sortie=new_sortie, player=player)
    update_ammo(sortie=new_sortie, player=player_mission)
    update_ammo(sortie=new_sortie, player=player_aircraft)
    update_ammo(sortie=new_sortie, player=vlife)

    update_killboard(player=player, killboard_pvp=new_sortie.killboard_pvp,
                     killboard_pve=new_sortie.killboard_pve)
    update_killboard(player=player_mission, killboard_pvp=new_sortie.killboard_pvp,
                     killboard_pve=new_sortie.killboard_pve)
    update_killboard(player=player_aircraft, killboard_pvp=new_sortie.killboard_pvp,
                     killboard_pve=new_sortie.killboard_pve)
    update_killboard(player=vlife, killboard_pvp=new_sortie.killboard_pvp,
                     killboard_pve=new_sortie.killboard_pve)

    player.streak_current = vlife.ak_total
    player.streak_max = max(player.streak_max, player.streak_current)
    player.streak_ground_current = vlife.gk_total
    player.streak_ground_max = max(player.streak_ground_max, player.streak_ground_current)
    player.score_streak_current = vlife.score
    player.score_streak_current_heavy = vlife.score_heavy
    player.score_streak_current_medium = vlife.score_medium
    player.score_streak_current_light = vlife.score_light
    player.score_streak_max = max(player.score_streak_max, player.score_streak_current)
    player.score_streak_max_heavy = max(player.score_streak_max_heavy, player.score_streak_current_heavy)
    player.score_streak_max_medium = max(player.score_streak_max_medium, player.score_streak_current_medium)
    player.score_streak_max_light = max(player.score_streak_max_light, player.score_streak_current_light)

    player.sorties_streak_current = vlife.sorties_total
    player.sorties_streak_max = max(player.sorties_streak_max, player.sorties_streak_current)
    player.ft_streak_current = vlife.flight_time
    player.ft_streak_max = max(player.ft_streak_max, player.ft_streak_current)

    if new_sortie.is_relive:
        player.streak_current = 0
        player.streak_ground_current = 0
        player.score_streak_current = 0
        player.score_streak_current_heavy = 0
        player.score_streak_current_medium = 0
        player.score_streak_current_light = 0
        player.sorties_streak_current = 0
        player.ft_streak_current = 0
        player.lost_aircraft_current = 0
    else:
        if new_sortie.is_lost_aircraft:
            player.lost_aircraft_current += 1

    player.sortie_max_ak = max(player.sortie_max_ak, new_sortie.ak_total)
    player.sortie_max_gk = max(player.sortie_max_gk, new_sortie.gk_total)

    update_status(new_sortie=new_sortie, player=player)
    update_status(new_sortie=new_sortie, player=player_mission)
    update_status(new_sortie=new_sortie, player=player_aircraft)
    update_status(new_sortie=new_sortie, player=vlife)
    if player.squad:
        update_status(new_sortie=new_sortie, player=player.squad)

    # ======================== MODDED PART BEGIN
    process_aircraft_stats(new_sortie)
    # ======================== MODDED PART END


# ======================== MODDED PART BEGIN
# TODO: Make stats_reset also work with new tables.
def process_old_sorties_batch_aircraft_stats(backfill_log):
    if backfill_log:
        print("Placeholder, processing batch!")
        print(aircraft_mod_models.AircraftBucket.objects.count())

    return True


def process_aircraft_stats(sortie):
    if not sortie.aircraft.cls_base == "aircraft":
        return

    bucket = (aircraft_mod_models.AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft))[0]
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

    # TODO: Update bucket.times_hit_shotdown (if possible)
    # TODO: Update bucket.plane_lethality_counter and bucket.pilot_lethality_counter
    # TODO: Update bucket.distinct_enemies hit and bucket.pilot_kills.
    # TODO: Update bucket.elo
    bucket.update_derived_fields()
    bucket.save()

    # TODO: Remove this print (used for debugging)
    print("Bucket saved!")
# ======================== MODDED PART END
