====================================================
IL-2 Stats Mod: Aircraft Stats
====================================================
Authors: =FEW=Revolves and Enigma89

This is a mod which aims to answer questions like "Just how survivable is a P-47 in IL-2" and "What's the best bomber?" by giving you cold, hard stats on these kind of topics. To that aim, this mod is an extension of the IL-2 stats website in use by most major IL-2 servers. It takes the data from the sorties stored on these websites, aggeregates data on a per-plane basis, and provides statistics on planes.

You can view the data collected by this mod in three new pages:
* An overview of all planes. Want to bomb the most targets per hour? Figure out which plane does it!
* A detailed summary of a single plane. If you ever want to know more about how your favorite plane performs.
* A page showing the performance of a single plane against all others. Do you want to know which plane works best again a Spitfire Mk.V?

We wish to thank =FB=Vaal and =FB=Isaay for their work creating the wonderful IL2 Stats system. Additional thanks go out to Vaudoo, PR9INICHEK, and HawkerMkIII who helped us translate this mod into French, Russian, and Spanish, respectively. We also thank RaptorAttacker for creating the new icons used by this mod.

This version is compatible with 1.2.48 of IL2 stats.

This mod does work retroactively. It hijacks the stats process while no new reports are found in order to retroactively aggregate old sorties (while checking for new reports periodically). This process may take a while. On an i7-6700k with an SSD the mod achieved a throughput of roughly 4000 sorties processed per minute. As a rule of thumb, you can expect a single month tour to be processed in about 15 minutes. 

If you want to adjust how many previous tours you wish to retroactively compute, there is a new config paramater under [stats] called "retro_compute_for_last_tours=10" to adjust this. A value of 0 will retroactively compute for only the current tour (for any sorties in the current tour before this mod was installed), a value of -1 will completely disable the retroactive computations. The default value of 10 retroactively aggregates stats for the previous 10 tours and the current one.

Installation
---------------------------------------------

1. You need an installation of il2 stats. The latest version can be found under https://forum.il2sturmovik.com/topic/19083-il2-stats-statistics-system-for-a-dedicated-server-il2-battle-of-stalingrad/

2. Copy the src folder inside this .zip into your il2 stats folder.

3. Inside your src/conf.ini, add the line "mods = mod_stats_by_aircraft" under [stats]. If you already have a mods line, you should change it instead - just be sure to remove any semicolons inside that line if there are any.

4. Configure retro_compute_for_last_tours=10 under [stats] to any value you'd like. See above for an explanation.

5. Run the update script in your /run folder after you're done with the above.

Support
---------------------------------------------
Contact =FEW=Revolves on the IL2 forums.


Compatibility with other mods
---------------------------------------------

This mod is compatible with IL-2 Split Rankings. Make sure mod_stats_by_aircraft comes after mod_rating_by_type in the mods config parameter.
This mod is mildly incompatible with the disconnect mod. Copy the src/ folder in compatibility_patch/disconnect/ inside this zip over into your il-2 stats folder after installing both mods.
This mod is mildly incompatible with the tank mod. Copy the src/folder in compatibility_patch/tank/ over into your il-2 stats folder after installing both mods.

If you want to install all four of these mods, then check out this bundle: https://forum.il2sturmovik.com/topic/70029-il-2-stats-mod-bundle-disco-tanks-splitrankings/

License
---------------------------------------------
This mod is licensed under the MIT License.
