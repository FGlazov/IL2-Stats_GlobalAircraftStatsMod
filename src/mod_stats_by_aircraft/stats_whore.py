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
def process_old_sorties_batch_aircraft_stats(backfill_log):
    if backfill_log:
        print("Placeholder, processing batch!")
        print(aircraft_mod_models.AircraftBucket.objects.count())

    return True

def process_aircraft_stats(sortie):
    # TODO: Implement this, it will fill in aircraft stats.
    print("Placeholder, processing!")
# ======================== MODDED PART END
