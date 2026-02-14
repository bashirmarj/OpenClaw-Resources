import logging
import numpy as np
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.BRep import BRep_Tool
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.Poly import Poly_Triangulation

logger = logging.getLogger(__name__)

class GeometryProcessor:
    def process_step_file(self, file_path: str):
        """
        Parses a STEP file and returns mesh data in JSON-compatible format.
        """
        reader = STEPControl_Reader()
        status = reader.ReadFile(file_path)
        
        if status != 1:
            raise Exception(f"Failed to read STEP file: {file_path}")
            
        reader.TransferRoots()
        shape = reader.OneShape()
        
        # Tessellate
        mesh = BRepMesh_IncrementalMesh(shape, 0.1) # Linear deflection
        mesh.Perform()
        
        vertices = []
        indices = []
        normals = []
        
        explorer = TopExp_Explorer(shape, TopAbs_FACE)
        face_index = 1
        
        while explorer.More():
            face = explorer.Current()
            location = TopLoc_Location()
            triangulation = BRep_Tool.Triangulation(face, location)
            
            if triangulation:
                # Get transformation matrix
                trans = location.Transformation()
                
                # Current vertex count to offset indices
                v_offset = len(vertices) // 3
                
                # Vertices
                for i in range(1, triangulation.NbNodes() + 1):
                    pnt = triangulation.Node(i)
                    pnt.Transform(trans)
                    vertices.extend([pnt.X(), pnt.Y(), pnt.Z()])
                    
                    # Basic normal placeholder (could be improved with Adaptor)
                    normals.extend([0, 0, 1])
                
                # Indices
                for i in range(1, triangulation.NbTriangles() + 1):
                    tri = triangulation.Triangle(i)
                    # OpenCascade uses 1-based indexing
                    i1, i2, i3 = tri.Get()
                    indices.extend([i1 - 1 + v_offset, i2 - 1 + v_offset, i3 - 1 + v_offset])
            
            explorer.Next()
            face_index += 1
            
        return {
            "vertices": vertices,
            "indices": indices,
            "normals": normals,
            "triangle_count": len(indices) // 3
        }
