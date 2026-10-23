import unittest
from collections import Counter

from knoxbuild.layout import build_building


class HouseRoomQuotas(unittest.TestCase):
    # The bounds are the game's own: vanilla's 3,571 houses never have more
    # than five bedrooms, and never more bathrooms than bedrooms plus one
    # (layout.HOUSE_PROGRAMS).
    def test_large_house_has_a_bounded_whole_building_room_count(self):
        for seed in range(3):
            with self.subTest(seed=seed):
                building = build_building(28, 24, levels=3, seed=seed, kind="house")
                counts = Counter(room.kind for room in building.rooms)
                bedrooms = counts["bedroom"] + counts["kidsbedroom"]
                self.assertLessEqual(bedrooms, 5)
                self.assertLessEqual(counts["bathroom"], bedrooms + 1)
                self.assertLessEqual(counts["bathroom"], 4)
                self.assertGreater(bedrooms, 0)

    def test_single_storey_house_has_the_games_bedrooms_and_a_bath(self):
        # 168 m2 of one storey: vanilla's houses of 120-200 m2 have two or
        # three bedrooms (two in 91% under 160, three in 78% over) and one
        # to three bathrooms.
        building = build_building(14, 12, seed=19, kind="house")
        counts = Counter(room.kind for room in building.rooms)

        self.assertIn(counts["bedroom"] + counts["kidsbedroom"], (2, 3))
        self.assertGreaterEqual(counts["bathroom"], 1)
        self.assertLessEqual(counts["bathroom"], 3)


if __name__ == "__main__":
    unittest.main()
