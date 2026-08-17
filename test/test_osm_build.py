'''
@Author: WANG Maonan
@Date: 2026-08-17
@Description: Tests for SUMO OSM build helpers.
'''
import tempfile
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


class TestOsmBuild(unittest.TestCase):
    def test_prepare_osm_for_polyconvert_patches_closed_building_parts(self):
        from tshub.sumo_tools.osm_build import prepare_osm_for_polyconvert

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            osm = tmp / "map.osm"
            out = tmp / "map.polyconvert.osm"
            osm.write_text(
                '<osm>'
                '<way id="closed"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="1"/>'
                '<tag k="building:part" v="yes"/></way>'
                '<way id="open"><nd ref="1"/><nd ref="2"/><nd ref="3"/>'
                '<tag k="building:part" v="yes"/></way>'
                '</osm>'
            )

            changed = prepare_osm_for_polyconvert(osm, out)
            root = ET.parse(out).getroot()

        self.assertEqual(changed, 1)
        tags_by_id = {
            way.get("id"): {tag.get("k"): tag.get("v") for tag in way.findall("tag")}
            for way in root.iter("way")
        }
        self.assertEqual(tags_by_id["closed"]["building"], "yes")
        self.assertNotIn("building", tags_by_id["open"])

    def test_enrich_poly_with_osm_building_tags(self):
        from tshub.sumo_tools.osm_build import enrich_poly_with_osm_tags

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            osm = tmp / "map.osm"
            poly = tmp / "map.poly.xml"
            osm.write_text(
                '<osm>'
                '<way id="100"><tag k="building" v="yes"/>'
                '<tag k="building:levels" v="12"/>'
                '<tag k="name" v="Tower A"/></way>'
                '<way id="200"><tag k="building:part" v="roof"/>'
                '<tag k="height" v="8"/></way>'
                '</osm>'
            )
            poly.write_text(
                '<additional>'
                '<poly id="100#1" type="building" shape="0,0 1,0 1,1"/>'
                '<poly id="way_200" type="building" shape="2,0 3,0 3,1"/>'
                '</additional>'
            )

            changed = enrich_poly_with_osm_tags(poly, osm)
            root = ET.parse(poly).getroot()

        self.assertEqual(changed, 5)
        params = {
            p.get("id"): {param.get("key"): param.get("value") for param in p.findall("param")}
            for p in root.iter("poly")
        }
        self.assertEqual(params["100#1"]["building:levels"], "12")
        self.assertEqual(params["100#1"]["name"], "Tower A")
        self.assertEqual(params["way_200"]["building:part"], "roof")
        self.assertEqual(params["way_200"]["height"], "8")

if __name__ == '__main__':
    unittest.main()
