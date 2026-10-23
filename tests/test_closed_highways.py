"""A closed highway way is a loop, not an area, unless it says area=yes."""
import unittest

from generator.osm import OSMFeature
from generator.rendering.geometry import _is_polygon
from generator.rendering.landcover import GREEN_CATEGORIES

RING = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (0.0, 0.0)]
LINE = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0)]


def way(tags, geometry=RING):
    return OSMFeature(1, "way", tags, geometry)


class ClosedHighways(unittest.TestCase):
    def test_loops_are_lines(self):
        for highway in ("footway", "residential", "service", "path", "pedestrian"):
            self.assertFalse(_is_polygon(way({"highway": highway})), highway)

    def test_marked_areas_stay_areas(self):
        self.assertTrue(_is_polygon(way({"highway": "footway", "area": "yes"})))
        self.assertTrue(_is_polygon(way({"highway": "pedestrian", "area": "yes"})))
        for highway in ("rest_area", "services", "platform"):
            self.assertTrue(_is_polygon(way({"highway": highway})), highway)

    def test_everything_else_unchanged(self):
        self.assertTrue(_is_polygon(way({"landuse": "residential"})))
        self.assertTrue(_is_polygon(way({"building": "yes"})))
        self.assertFalse(_is_polygon(way({"landuse": "grass"}, LINE)))
        self.assertTrue(_is_polygon(OSMFeature(1, "relation", {"highway": "pedestrian"}, [])))

    def test_residential_keeps_its_lawns(self):
        self.assertIn("residential", GREEN_CATEGORIES)


if __name__ == "__main__":
    unittest.main()
