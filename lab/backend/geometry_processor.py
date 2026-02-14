import logging
import numpy as np
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.BRep import BRep_Tool
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib

logger = logging.getLogger(__name__)

class GeometryProcessor:
    def process_step_file(self, file_path: str):
        reader = STEPControl_Reader()
        if reader.ReadFile(file_path) != 1:
            raise Exception("Failed to read STEP")
            
        reader.TransferRoots()
        shape = reader.OneShape()
        
        # High-res mesh
        BRepMesh_IncrementalMesh(shape, 0.05, False, 0.5)
        
        vertices = []
        indices = []
        normals = []
        
        explorer = TopExp_Explorer(shape, TopAbs_FACE)
        while explorer.More():
            face = explorer.Current()
            loc = TopLoc_Location()
            tri = BRep_Tool.Triangulation(face, loc)
            
            if tri:
                v_offset = len(vertices) // 3
                trans = loc.Transformation()
                
                for i in range(1, tri.NbNodes() + 1):
                    p = tri.Node(i).Transformed(trans)
                    vertices.extend([p.X(), p.Y(), p.Z()])
                    
                for i in range(1, tri.NbTriangles() + 1):
                    t = tri.Triangle(i)
                    i1, i2, i3 = t.Get()
                    indices.extend([i1-1+v_offset, i2-1+v_offset, i3-1+v_offset])
            explorer.Next()
            
        # Re-compute normals if needed
        return {
            "vertices": vertices,
            "indices": indices,
            "normals": [], # Let Three.js compute smooth normals
            "triangle_count": len(indices) // 3
        }
