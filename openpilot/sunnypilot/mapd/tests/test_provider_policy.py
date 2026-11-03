"""Provider policy checks; also runnable with stdlib unittest on the comma."""
import tempfile
import ast
import io
import os
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch


class TestProviderPolicy(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    try:
      from openpilot.sunnypilot.mapd.live_map_data import osm_map_data
    except OSError as exc:
      raise unittest.SkipTest(f'native Params library unavailable: {exc}') from exc
    cls.module = osm_map_data

  def setUp(self):
    self.directory = tempfile.TemporaryDirectory()
    self.addCleanup(self.directory.cleanup)
    real_open = open
    patcher = patch.object(self.module, 'open', lambda path, mode='r': real_open(Path(self.directory.name) / Path(path).name, mode), create=True)
    patcher.start()
    self.addCleanup(patcher.stop)
    self.map = self.module.OsmMapData.__new__(self.module.OsmMapData)
    self.map.speed_limit_provider = Mock()
    self.map.osm_fallback_enabled = False
    self.map.provider_limits = None
    self.map.mem_params = Mock()
    self.map.mem_params.get.side_effect = lambda name: {'MapSpeedLimit': 100 / 3.6,
      'NextMapSpeedLimit': {'speedlimit': 30 / 3.6, 'latitude': .003, 'longitude': 0}}.get(name)
    self.map._native_direction_valid = Mock(return_value=True)
    self.map.localizer_valid = True
    self.map.sm = {'liveLocationKalman': NS(gpsOK=True)}

  def test_tomtom_only_ignores_available_osm_current_and_upcoming(self):
    self.assertEqual(self.map.get_current_speed_limit(), 0.)
    self.assertEqual(self.map.get_next_speed_limit_and_distance(), (0., 0.))
    self.assertEqual((Path(self.directory.name) / 'tomtom_active').read_text(), 'TomTom unavailable')
    self.map.mem_params.get.assert_not_called()

  def test_previous_tomtom_is_retained_as_provenance_not_a_fresh_map_limit(self):
    self.map.provider_limits = (50 / 3.6, 30 / 3.6, 200.)
    self.assertAlmostEqual(self.map.get_current_speed_limit(), 50 / 3.6)
    self.assertEqual(self.map.get_next_speed_limit_and_distance(), (30 / 3.6, 200.))
    self.map.provider_limits = None
    self.assertEqual(self.map.get_current_speed_limit(), 0.)
    self.assertEqual(self.map.last_tomtom_kph, 50.)
    self.assertEqual(self.map.get_next_speed_limit_and_distance(), (0., 0.))
    self.assertEqual((Path(self.directory.name) / 'tomtom_active').read_text(), 'TomTom retained')

  def test_osm_mode_without_tomtom_still_works(self):
    self.map.speed_limit_provider = None
    self.assertAlmostEqual(self.map.get_current_speed_limit(), 100 / 3.6)
    self.assertEqual((Path(self.directory.name) / 'tomtom_active').read_text().strip(), 'OSM fallback')

  def test_explicit_opt_in_can_restore_osm_fallback(self):
    self.map.osm_fallback_enabled = True
    self.assertAlmostEqual(self.map.get_current_speed_limit(), 100 / 3.6)


class TestProviderIndicator(unittest.TestCase):
  def draw(self, status):
    configured = os.getenv('UI_CANDIDATE_PATH')
    path = Path(configured) if configured else Path(__file__).parents[3] / 'selfdrive/ui/sunnypilot/onroad/speed_limit.py'
    tree = ast.parse(path.read_text())
    method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == '_draw_source_indicator')
    drawing = Mock()
    namespace = {'rl': NS(Color=lambda *color: color, Vector2=lambda x, y: (x, y), draw_text_ex=drawing),
                 'open': lambda *_args: io.StringIO(status)}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
    namespace['_draw_source_indicator'](NS(speed_limit_valid=False, speed_limit_last_valid=True, font_demi=None),
                                        NS(x=0, y=0, width=100, height=100))
    return drawing

  def test_tomtom_unavailable_and_retained_are_never_labelled_osm(self):
    for status in ['TomTom: 13.9 m/s', 'TomTom retained', 'TomTom unavailable']:
      self.assertEqual(self.draw(status).call_args.args[1], 'TT')

  def test_explicit_osm_status_and_unknown_status_are_distinguished(self):
    self.assertEqual(self.draw('OSM fallback').call_args.args[1], 'OSM')
    self.draw('unknown').assert_not_called()


if __name__ == '__main__':
  unittest.main()
