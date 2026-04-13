"""
H3 Spatial Grid Generator
Creates hexagonal grid for Miami-Dade County using Uber H3
"""
import h3
from typing import List, Dict, Tuple, Set
from shapely.geometry import Polygon, Point
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


class H3GridGenerator:
    """
    Generates and manages H3 hexagonal grid for spatial analysis
    
    H3 Resolution Guide:
    - Res 7: ~5.16 km² per hexagon (too large)
    - Res 8: ~0.74 km² per hexagon (good for city-level)
    - Res 9: ~0.10 km² per hexagon (ideal for neighborhood analysis)
    - Res 10: ~0.015 km² per hexagon (too granular)
    
    Default: Resolution 9 (~174m edge length, ~100k m²)
    """
    
    def __init__(self, resolution: int = None):
        """
        Initialize H3 grid generator
        
        Args:
            resolution: H3 resolution level (default from settings)
        """
        self.resolution = resolution or settings.default_h3_resolution
        self.bbox = {
            "min_lat": settings.bbox_min_lat,
            "min_lng": settings.bbox_min_lng,
            "max_lat": settings.bbox_max_lat,
            "max_lng": settings.bbox_max_lng
        }
        
        logger.info(f"H3 Grid Generator initialized with resolution {self.resolution}")
    
    def generate_grid(self) -> Set[str]:
        """
        Generate complete H3 grid for Miami-Dade County
        
        Returns:
            Set of H3 cell IDs (strings)
        """
        logger.info("Generating H3 grid for Miami-Dade County...")
        
        # Create bounding box polygon
        bbox_polygon = Polygon([
            (self.bbox["min_lng"], self.bbox["min_lat"]),
            (self.bbox["max_lng"], self.bbox["min_lat"]),
            (self.bbox["max_lng"], self.bbox["max_lat"]),
            (self.bbox["min_lng"], self.bbox["max_lat"]),
            (self.bbox["min_lng"], self.bbox["min_lat"])
        ])
        
        # Convert polygon to GeoJSON format for H3
        geojson = {
            "type": "Polygon",
            "coordinates": [list(bbox_polygon.exterior.coords)]
        }
        
        # Generate H3 cells that cover the polygon
        h3_cells = h3.polyfill_geojson(geojson, self.resolution)
        
        logger.info(f"Generated {len(h3_cells)} H3 cells at resolution {self.resolution}")
        
        return h3_cells
    
    def get_cell_from_point(self, lat: float, lng: float) -> str:
        """
        Get H3 cell ID for a given point
        
        Args:
            lat: Latitude
            lng: Longitude
        
        Returns:
            H3 cell ID (string)
        """
        return h3.geo_to_h3(lat, lng, self.resolution)
    
    def get_cell_center(self, h3_cell: str) -> Tuple[float, float]:
        """
        Get center coordinates of an H3 cell
        
        Args:
            h3_cell: H3 cell ID
        
        Returns:
            (latitude, longitude) tuple
        """
        lat, lng = h3.h3_to_geo(h3_cell)
        return (lat, lng)
    
    def get_cell_boundary(self, h3_cell: str) -> List[Tuple[float, float]]:
        """
        Get boundary coordinates of an H3 cell
        
        Args:
            h3_cell: H3 cell ID
        
        Returns:
            List of (lat, lng) tuples forming hexagon boundary
        """
        boundary = h3.h3_to_geo_boundary(h3_cell)
        return boundary
    
    def get_neighbors(self, h3_cell: str, ring: int = 1) -> Set[str]:
        """
        Get neighboring H3 cells
        
        Args:
            h3_cell: Center H3 cell ID
            ring: Ring distance (1 = immediate neighbors, 2 = second ring, etc.)
        
        Returns:
            Set of neighboring H3 cell IDs
        """
        return h3.k_ring(h3_cell, ring)
    
    def get_distance(self, h3_cell1: str, h3_cell2: str) -> int:
        """
        Get grid distance between two H3 cells
        
        Args:
            h3_cell1: First H3 cell ID
            h3_cell2: Second H3 cell ID
        
        Returns:
            Number of cells between them (0 if same cell)
        """
        return h3.h3_distance(h3_cell1, h3_cell2)
    
    def cells_in_radius(self, lat: float, lng: float, radius_meters: float) -> Set[str]:
        """
        Get all H3 cells within a radius of a point
        
        Args:
            lat: Center latitude
            lng: Center longitude
            radius_meters: Radius in meters
        
        Returns:
            Set of H3 cell IDs within radius
        """
        # Get center cell
        center_cell = self.get_cell_from_point(lat, lng)
        
        # Calculate how many rings we need based on radius
        # H3 res 9 has ~174m edge length, so diameter ~348m
        edge_length = h3.edge_length(self.resolution, 'm')
        rings_needed = int(radius_meters / edge_length) + 1
        
        # Get all cells in radius
        cells = h3.k_ring(center_cell, rings_needed)
        
        # Filter to exact radius
        filtered_cells = set()
        center_point = Point(lng, lat)
        
        for cell in cells:
            cell_lat, cell_lng = self.get_cell_center(cell)
            cell_point = Point(cell_lng, cell_lat)
            
            # Approximate distance (good enough for filtering)
            distance = center_point.distance(cell_point) * 111000  # Rough deg to meters
            
            if distance <= radius_meters:
                filtered_cells.add(cell)
        
        return filtered_cells
    
    def get_grid_stats(self) -> Dict[str, any]:
        """
        Get statistics about the H3 grid
        
        Returns:
            Dictionary with grid statistics
        """
        cells = self.generate_grid()
        
        # Calculate coverage area
        edge_length_km = h3.edge_length(self.resolution, 'km')
        cell_area_km2 = h3.hex_area(self.resolution, 'km^2')
        total_area_km2 = len(cells) * cell_area_km2
        
        return {
            "resolution": self.resolution,
            "total_cells": len(cells),
            "edge_length_m": edge_length_km * 1000,
            "cell_area_m2": cell_area_km2 * 1_000_000,
            "cell_area_km2": cell_area_km2,
            "total_coverage_km2": total_area_km2,
            "bounding_box": self.bbox
        }


# Singleton instance for global use
_h3_generator = None

def get_h3_generator() -> H3GridGenerator:
    """Get singleton H3 grid generator instance"""
    global _h3_generator
    if _h3_generator is None:
        _h3_generator = H3GridGenerator()
    return _h3_generator
