import logging
import os

# Try to use OCP (the engine behind CadQuery)
try:
    from OCP.STEPControl import STEPControl_Reader
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    ENGINE = "OCP"
except ImportError:
    # Fallback to pythonocc-core if present
    try:
        from OCC.Core.STEPControl import STEPControl_Reader
        from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
        from OCC.Core.TopAbs import TopAbs_FACE
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.BRep import BRep_Tool
        from OCC.Core.TopLoc import TopLoc_Location
        ENGINE = "OCC"
    except ImportError:
        ENGINE = None

logger = logging.getLogger(__name__)

class GeometryProcessor:
    def process_step_file(self, file_path: str):
        if not ENGINE:
            raise Exception("No geometry engine found. Please install 'cadquery' (for OCP) or 'pythonocc-core'.")

        reader = STEPControl_Reader()
        status = reader.ReadFile(file_path)
        
        if status != 1:
            raise Exception(f"Failed to read STEP file: {file_path}")
            
        reader.TransferRoots()
        shape = reader.OneShape()
        
        # Tessellate
        mesh = BRepMesh_IncrementalMesh(shape, 0.1) 
        mesh.Perform()
        
        vertices = []
        indices = []
        
        explorer = TopExp_Explorer(shape, TopAbs_FACE)
        
        while explorer.More():
            face = explorer.Current()
            location = TopLoc_Location()
            triangulation = BRep_Tool.Triangulation(face, location)
            
            if triangulation:
                trans = location.Transformation()
                v_offset = len(vertices) // 3
                
                for i in range(1, triangulation.NbNodes() + 1):
                    pnt = triangulation.Node(i)
                    # Handle engine differences in Transform call if any
                    pnt.Transform(trans)
                    vertices.extend([pnt.X(), pnt.Y(), pnt.Z()])
                
                for i in range(1, triangulation.NbTriangles() + 1):
                    tri = triangulation.Triangle(i)
                    i1, i2, i3 = tri.Get()
                    indices.extend([i1 - 1 + v_offset, i2 - 1 + v_offset, i3 - 1 + v_offset])
            
            explorer.Next()
            
        return {
            "vertices": vertices,
            "indices": indices,
            "engine": ENGINE
        }
