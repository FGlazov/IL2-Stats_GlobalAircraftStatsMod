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

===============================================================================
How Our Elo system works (Elo gained/lost may vary slightly):

All Aircraft start with 1500 Elo. Some aircraft have subtypes.
For example, the BF 109 K-4 has 4 subtypes (no bombs, bombs, upgraded engine, upgraded engine with bombs)

Most fighters have jabo/pure fighter subtypes (bombs, no bombs). Some have upgraded engine subtypes (if you have 150 octane or better engines).
Attackers and Bombers other than the P-38 do not have subtypes. They're all pretty much purely ground attackers, so bombs/no bombs would not make much sense.

===============================================================================
Case 1: Aircraft 1 and 2 both have no subtypes.
===============================================================================

There is an engangement, so both Aircraft 1 and 2 aircraft 2's Elos get updated.

For example:

Aircraft 1 (1500 Elo) wins vs Aircraft 2 (1500 Elo), new Elos are 1504 and 1496, respectively.
Aircraft 1 (1500 Elo) wins vs Aircraft 2 (3000 Elo), new elos are 1508 and 2992, respectively.
Aircraft 1 (3000 Elo) wins vs Aircraft 2 (1500 Elo), new elos are 1501 and 2999, respectively.

This is done in such a way so that elo changes the most when there is a suprising event. (3000 should almost always win vs 1500!)
===============================================================================
Case 2: Aircraft 1 and 2 both have subtypes.
===============================================================================

There is an engangement. Noticer in this case Aircraft 1 and 2 both have exactly one subtype in this engagement.

Aircraft 1 (Main Elo 1500, Subtype Elo 1500) wins vs Aircraft 2 (Main Elo 1500, Subtype Elo 3000)

The Updated elos are:

Aircraft 1 (Main Elo 1504, 1508)
Aircraft 2 (Main Elo 1496, 2992)

Main elos update each other, subtype elos update each other.
===============================================================================
Case 3: Aircraft 1 has a subtype, but aircraft 2 does not.
===============================================================================

Aircraft 1 (Main Elo 1500, subtype elo 500) wins vs Aircraft 2 (1000 Elo)

Updated Elos are:

Aircraft 1 (Main Elo 1502, subtype Elo 506)

Here 1502 is the Elo you get from 1500 winning vs 1000
Here 506 is the elo you get from 500 winning vs 1000

Aircraft 2: 996 Elo

You lose 2 elo if you have 1000 Elo and lose against 1500
You lose 6 elo if you have 1000 Elo and lose against 500

So the total loss is (2 + 6)/2 = 4
====================================================================================

So generally speaking the Elos of subtypes should be compared to Elos of subtypes,
and the elos of the main type should be compared to elos of the main types. Subtype
Elo and main type elo is likely to be different, since these don't play in the same
arena.