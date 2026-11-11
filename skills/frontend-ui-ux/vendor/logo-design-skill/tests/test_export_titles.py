"""SVG title regression tests; no renderer or assets required."""
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/logo-design/scripts'))
import export_variants as ev

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><rect x="32" y="32" width="192" height="192"/></svg>'
NS = '{http://www.w3.org/2000/svg}'


class ExportTitles(unittest.TestCase):
    def test_titles_round_trip_as_text_in_each_writer(self):
        for title in ('Harbor', 'A & B', '<Studio> "Brand"', '東京 café', '</title><path/>'):
            for writer in (lambda t: ev.set_title(SVG, t),
                           lambda t: ev.square_wrap(SVG, ET.fromstring(SVG), title=t)):
                with self.subTest(title=title, writer=writer):
                    root = ET.fromstring(writer(title))
                    self.assertEqual(root.find(NS + 'title').text, title)
                    self.assertEqual(len(root.findall('.//' + NS + 'path')), 0)

    def test_no_title_preserves_existing_behavior(self):
        self.assertEqual(ev.set_title(SVG, None), SVG)
        self.assertIsNone(ET.fromstring(ev.square_wrap(SVG, ET.fromstring(SVG))).find(NS + 'title'))


if __name__ == '__main__':
    unittest.main()
