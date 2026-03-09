"""
Tests for the deliveries utils module.
Tests the calculate_distance Haversine formula function.
"""
import pytest
from deliveries.utils import calculate_distance


class TestCalculateDistance:
    """Tests for the calculate_distance function using Haversine formula."""
    
    def test_same_location_returns_zero(self):
        """Test that distance between same point is zero."""
        lat, lon = -26.2041, 28.0473  # Johannesburg
        
        distance = calculate_distance(lat, lon, lat, lon)
        
        assert distance == 0.0
    
    def test_known_distance_johannesburg_to_pretoria(self):
        """Test distance between Johannesburg and Pretoria (~58 km)."""
        # Johannesburg coordinates
        jnb_lat, jnb_lon = -26.2041, 28.0473
        # Pretoria coordinates
        pta_lat, pta_lon = -25.7479, 28.2293
        
        distance = calculate_distance(jnb_lat, jnb_lon, pta_lat, pta_lon)
        
        # Should be approximately 58 km (allow 5km tolerance)
        assert 53 < distance < 63
    
    def test_known_distance_cape_town_to_durban(self):
        """Test distance between Cape Town and Durban (~1270 km)."""
        # Cape Town coordinates
        cpt_lat, cpt_lon = -33.9249, 18.4241
        # Durban coordinates
        dbn_lat, dbn_lon = -29.8587, 31.0218
        
        distance = calculate_distance(cpt_lat, cpt_lon, dbn_lat, dbn_lon)
        
        # Should be approximately 1270 km (allow 50km tolerance)
        assert 1220 < distance < 1320
    
    def test_short_distance_meters_level(self):
        """Test very short distance (meters level)."""
        # Two points very close together in Johannesburg
        lat1, lon1 = -26.2041, 28.0473
        lat2, lon2 = -26.2042, 28.0474  # About 100-150 meters away
        
        distance = calculate_distance(lat1, lon1, lat2, lon2)
        
        # Should be less than 1 km
        assert distance < 1
        # Should be greater than 0
        assert distance > 0
    
    def test_distance_is_symmetric(self):
        """Test that distance from A to B equals distance from B to A."""
        lat1, lon1 = -26.2041, 28.0473
        lat2, lon2 = -33.9249, 18.4241
        
        distance_ab = calculate_distance(lat1, lon1, lat2, lon2)
        distance_ba = calculate_distance(lat2, lon2, lat1, lon1)
        
        assert distance_ab == distance_ba
    
    def test_northern_hemisphere_coordinates(self):
        """Test with northern hemisphere coordinates."""
        # New York
        ny_lat, ny_lon = 40.7128, -74.0060
        # London
        london_lat, london_lon = 51.5074, -0.1278
        
        distance = calculate_distance(ny_lat, ny_lon, london_lat, london_lon)
        
        # Should be approximately 5570 km (allow 100km tolerance)
        assert 5400 < distance < 5700
    
    def test_cross_hemisphere_coordinates(self):
        """Test distance across hemispheres."""
        # São Paulo (Southern)
        sp_lat, sp_lon = -23.5505, -46.6333
        # Tokyo (Northern)
        tokyo_lat, tokyo_lon = 35.6762, 139.6503
        
        distance = calculate_distance(sp_lat, sp_lon, tokyo_lat, tokyo_lon)
        
        # Should be approximately 18500 km (allow 500km tolerance)
        assert 18000 < distance < 19000
    
    def test_international_date_line_crossing(self):
        """Test distance crossing international date line."""
        # Auckland, New Zealand
        auckland_lat, auckland_lon = -36.8485, 174.7633
        # Fiji
        fiji_lat, fiji_lon = -17.7134, -178.0650
        
        distance = calculate_distance(auckland_lat, auckland_lon, fiji_lat, fiji_lon)
        
        # Should be a reasonable distance (approximately 2100-2200 km)
        assert 2000 < distance < 2400
    
    def test_equator_distance(self):
        """Test distance along the equator."""
        # Point on equator
        lat1, lon1 = 0.0, 0.0
        lat2, lon2 = 0.0, 1.0  # 1 degree longitude difference
        
        distance = calculate_distance(lat1, lon1, lat2, lon2)
        
        # 1 degree at equator ≈ 111 km
        assert 100 < distance < 120
    
    def test_returns_float(self):
        """Test that function returns a float."""
        result = calculate_distance(-26.0, 28.0, -25.0, 27.0)
        
        assert isinstance(result, float)
    
    def test_typical_delivery_radius(self):
        """Test distance within typical delivery radius (5km)."""
        # Sandton, Johannesburg
        center_lat, center_lon = -26.1076, 28.0567
        # Point ~3km away
        nearby_lat, nearby_lon = -26.0876, 28.0567
        
        distance = calculate_distance(center_lat, center_lon, nearby_lat, nearby_lon)
        
        # Should be approximately 2-3 km
        assert 2 < distance < 4
