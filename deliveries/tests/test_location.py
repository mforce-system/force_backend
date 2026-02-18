import pytest
from deliveries.location import calculate_distance, estimate_eta, parse_coordinates


class TestLocationUtilities:
    """Test location calculation utilities"""
    
    def test_calculate_distance(self):
        """Test Haversine distance calculation"""
        # New York to Los Angeles (approximate)
        ny_lat, ny_lon = 40.7128, -74.0060
        la_lat, la_lon = 34.0522, -118.2437
        
        distance = calculate_distance(ny_lat, ny_lon, la_lat, la_lon)
        
        # Should be approximately 3944 km
        assert 3900 < distance < 4000
    
    def test_calculate_distance_same_location(self):
        """Distance between same coordinates should be 0"""
        distance = calculate_distance(0.0, 0.0, 0.0, 0.0)
        assert distance == 0.0
    
    def test_estimate_eta(self):
        """Test ETA calculation"""
        # 30km at 30km/h = 60 minutes
        eta = estimate_eta(30, avg_speed_kmh=30)
        assert eta == 60
        
        # 15km at 30km/h = 30 minutes
        eta = estimate_eta(15, avg_speed_kmh=30)
        assert eta == 30
    
    def test_estimate_eta_zero_distance(self):
        """ETA for zero distance should be 0"""
        eta = estimate_eta(0)
        assert eta == 0
    
    def test_parse_coordinates_valid(self):
        """Test parsing valid coordinate string"""
        lat, lon = parse_coordinates("40.7128, -74.0060")
        assert lat == 40.7128
        assert lon == -74.0060
    
    def test_parse_coordinates_no_spaces(self):
        """Test parsing without spaces"""
        lat, lon = parse_coordinates("34.0522,-118.2437")
        assert lat == 34.0522
        assert lon == -118.2437
    
    def test_parse_coordinates_invalid(self):
        """Test parsing invalid format raises ValueError"""
        with pytest.raises(ValueError):
            parse_coordinates("invalid")
        
        with pytest.raises(ValueError):
            parse_coordinates("40.7128")
