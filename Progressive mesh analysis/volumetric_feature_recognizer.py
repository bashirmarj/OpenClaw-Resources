# -*- coding: utf-8 -*-
"""
Volumetric Subtraction-Based CAD Feature Recognition for Vectis Machining
Simple, stable approach using Boolean operations instead of topology analysis

Core Concept:
1. Get bounding box of part
2. Create solid volume from bounding box (box or cylinder)
3. Subtract actual part from bounding volume → removed material = features
4. Analyze removed volumes geometrically

This avoids MapShapesAndAncestors entirely and uses only stable OpenCascade operations.
"""

import time
import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# OpenCascade imports
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_SOLID, TopAbs_EDGE, TopAbs_VERTEX
from OCC.Core.TopoDS import topods
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.GeomAbs import (
    GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone, GeomAbs_Sphere,
    GeomAbs_Torus
)
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop_VolumeProperties, brepgprop_SurfaceProperties
from OCC.Core.gp import gp_Ax2, gp_Pnt, gp_Dir, gp_Vec
from OCC.Core.BRep import BRep_Tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RecognizedFeature:
    """Container for recognized manufacturing feature"""
    feature_type: str  # 'hole', 'pocket', 'slot', 'fillet', 'chamfer'
    subtype: Optional[str]  # 'through', 'blind', 'rectangular', etc.
    volume: float  # Volume of removed material
    confidence: float
    parameters: Dict[str, Any]  # Feature-specific parameters
    
    def to_dict(self) -> dict:
        return {
            'type': self.feature_type,
            'subtype': self.subtype,
            'volume': self.volume,
            'confidence': self.confidence,
            'parameters': self.parameters
        }


class VolumetricFeatureRecognizer:
    """
    Volumetric subtraction-based feature recognition
    Simple, stable, no topology graph construction required
    """
    
    def __init__(self, time_limit: int = 30, memory_limit_mb: int = 1800):
        self.time_limit = time_limit
        self.memory_limit_mb = memory_limit_mb
        self.shape = None
        self.features = []
        self.start_time = None
        
    def recognize_features(self, step_file_path: str) -> Dict:
        """Main entry point for feature recognition"""
        self.start_time = time.time()
        self.features = []
        
        logger.info(f"🔍 Starting volumetric feature recognition: {step_file_path}")
        
        try:
            # Load STEP file
            self.shape = self._load_step_file(step_file_path)
            if not self.shape:
                return self._error_response("Failed to load STEP file")
            
            # Determine part type (rectangular/cylindrical)
            part_type, bounding_info = self._analyze_part_geometry()
            logger.info(f"📐 Detected part type: {part_type}")
            
            # Create bounding volume and find removed material
            removed_volumes = self._find_removed_material(part_type, bounding_info)
            logger.info(f"✂️ Found {len(removed_volumes)} removed volumes")
            
            # Analyze each removed volume to classify feature type
            for volume_idx, removed_solid in enumerate(removed_volumes):
                if not self._check_constraints():
                    logger.warning("⏱️ Time limit exceeded, returning partial results")
                    break
                
                self._classify_removed_volume(removed_solid, volume_idx)
            
            # Generate response
            return self._generate_response()
            
        except Exception as e:
            logger.error(f"❌ Error during feature recognition: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._error_response(str(e))
    
    def _load_step_file(self, step_file_path: str):
        """Load STEP file using STEPControl_Reader"""
        try:
            reader = STEPControl_Reader()
            status = reader.ReadFile(str(step_file_path))
            
            if status != IFSelect_RetDone:
                logger.error("Failed to read STEP file")
                return None
            
            reader.TransferRoots()
            shape = reader.OneShape()
            
            logger.info(f"✅ Loaded STEP file successfully")
            return shape
            
        except Exception as e:
            logger.error(f"Error loading STEP file: {e}")
            return None
    
    def _analyze_part_geometry(self) -> Tuple[str, Dict]:
        """
        Determine if part is primarily rectangular or cylindrical
        Returns: ('rectangular' or 'cylindrical', bounding_info)
        """
        # Get bounding box
        bbox = Bnd_Box()
        brepbndlib.Add(self.shape, bbox)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
        
        # Calculate dimensions
        dx = xmax - xmin
        dy = ymax - ymin
        dz = zmax - zmin
        
        dimensions = sorted([dx, dy, dz])
        aspect_ratio = dimensions[2] / dimensions[0] if dimensions[0] > 0 else 1.0
        
        # Analyze surface types to determine part type
        cylindrical_area = 0.0
        planar_area = 0.0
        total_area = 0.0
        
        explorer = TopExp_Explorer(self.shape, TopAbs_FACE)
        while explorer.More():
            face = topods.Face(explorer.Current())
            surf_adaptor = BRepAdaptor_Surface(face, True)
            
            # Get face area
            props = GProp_GProps()
            brepgprop_SurfaceProperties(face, props)
            area = props.Mass()
            total_area += area
            
            # Classify surface type
            if surf_adaptor.GetType() == GeomAbs_Cylinder:
                cylindrical_area += area
            elif surf_adaptor.GetType() == GeomAbs_Plane:
                planar_area += area
            
            explorer.Next()
        
        # Determine part type based on surface areas
        cylindrical_ratio = cylindrical_area / total_area if total_area > 0 else 0
        
        if cylindrical_ratio > 0.3 and aspect_ratio > 2.0:
            # Likely a shaft or cylindrical part
            part_type = 'cylindrical'
            # Determine axis (longest dimension)
            if dz == max(dx, dy, dz):
                axis = 'Z'
                radius = max(dx, dy) / 2
                height = dz
            elif dy == max(dx, dy, dz):
                axis = 'Y'
                radius = max(dx, dz) / 2
                height = dy
            else:
                axis = 'X'
                radius = max(dy, dz) / 2
                height = dx
            
            bounding_info = {
                'type': 'cylindrical',
                'axis': axis,
                'radius': radius,
                'height': height,
                'center': ((xmin + xmax)/2, (ymin + ymax)/2, (zmin + zmax)/2),
                'bbox': (xmin, ymin, zmin, xmax, ymax, zmax)
            }
        else:
            # Rectangular/prismatic part
            part_type = 'rectangular'
            bounding_info = {
                'type': 'rectangular',
                'dimensions': (dx, dy, dz),
                'center': ((xmin + xmax)/2, (ymin + ymax)/2, (zmin + zmax)/2),
                'bbox': (xmin, ymin, zmin, xmax, ymax, zmax)
            }
        
        return part_type, bounding_info
    
    def _find_removed_material(self, part_type: str, bounding_info: Dict) -> List:
        """
        Create bounding volume, subtract actual part, return removed volumes
        This is the core of the volumetric approach
        """
        try:
            # Create bounding volume
            if part_type == 'cylindrical':
                bounding_solid = self._create_bounding_cylinder(bounding_info)
            else:
                bounding_solid = self._create_bounding_box(bounding_info)
            
            logger.info(f"📦 Created bounding {part_type} volume")
            
            # Perform Boolean subtraction: bounding_volume - actual_part = removed_material
            # This is the key operation - it's stable and doesn't use MapShapesAndAncestors
            cut_operation = BRepAlgoAPI_Cut(bounding_solid, self.shape)
            cut_operation.Build()
            
            if not cut_operation.IsDone():
                logger.warning("⚠️ Boolean cut operation failed")
                return []
            
            removed_material = cut_operation.Shape()
            logger.info("✂️ Boolean subtraction completed")
            
            # Extract individual solid volumes from the result
            removed_volumes = []
            explorer = TopExp_Explorer(removed_material, TopAbs_SOLID)
            while explorer.More():
                solid = topods.Solid(explorer.Current())
                removed_volumes.append(solid)
                explorer.Next()
            
            return removed_volumes
            
        except Exception as e:
            logger.error(f"Error in Boolean subtraction: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _create_bounding_box(self, bounding_info: Dict):
        """Create a solid box from bounding box dimensions"""
        xmin, ymin, zmin, xmax, ymax, zmax = bounding_info['bbox']
        
        # Create box primitive
        box = BRepPrimAPI_MakeBox(
            gp_Pnt(xmin, ymin, zmin),
            gp_Pnt(xmax, ymax, zmax)
        ).Shape()
        
        return box
    
    def _create_bounding_cylinder(self, bounding_info: Dict):
        """Create a solid cylinder from bounding info"""
        center = bounding_info['center']
        radius = bounding_info['radius'] * 1.1  # Slightly larger to ensure full coverage
        height = bounding_info['height']
        axis = bounding_info['axis']
        
        # Set up cylinder axis
        if axis == 'Z':
            axis_dir = gp_Dir(0, 0, 1)
            origin = gp_Pnt(center[0], center[1], center[2] - height/2)
        elif axis == 'Y':
            axis_dir = gp_Dir(0, 1, 0)
            origin = gp_Pnt(center[0], center[1] - height/2, center[2])
        else:  # X
            axis_dir = gp_Dir(1, 0, 0)
            origin = gp_Pnt(center[0] - height/2, center[1], center[2])
        
        ax2 = gp_Ax2(origin, axis_dir)
        cylinder = BRepPrimAPI_MakeCylinder(ax2, radius, height).Shape()
        
        return cylinder
    
    def _classify_removed_volume(self, solid, volume_idx: int):
        """
        Analyze a removed volume to determine what feature it represents
        This is where the progressive scanning approach would be enhanced
        """
        try:
            # Calculate volume
            props = GProp_GProps()
            brepgprop_VolumeProperties(solid, props)
            volume = props.Mass()
            
            if volume < 0.01:  # Ignore tiny volumes (likely numerical artifacts)
                return
            
            # Get bounding box of removed volume
            bbox = Bnd_Box()
            brepbndlib.Add(solid, bbox)
            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
            
            dx = xmax - xmin
            dy = ymax - ymin
            dz = zmax - zmin
            
            # Analyze faces in the removed volume
            face_types = self._analyze_faces_in_volume(solid)
            
            # Classification logic based on geometry
            feature = self._classify_by_geometry(
                volume, (dx, dy, dz), face_types, volume_idx
            )
            
            if feature:
                self.features.append(feature)
                logger.info(f"✓ Detected {feature.feature_type} ({feature.subtype}), confidence: {feature.confidence:.2f}")
            
        except Exception as e:
            logger.debug(f"Failed to classify volume {volume_idx}: {e}")
    
    def _analyze_faces_in_volume(self, solid) -> Dict[str, int]:
        """Analyze surface types in a removed volume"""
        face_types = {
            'cylindrical': 0,
            'planar': 0,
            'conical': 0,
            'spherical': 0,
            'other': 0
        }
        
        explorer = TopExp_Explorer(solid, TopAbs_FACE)
        while explorer.More():
            face = topods.Face(explorer.Current())
            surf_adaptor = BRepAdaptor_Surface(face, True)
            
            surf_type = surf_adaptor.GetType()
            if surf_type == GeomAbs_Cylinder:
                face_types['cylindrical'] += 1
            elif surf_type == GeomAbs_Plane:
                face_types['planar'] += 1
            elif surf_type == GeomAbs_Cone:
                face_types['conical'] += 1
            elif surf_type == GeomAbs_Sphere:
                face_types['spherical'] += 1
            else:
                face_types['other'] += 1
            
            explorer.Next()
        
        return face_types
    
    def _classify_by_geometry(self, volume: float, dimensions: Tuple[float, float, float],
                             face_types: Dict, volume_idx: int) -> Optional[RecognizedFeature]:
        """
        Classify feature based on geometric characteristics
        This is simplified - you can enhance with more sophisticated rules
        """
        dx, dy, dz = sorted(dimensions)
        aspect_ratio = dz / dx if dx > 0 else 1.0
        
        # HOLE DETECTION
        # Cylindrical removed volume with high aspect ratio
        if face_types['cylindrical'] >= 1 and aspect_ratio > 2.0:
            diameter = (dx + dy) / 2  # Approximate diameter
            depth = dz
            
            # Check if through hole or blind hole
            # Through holes typically have similar entry/exit dimensions
            # This is simplified - could be enhanced with more analysis
            is_through = aspect_ratio < 10.0  # Heuristic
            
            return RecognizedFeature(
                feature_type='hole',
                subtype='through' if is_through else 'blind',
                volume=volume,
                confidence=0.80 if face_types['cylindrical'] >= 1 else 0.60,
                parameters={
                    'diameter': diameter,
                    'depth': depth,
                    'volume_index': volume_idx
                }
            )
        
        # SLOT DETECTION
        # Elongated rectangular removed volume
        if face_types['planar'] >= 4 and aspect_ratio > 3.0:
            # Two similar dimensions (width), one much longer (length)
            dims = sorted(dimensions)
            width = dims[0]
            depth = dims[1]
            length = dims[2]
            
            return RecognizedFeature(
                feature_type='slot',
                subtype='rectangular_slot',
                volume=volume,
                confidence=0.75,
                parameters={
                    'width': width,
                    'depth': depth,
                    'length': length,
                    'volume_index': volume_idx
                }
            )
        
        # POCKET DETECTION
        # Rectangular removed volume with moderate aspect ratio
        if face_types['planar'] >= 3 and aspect_ratio < 3.0:
            # Nearly cubic or rectangular depression
            width = dx
            length = dy
            depth = dz
            
            return RecognizedFeature(
                feature_type='pocket',
                subtype='rectangular_pocket',
                volume=volume,
                confidence=0.70,
                parameters={
                    'width': width,
                    'length': length,
                    'depth': depth,
                    'volume_index': volume_idx
                }
            )
        
        # CHAMFER DETECTION
        # Small conical or wedge-shaped removed volume
        if face_types['conical'] >= 1 or (face_types['planar'] >= 2 and volume < 10.0):
            return RecognizedFeature(
                feature_type='chamfer',
                subtype='edge_chamfer',
                volume=volume,
                confidence=0.65,
                parameters={
                    'volume': volume,
                    'volume_index': volume_idx
                }
            )
        
        # FILLET DETECTION
        # Small rounded removed volume (torus-like or small cylinder at edge)
        if face_types['cylindrical'] >= 1 and volume < 20.0 and aspect_ratio < 2.0:
            radius = dx / 2  # Approximate fillet radius
            return RecognizedFeature(
                feature_type='fillet',
                subtype='constant_radius',
                volume=volume,
                confidence=0.65,
                parameters={
                    'radius': radius,
                    'volume_index': volume_idx
                }
            )
        
        # GENERIC FEATURE
        # Couldn't classify specifically, but it's removed material
        return RecognizedFeature(
            feature_type='generic_feature',
            subtype='unclassified',
            volume=volume,
            confidence=0.40,
            parameters={
                'dimensions': dimensions,
                'face_types': face_types,
                'volume_index': volume_idx
            }
        )
    
    def _check_constraints(self) -> bool:
        """Check if processing constraints are met"""
        elapsed = time.time() - self.start_time
        
        if elapsed > self.time_limit:
            logger.warning(f"⏱️ Time limit exceeded ({elapsed:.1f}s > {self.time_limit}s)")
            return False
        
        return True
    
    def _generate_response(self) -> Dict:
        """Generate final response with all detected features"""
        elapsed_time = time.time() - self.start_time
        
        # Group features by type
        feature_summary = {}
        for feature in self.features:
            feature_type = feature.feature_type
            feature_summary[feature_type] = feature_summary.get(feature_type, 0) + 1
        
        # Calculate average confidence
        avg_confidence = sum(f.confidence for f in self.features) / len(self.features) if self.features else 0.0
        
        response = {
            'status': 'success',
            'method': 'volumetric_subtraction',
            'num_features_detected': len(self.features),
            'feature_summary': feature_summary,
            'avg_confidence': avg_confidence,
            'inference_time_sec': elapsed_time,
            'instances': [f.to_dict() for f in self.features]
        }
        
        logger.info(f"✅ Recognition complete: {len(self.features)} features in {elapsed_time:.2f}s")
        return response
    
    def _error_response(self, error_message: str) -> Dict:
        """Generate error response"""
        return {
            'status': 'error',
            'error': error_message,
            'num_features_detected': 0,
            'instances': []
        }


# Test function for development
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        recognizer = VolumetricFeatureRecognizer()
        result = recognizer.recognize_features(sys.argv[1])
        
        print("\n=== Volumetric Feature Recognition Results ===")
        print(f"Status: {result.get('status')}")
        print(f"Method: {result.get('method')}")
        print(f"Features detected: {result.get('num_features_detected', 0)}")
        print(f"Processing time: {result.get('inference_time_sec', 0):.2f}s")
        print(f"Average confidence: {result.get('avg_confidence', 0):.2%}")
        
        if result.get('feature_summary'):
            print("\n=== Feature Summary ===")
            for feature_type, count in result['feature_summary'].items():
                print(f"  {feature_type}: {count}")
        
        if result.get('instances'):
            print("\n=== Feature Details ===")
            for i, feature in enumerate(result['instances'][:10]):  # Show first 10
                print(f"\nFeature {i+1}:")
                print(f"  Type: {feature.get('type')}")
                print(f"  Subtype: {feature.get('subtype')}")
                print(f"  Confidence: {feature.get('confidence'):.2%}")
                print(f"  Volume: {feature.get('volume'):.2f} mm³")
                if 'diameter' in feature.get('parameters', {}):
                    print(f"  Diameter: {feature['parameters']['diameter']:.2f} mm")
                if 'depth' in feature.get('parameters', {}):
                    print(f"  Depth: {feature['parameters']['depth']:.2f} mm")
    else:
        print("Usage: python volumetric_feature_recognizer.py <step_file_path>")
