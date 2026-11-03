import pytest

from openpilot.cereal.messaging import FrequencyTracker


@pytest.mark.parametrize('times', [[100., 100.], [100., 101., 100.], [100., 99.]])
def test_nonpositive_average_is_invalid(times):
  tracker = FrequencyTracker(20., 20., False)
  for timestamp in times:
    tracker.record_recv_time(timestamp)
  assert not tracker.valid


def test_recovers_after_repeated_receive_timestamp():
  tracker = FrequencyTracker(20., 20., False)
  tracker.record_recv_time(100.)
  tracker.record_recv_time(100.)
  assert not tracker.valid
  for i in range(1, 21):
    tracker.record_recv_time(100. + i / 20.)
  assert tracker.valid


def test_zero_recent_average_does_not_crash_when_long_average_is_invalid():
  tracker = FrequencyTracker(20., 20., False)
  for i in range(11):
    tracker.record_recv_time(100. + 2. * i)
  for _ in range(20):
    tracker.record_recv_time(120.)
  assert tracker.avg_dt.get_average() > 0.
  assert tracker.recent_avg_dt.get_average() == 0.
  assert not tracker.valid


def test_valid_recent_window_can_recover_from_zero_long_average():
  tracker = FrequencyTracker(8., 8., False)
  for timestamp in [100., 99., *(99. + i / 8. for i in range(1, 9))]:
    tracker.record_recv_time(timestamp)
  assert tracker.avg_dt.get_average() == 0.
  assert tracker.recent_avg_dt.get_average() > 0.
  assert tracker.valid
