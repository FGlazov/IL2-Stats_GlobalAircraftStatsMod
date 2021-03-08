from django.db import models
from stats.models import Tour, Object, Sortie, rating_format_helper
from mission_report.constants import Coalition
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.conf import settings
from django.urls import reverse




def compute_float(numerator, denominator, round_to=2):
    return round(numerator / max(denominator, 1), round_to)


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
    elo = models.IntegerField(default=1500, db_index=True)
    rating = models.IntegerField(default=0, db_index=True)
    # ========================= SORTABLE FIELDS END

    # ========================= NON-SORTABLE VISIBLE FIELDS
    # Assists per hour
    ahr = models.FloatField(default=0)
    # Assists per death
    ahd = models.FloatField(default=0)
    hits_to_death = models.FloatField(default=0)

    kills = models.BigIntegerField(default=0)
    ground_kills = models.BigIntegerField(default=0)
    assists = models.BigIntegerField(default=0)
    aircraft_lost = models.BigIntegerField(default=0)

    killboard_planes = JSONField(default=dict)
    killboard_ground = JSONField(default=dict)
    COALITIONS = (
        (Coalition.neutral, pgettext_lazy('coalition', _('neutral'))),
        (Coalition.coal_1, settings.COAL_1_NAME),
        (Coalition.coal_2, settings.COAL_2_NAME),
    )

    coalition = models.IntegerField(default=Coalition.neutral, choices=COALITIONS)
    # ========================== NON-SORTABLE VISIBLE FIELDS END

    # ========================== NON-VISIBLE HELPER FIELDS (used to calculate other visible fields)
    score = models.BigIntegerField(default=0)
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

    bomb_rocket_shot = models.BigIntegerField(default=0)
    bomb_rocket_hit = models.BigIntegerField(default=0)

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

    def update_derived_fields(self):
        self.khr = compute_float(self.kills, self.flight_time_hours)
        self.gkhr = compute_float(self.ground_kills, self.flight_time_hours)
        self.kd = compute_float(self.kills, self.relive)
        self.gkd = compute_float(self.ground_kills, self.relive)
        self.accuracy = compute_float(self.ammo_hit * 100, self.ammo_shot, 1)
        self.bomb_rocket_accuracy = compute_float(self.bomb_rocket_hit * 100, self.bomb_rocket_shot, 1)
        self.plane_survivability = compute_float(self.plane_survivability_counter, self.sorties_plane_was_hit)
        self.pilot_survivability = compute_float(self.pilot_survivability_counter, self.sorties_plane_was_hit)
        self.plane_lethality = compute_float(self.plane_lethality_counter, self.distinct_enemies_hit)
        self.pilot_lethality = compute_float(self.pilot_lethality_counter, self.distinct_enemies_hit)
        self.update_rating()
        self.ahr = compute_float(self.assists, self.flight_time_hours)
        self.ahd = compute_float(self.assists, self.relive)

    def update_rating(self):
        # score per death
        sd = self.score / max(self.relive, 1)
        # score per hour
        shr = self.score / max(self.flight_time_hours, 1)
        self.rating = int(sd * shr / 1000)
        # Note this rating is NOT multiplied by score
        # In the original formula, you got higher rating the longer you played with the same performance.
        # This was due to the multiplication by score. This is not wanted for aircraft stats.

    @property
    def flight_time_hours(self):
        return self.total_flight_time / 3600

    @property
    def relive(self):
        return self.deaths + self.captures

    @property
    def rating_format(self):
        return rating_format_helper(self.rating)

    def get_aircraft_url(self):
        url = '{url}?tour={tour_id}'.format(url=reverse('stats:aircraft', args=[self.aircraft.id]), tour_id=self.tour.id)
        return url


# All pairs of aircraft. Here, aircraft_1.name < aircraft_2.name (Lex order)
class AircraftKillboard(models.Model):
    # ========================= NATURAL KEY
    aircraft_1 = models.ForeignKey(Object, related_name='+', on_delete=models.PROTECT)
    aircraft_2 = models.ForeignKey(Object, related_name='+', on_delete=models.PROTECT)
    tour = models.ForeignKey(Tour, related_name='+', on_delete=models.PROTECT)
    # ========================= NATURAL KEY END

    # TODO: Make DB indices
    aircraft_1_kills = models.BigIntegerField(default=0)
    aircraft_1_shotdown = models.BigIntegerField(default=0) # Nr times aircraft 1 shot down aircraft 2
    aircraft_1_assists = models.BigIntegerField(default=0)
    aircraft_2_kills = models.BigIntegerField(default=0)
    aircraft_2_shotdown = models.BigIntegerField(default=0) # Nr times aircraft 2 shot down aircraft 1
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


