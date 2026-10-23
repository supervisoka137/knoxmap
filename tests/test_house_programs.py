"""Houses laid out to the game's own room programs (layout.HOUSE_PROGRAMS),
their garages and storeys, and what an untagged footprint too long or too big
for a house becomes (build.untagged_kind)."""
import random
import unittest
from collections import Counter
from statistics import mean

import numpy as np

from knoxbuild import layout
from knoxbuild.build import (BIG_BLOCK_M2, ROW_MIN_LENGTH_HOUSE_M, building_levels,
                             classify_building, row_units, untagged_kind)
from knoxbuild.footprint import Footprint
from knoxbuild.regional import area_level_pool
from knoxbuild.settings import Settings


def footprint(w, h):
    return Footprint(0, 0, np.ones((h, w), dtype=bool), 0.0, min(w, h), max(w, h))


def kinds_by_level(building):
    return [Counter(r.kind for r in storey.rooms) for storey in building.storeys]


class HousePrograms(unittest.TestCase):
    def test_draws_follow_the_games_bedrooms_and_bathrooms(self):
        # 180 m2 of one storey: the game's houses of 160-200 m2 have 2.8
        # bedrooms and 2.3 bathrooms on average.
        draws = [layout.house_program(180, 1, 12, 15, random.Random(i), garage=False)
                 for i in range(600)]
        self.assertAlmostEqual(mean(d.bedrooms for d in draws), 2.8, delta=0.15)
        self.assertAlmostEqual(mean(d.bathrooms for d in draws), 2.3, delta=0.15)
        small = [layout.house_program(60, 1, 8, 8, random.Random(i), garage=False)
                 for i in range(300)]
        self.assertTrue(all(d.bedrooms <= 2 and d.bathrooms == 1 for d in small))

    def test_no_house_has_more_rooms_than_the_game_gives_one(self):
        for i in range(200):
            d = layout.house_program(random.randint(30, 900), random.randint(1, 3),
                                     12, 12, random.Random(i))
            self.assertLessEqual(d.bedrooms, 5)
            self.assertLessEqual(d.bathrooms, d.bedrooms + 1)

    def test_every_house_has_a_kitchen_a_bathroom_and_a_bed(self):
        rng = random.Random(5)
        for i in range(60):
            w, h = rng.randint(7, 22), rng.randint(7, 18)
            levels = rng.choice((1, 1, 2))
            with self.subTest(w=w, h=h, levels=levels, seed=i):
                b = layout.build_building(w, h, levels=levels, seed=i, kind="house",
                                          street=rng.choice("NSEW"))
                counts = Counter(r.kind for r in b.rooms)
                ground = kinds_by_level(b)[0]
                self.assertTrue(ground["kitchen"] or ground["openplan"], dict(counts))
                self.assertGreaterEqual(ground["bathroom"], 1, dict(counts))
                if w * h >= 60:
                    self.assertGreaterEqual(counts["bedroom"] + counts["kidsbedroom"], 1,
                                            dict(counts))
                # Not a house of storerooms and offices any more.
                self.assertLessEqual(counts["office"], 1)
                self.assertLessEqual(counts["storage"], 1)

    def test_two_storey_house_sleeps_upstairs(self):
        for seed in range(8):
            b = layout.build_building(12, 10, levels=2, seed=seed, kind="house", street="S")
            ground, upper = kinds_by_level(b)
            with self.subTest(seed=seed):
                self.assertTrue(ground["kitchen"] or ground["openplan"])
                self.assertGreaterEqual(ground["bathroom"], 1)
                self.assertEqual(ground["bedroom"] + ground["kidsbedroom"], 0)
                self.assertGreaterEqual(upper["bedroom"] + upper["kidsbedroom"], 1)

    def test_closets_are_the_games_two_tiles(self):
        sizes = []
        for seed in range(30):
            b = layout.build_building(16, 13, seed=seed, kind="house", street="S")
            storey = b.storeys[0]
            for i, r in enumerate(storey.rooms, 1):
                if r.kind == "closet":
                    sizes.append(sum(row.count(i) for row in storey.grid))
        self.assertTrue(sizes)
        self.assertLessEqual(Counter(sizes).most_common(1)[0][0], 3)

    def test_a_big_house_has_a_garage_on_the_street_with_a_vehicle_opening(self):
        found = 0
        for seed in range(40):
            b = layout.build_building(20, 14, seed=seed, kind="house", street="S")
            ground = b.storeys[0]
            garage = [i for i, r in enumerate(ground.rooms, 1) if r.kind == "garage"]
            if not garage:
                continue
            found += 1
            idx = garage[0]
            tiles = [(x, y) for y, row in enumerate(ground.grid) for x, v in enumerate(row)
                     if v == idx]
            self.assertGreaterEqual(len(tiles), 24)
            # Against the street wall (south, y = height), and opening onto it
            # three doors wide.
            self.assertEqual(max(y for _x, y in tiles), 13)
            street_doors = [d for d in ground.doors if d[2] == "N" and d[1] == 14
                            and ground.grid[13][d[0]] == idx]
            self.assertEqual(len(street_doors), 3)
            # Racks and crates, not the house's dressers.
            furniture = {role for role, x, y, _o in ground.furniture
                         if 0 <= y < 14 and 0 <= x < 20 and ground.grid[y][x] == idx}
            self.assertFalse(any(role.startswith("dresser") for role in furniture))
        # 280 m2: the game has a garage on 38-57% of houses that size.
        self.assertGreater(found, 8)

    def test_no_door_is_hung_twice(self):
        for seed in range(40):
            b = layout.build_building(11, 9, seed=seed, kind="house",
                                      street=random.Random(seed).choice("NSEW"))
            for storey in b.storeys:
                self.assertEqual(len(storey.doors), len(set(storey.doors)), seed)


class Stoves(unittest.TestCase):
    """Something to cook on in every house's kitchen. A door slid off a corner
    after the rooms were furnished landed on the stove, and the way through it
    was cleared by taking the stove out; in a narrow kitchen the table took
    every spot it could stand. 2.6% of Howell and Brighton's houses had none,
    and Knox County 0.4%."""

    def test_a_door_moved_off_a_corner_does_not_cost_the_stove(self):
        # A 4x4 kitchen whose door into the bedroom was slid onto the stove.
        rng = random.Random(1)
        for i in range(284):
            w, h = rng.randint(7, 24), rng.randint(7, 20)
            levels, street = rng.choice((1, 1, 2)), rng.choice("NSEW")
        b = layout.build_building(w, h, levels=levels, seed=283, kind="house", street=street)
        self.assertTrue(any(f[0].startswith("stove") for f in b.storeys[0].furniture))

    def test_nearly_every_kitchen_has_a_stove(self):
        rng = random.Random(2)
        kitchens = without = 0
        for i in range(300):
            w, h = rng.randint(7, 24), rng.randint(7, 20)
            b = layout.build_building(w, h, levels=rng.choice((1, 1, 2)), seed=i,
                                      kind="house", street=rng.choice("NSEW"))
            for plan in b.storeys:
                for idx, room in enumerate(plan.rooms, 1):
                    if room.kind not in ("kitchen", "openplan"):
                        continue
                    kitchens += 1
                    without += not any(f[0].startswith("stove")
                                       and layout._room_at(plan, f[1], f[2]) == idx
                                       for f in plan.furniture)
        self.assertLessEqual(without, kitchens // 100, f"{without} of {kitchens}")


class HouseStoreys(unittest.TestCase):
    def test_house_storeys_are_the_games(self):
        self.assertEqual(set(area_level_pool(None, 60.0)), {1})
        pool = area_level_pool(None, 110.0)
        self.assertAlmostEqual(pool.count(2) / len(pool), 0.35, delta=0.01)
        pool = area_level_pool(None, 180.0)
        self.assertAlmostEqual(pool.count(2) / len(pool), 0.6, delta=0.01)
        for m2 in (50, 120, 180, 250, 500, 1000):
            self.assertLessEqual(max(area_level_pool(None, m2)), 3)

    def test_a_big_ranch_house_keeps_to_one_storey(self):
        # 250 m2: past 200 the game builds most houses on one floor.
        settings = Settings(max_levels=4)
        levels = Counter(building_levels({}, None, 250, random.Random(i), settings)[0]
                         for i in range(400))
        self.assertGreater(levels[1], levels[2])
        self.assertEqual(levels[4], 0)


class UntaggedFootprints(unittest.TestCase):
    TOWN, COUNTRY = 0.15, 0.02

    def test_long_rows(self):
        # The county airport's T-hangars and a self-storage block.
        self.assertEqual(untagged_kind(footprint(135, 16), self.TOWN), "industrial")
        self.assertEqual(untagged_kind(footprint(76, 10), self.TOWN), "industrial")
        self.assertEqual(untagged_kind(footprint(94, 20), self.COUNTRY), "barn")
        # A condo row: homes, cut up by row_units.
        self.assertIsNone(untagged_kind(footprint(46, 13), self.TOWN))
        # A row of garages behind the flats.
        self.assertEqual(untagged_kind(footprint(41, 7), self.TOWN), "shed")
        # A ranch house with its garage stays a house.
        self.assertIsNone(untagged_kind(footprint(30, 10), self.TOWN))
        self.assertEqual(untagged_kind(footprint(17, 2), self.TOWN), "shed")

    def test_big_footprints(self):
        self.assertEqual(untagged_kind(footprint(40, 30), self.TOWN), "apartment")
        side = int(BIG_BLOCK_M2 ** 0.5) + 5
        self.assertEqual(untagged_kind(footprint(side, side), self.TOWN), "industrial")
        self.assertEqual(untagged_kind(footprint(40, 30), self.COUNTRY), "barn")
        self.assertIsNone(untagged_kind(footprint(20, 14), self.TOWN))

    def test_a_house_is_not_cut_into_terraced_houses(self):
        self.assertEqual(len(row_units(footprint(28, 10), None, "yes", 0, 1.0)), 1)
        units = row_units(footprint(int(ROW_MIN_LENGTH_HOUSE_M) + 10, 12), None, "yes", 0, 1.0)
        self.assertGreater(len(units), 3)
        # A mapped terrace is still a terrace at any length past a shop's.
        self.assertGreater(len(row_units(footprint(28, 10), None, "terrace", 0, 1.0)), 1)

    def test_a_hangar_is_a_works_but_a_bases_hangar_is_the_bases(self):
        self.assertEqual(classify_building({"building": "hangar"}), "industrial")
        self.assertEqual(classify_building({"military": "hangar",
                                            "building": "hangar"}), "military")


if __name__ == "__main__":
    unittest.main()
