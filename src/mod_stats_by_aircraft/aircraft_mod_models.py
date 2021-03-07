from django.db import models
from stats.models import Tour, Object, Sortie
from django.contrib.postgres.fields import JSONField


class AircraftBucket(models.Model):
    # ========================= NATURAL KEY
    tour = models.ForeignKey(Tour, related_name='+', on_delete=models.PROTECT)
    aircraft = models.ForeignKey(Object, related_name='+', on_delete=models.PROTECT)
    # ========================= NATURAL KEY END

    # ========================= SORTABLE FIELDS
    total_sorties = models.BigIntegerField(default=0, db_index=True)
    total_flight_time = models.BigIntegerField(default=0, db_index=True)
    khr = models.FloatField(default=0, db_index=True)
    gkhr = models.FloatField(default=0, db_index=True)
    kd = models.FloatField(default=0, db_index=True)
    gkd = models.FloatField(default=0, db_index=True)
    accuracy = models.FloatField(default=0, db_index=True)
    bomb_rocket_accuracy = models.FloatField(default=0, db_index=True)
    plane_survivability = models.FloatField(default=0, db_index=True)
    pilot_survivability = models.FloatField(default=0, db_index=True)
    plane_lethality = models.FloatField(default=0, db_index=True)
    pilot_lethality = models.FloatField(default=0, db_index=True)
    elo = models.IntegerField(default=0, db_index=True)
    rating = models.IntegerField(default=0, db_index=True)
    # ========================= SORTABLE FIELDS END

    # ========================= NON-SORTABLE VISIBLE FIELDS
    # Assists per hour
    ahr = models.FloatField(default=0)
    # Assists per death
    ahd = models.FloatField(default=0)
    ammo_to_kill = models.FloatField(default=0)

    kills = models.BigIntegerField(default=0)
    ground_kills = models.BigIntegerField(default=0)
    assists = models.BigIntegerField(default=0)
    aircraft_lost = models.BigIntegerField(default=0)

    killboard_planes = JSONField(default=dict)
    killboard_ground = JSONField(default=dict)
    # ========================== NON-SORTABLE VISIBLE FIELDS END

    # ========================== NON-VISIBLE HELPER FIELDS (used to calculate other visible fields)
    deaths = models.BigIntegerField(default=0)
    captures = models.BigIntegerField(default=0)
    bailouts = models.BigIntegerField(default=0)
    ditches = models.BigIntegerField(default=0)
    landings = models.BigIntegerField(default=0)
    in_flight = models.BigIntegerField(default=0)
    crashes = models.BigIntegerField(default=0)
    shotdown = models.BigIntegerField(default=0)

    ammo_shot = models.BigIntegerField(default=0)
    ammo_hit = models.BigIntegerField(default=0)
    # How much ammo did you shoot when enemy plane was shotdown?
    ammo_shot_kill = models.BigIntegerField(default=0)

    sorties_plane_was_hit = models.BigIntegerField(default=0)
    plane_survivability_counter = models.BigIntegerField(default=0)
    pilot_survivability_counter = models.BigIntegerField(default=0)
    plane_lethality_counter = models.BigIntegerField(default=0)
    pilot_lethality_counter = models.BigIntegerField(default=0)

    distinct_enemies_hit = models.BigIntegerField(default=0)
    pilot_kills = models.BigIntegerField(default=0)  # Assisting in a pilot kill count.

    # ========================== NON-VISIBLE HELPER FIELDS  END
    class Meta:
        # The long table name is to avoid any conflicts with new tables defined in the main branch of IL2 Stats.
        db_table = "AircraftBucket_MOD_STATS_BY_AIRCRAFT"
        ordering = ['-id']

# All pairs of aircraft. Here, aircraft_1.name < aircraft_2.name (Lex order)
class AircraftKillboard(models.Model):
    # ========================= NATURAL KEY
    aircraft_1 = models.ForeignKey(Object, related_name='+', on_delete=models.PROTECT)
    aircraft_2 = models.ForeignKey(Object, related_name='+', on_delete=models.PROTECT)
    tour = models.ForeignKey(Tour, related_name='+', on_delete=models.CASCADE)
    # ========================= NATURAL KEY END

    aircraft_1_kills = models.BigIntegerField(default=0)
    aircraft_1_assists = models.BigIntegerField(default=0)
    aircraft_2_kills = models.BigIntegerField(default=0)
    aircraft_2_assists = models.BigIntegerField(default=0)

    # These two count how many times aircraft_x hit aircraft_y at least once in a sortie.
    # To calculate survivability/lethality.
    aircraft_1_distinct_hits = models.BigIntegerField(default=0)
    aircraft_2_distinct_hits = models.BigIntegerField(default=0)

    class Meta:
        # The long table name is to avoid any conflicts with new tables defined in the main branch of IL2 Stats.
        db_table = "AircraftKillboard_MOD_STATS_BY_AIRCRAFT"
        ordering = ['-id']


# Additional fields to Sortie objects used by this mod.
class SortieAugmentation(models.Model):
    sortie = models.OneToOneField(Sortie, on_delete=models.PROTECT, primary_key=True,
                                  related_name='SortieAugmentation_MOD_STATS_BY_AIRCRAFT')
    sortie_stats_processed = models.BooleanField(default=False, db_index=True)

    class Meta:
        # The long table name is to avoid any conflicts with new tables defined in the main branch of IL2 Stats.
        db_table = "Sortie_MOD_STATS_BY_AIRCRAFT"
