from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ModConfig(AppConfig):
    name = 'mod_stats_by_aircraft'

    def ready(self):
        # frontend monkey patch
        # TODO: Start working on the frontend
        # from stats import urls as original_urls
        # from . import urls as new_urls
        # original_urls.urlpatterns = new_urls.urlpatterns

        # backend monkey patch
        from . import stats_whore
        from stats import stats_whore as old_stats_whore

        old_stats_whore.main = stats_whore.main
        old_stats_whore.update_sortie = stats_whore.update_sortie
