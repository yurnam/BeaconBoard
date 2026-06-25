"""Tests for triangulation.py module."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from triangulation import rssi_to_distance, trilaterate_2d, smooth_position, normalize_distance


class TestRssiToDistance:
    """Tests for RSSI to distance conversion."""

    def test_rss_to_zero_returns_negative_one(self):
        assert rssi_to_distance(0) == -1.0

    def test_strong_signal_short_distance(self):
        # TxPower=-59, RSSI=-59 => ratio=0 => distance=1m (capped at 0.1m min)
        result = rssi_to_distance(-59)
        assert result == 1.0

    def test_weak_signal_long_distance(self):
        # RSSI=-79 => ratio=20/25=0.8 => 10^0.8 ≈ 6.3m
        result = rssi_to_distance(-79)
        assert result > 6.0 and result < 7.0

    def test_very_weak_signal_further(self):
        # RSSI=-100 => ratio=41/25≈1.64 => 10^1.64 ≈ 43m
        result = rssi_to_distance(-100)
        assert result > 40.0 and result < 50.0

    def test_custom_path_loss_exponent(self):
        result = rssi_to_distance(-59, n=2.0)
        # With n=2.0 same RSSI gives shorter distance (free space)
        assert result == 1.0

    def test_result_min_cap_at_0_1(self):
        # Extremely strong signal that would give < 0.1m should be capped
        result = rssi_to_distance(-40, tx_power=-59, n=2.5)
        assert result >= 0.1

    def test_increasing_rssi_shorter_distance(self):
        d1 = rssi_to_distance(-80)
        d2 = rssi_to_distance(-50)
        assert d2 < d1


class TestTrilaterate2d:
    """Tests for 2D trilateration."""

    def test_less_than_three_stations(self):
        result = trilaterate_2d([(0.0, 0.0)], [1.0])
        assert result is None

    def test_mismatched_lists(self):
        result = trilaterate_2d(
            [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)],
            [1.0]
        )
        assert result is None

    def test_equal_distances_gives_center(self):
        stations = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)]
        distances = [0.57, 0.57, 0.57]
        result = trilaterate_2d(stations, distances)
        assert result is not None
        # Should be near the center of the equilateral triangle
        x, y = result
        assert 0.4 < x < 0.6

    def test_clamped_to_zero_one(self):
        stations = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)]
        # Very small distances should push result inside the triangle
        distances = [0.1, 0.1, 0.1]
        result = trilaterate_2d(stations, distances)
        assert result is not None
        x, y = result
        assert 0.0 <= x <= 1.0
        assert 0.0 <= y <= 1.0

    def test_collinear_falls_back_to_weighted_centroid(self):
        # Three collinear stations (all on x-axis)
        stations = [(0.0, 0.0), (0.5, 0.0), (1.0, 0.0)]
        distances = [0.25, 0.25, 0.25]
        result = trilaterate_2d(stations, distances)
        assert result is not None

    def test_asymmetric_distances(self):
        stations = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)]
        device is known to be closer to station 1
        distances = [0.1, 0.7, 0.7]
        result = trilaterate_2d(stations, distances)
        assert result is not None
        x, y = result
        # Should be close to station at (0, 0) but within bounds
        assert abs(x - 0.05) < 0.1


class TestSmoothPosition:
    """Tests for position smoothing."""

    def test_none_current_returns_new(self):
        result = smooth_position(None, (0.5, 0.8))
        assert result == (0.5, 0.8)

    def test_alpha_1_full_weight_new(self):
        result = smooth_position((0.0, 0.0), (1.0, 1.0), alpha=1.0)
        assert result == (1.0, 1.0)

    def test_alpha_0_no_change(self):
        result = smooth_position((0.3, 0.4), (1.0, 1.0), alpha=0.0)
        assert result == (0.3, 0.4)

    def test_alpha_0_5_weighted(self):
        current = (0.0, 0.0)
        new = (2.0, 4.0)
        result = smooth_position(current, new, alpha=0.5)
        assert result == (1.0, 2.0)

    def test_default_smoothing(self):
        current = (0.0, 0.0)
        new = (10.0, 10.0)
        result = smooth_position(current, new)  # default alpha=0.3
        assert result == pytest.approx((3.0, 3.0), abs=0.01)


class TestNormalizeDistance:
    """Tests for distance normalization."""

    def test_zero_meters(self):
        assert normalize_distance(0.0) == 0.0

    def test_full_scale_20m(self):
        result = normalize_distance(20.0, map_scale=20.0)
        assert result == 1.0

    def test_half_scale(self):
        result = normalize_distance(10.0, map_scale=20.0)
        assert result == pytest.approx(0.5)

    def test_double_scale(self):
        result = normalize_distance(40.0, map_scale=20.0)
        assert result == 2.0

    def test_custom_scale(self):
        result = normalize_distance(5.0, map_scale=50.0)
        assert result == pytest.approx(0.1)
