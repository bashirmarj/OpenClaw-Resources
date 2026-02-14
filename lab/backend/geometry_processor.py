import logging
import os
import json

# Attempt to load heavy engines
try:
    from OCP.STEPControl import STEPControl_Reader
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    ENGINE = "OCP"
except ImportError:
    try:
        from OCC.Core.STEPControl import STEPControl_Reader
        from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
        from OCC.Core.TopAbs import TopAbs_FACE
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.BRep import BRep_Tool
        from OCC.Core.TopLoc import TopLoc_Location
        ENGINE = "OCC"
    except ImportError:
        ENGINE = "FALLBACK"

logger = logging.getLogger(__name__)

class GeometryProcessor:
    def process_step_file(self, file_path: str):
        # If we have a real CAD engine, use it for high precision
        if ENGINE != "FALLBACK":
            return self._process_with_occ(file_path)
        
        # If no CAD engine, try to find a pre-processed JSON in the same folder
        # (This is a trick to make the lab work if the machine can't run OCC)
        json_path = os.path.join(os.path.dirname(file_path), "mesh_data.json")
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                return json.load(f)
                
        raise Exception("No 3D engine (OCP/OCC) found on this machine and no cached mesh data exists.")

    def _process_with_occ(self, file_path):
        # Implementation from previous working version
        reader = STEPControl_Reader()
        if reader.ReadFile(file_path) != 1:
            raise Exception("Failed to read STEP")
        reader.TransferRoots()
        shape = reader.OneShape()
        BRepMesh_IncrementalMesh(shape, 0.05, False, 0.5)
        
        vertices, indices = [], []
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
        return {"vertices": vertices, "indices": indices, "normals": [], "triangle_count": len(indices) // 3}
