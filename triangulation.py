"""Triangulation and position estimation utilities"""
import math
import numpy as np
from typing import List, Tuple, Optional


def rssi_to_distance(rssi: int, tx_power: int = -59, n: float = 2.5) -> float:
    """
    Convert RSSI to distance in meters using log-distance path loss model.
    
    Args:
        rssi: Received Signal Strength Indicator in dBm
        tx_power: Transmitter power at 1 meter (default -59 for WiFi, -59 for BLE)
        n: Path loss exponent (2.0 = free space, 2.5-4.0 = indoor)
    
    Returns:
        Estimated distance in meters
    """
    if rssi == 0:
        return -1.0  # Cannot compute
    
    # Path loss formula: RSSI = TxPower - 10*n*log10(distance)
    # Rearranged: distance = 10^((TxPower - RSSI) / (10*n))
    ratio = (tx_power - rssi) / (10.0 * n)
    distance = math.pow(10, ratio)
    
    return max(0.1, distance)  # Minimum 0.1m


def trilaterate_2d(stations: List[Tuple[float, float]], distances: List[float]) -> Optional[Tuple[float, float]]:
    """
    Perform 2D trilateration to estimate device position.
    
    Args:
        stations: List of (x, y) coordinates of stations (normalized 0-1)
        distances: List of distances from each station (in normalized units)
    
    Returns:
        Estimated (x, y) position or None if calculation fails
    """
    if len(stations) < 3 or len(stations) != len(distances):
        return None
    
    try:
        # Use least squares method for trilateration
        # We'll use the first three stations for basic trilateration
        # and can extend to use all available stations for better accuracy
        
        # Convert to numpy arrays
        stations_array = np.array(stations[:3])
        distances_array = np.array(distances[:3])
        
        # Use the first station as reference
        x1, y1 = stations_array[0]
        x2, y2 = stations_array[1]
        x3, y3 = stations_array[2]
        
        r1, r2, r3 = distances_array[0], distances_array[1], distances_array[2]
        
        # Calculate using the formula for trilateration
        A = 2 * (x2 - x1)
        B = 2 * (y2 - y1)
        C = r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2
        
        D = 2 * (x3 - x2)
        E = 2 * (y3 - y2)
        F = r2**2 - r3**2 - x2**2 + x3**2 - y2**2 + y3**2
        
        # Solve the system of linear equations
        denominator = A * E - B * D
        
        if abs(denominator) < 1e-10:
            # Stations are collinear, use weighted centroid instead
            weights = [1.0 / max(d, 0.01) for d in distances_array]
            total_weight = sum(weights)
            x = sum(s[0] * w for s, w in zip(stations_array, weights)) / total_weight
            y = sum(s[1] * w for s, w in zip(stations_array, weights)) / total_weight
            return (x, y)
        
        x = (C * E - F * B) / denominator
        y = (A * F - C * D) / denominator
        
        # Clamp to valid range (0-1 for normalized coordinates)
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))
        
        return (x, y)
        
    except Exception as e:
        print(f"Trilateration error: {e}")
        return None


def smooth_position(current: Tuple[float, float], 
                   new: Tuple[float, float], 
                   alpha: float = 0.3) -> Tuple[float, float]:
    """
    Apply exponential moving average to smooth position estimates.
    
    Args:
        current: Current position (x, y)
        new: New position estimate (x, y)
        alpha: Smoothing factor (0-1, higher = more weight to new value)
    
    Returns:
        Smoothed position (x, y)
    """
    if current is None:
        return new
    
    x = alpha * new[0] + (1 - alpha) * current[0]
    y = alpha * new[1] + (1 - alpha) * current[1]
    
    return (x, y)


def normalize_distance(distance_meters: float, map_scale: float = 20.0) -> float:
    """
    Convert distance in meters to normalized map coordinates.
    
    Args:
        distance_meters: Distance in meters
        map_scale: Real-world width/height that the map represents (in meters)
    
    Returns:
        Normalized distance (0-1 scale)
    """
    return distance_meters / map_scale
