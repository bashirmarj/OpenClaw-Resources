import { useEffect, useState, Suspense, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera, Center } from "@react-three/drei";
import * as THREE from "three";
import { MeshModel } from "./cad-viewer/MeshModel";
import { ProfessionalLighting } from "./cad-viewer/enhancements/ProfessionalLighting";

const CADViewer = ({ partName, onFaceClick }: { partName: string; onFaceClick?: (id: number) => void }) => {
  const [meshData, setMeshData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const response = await fetch(`/resources/data/${partName}/mesh`);
        const data = await response.json();
        setMeshData(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [partName]);

  return (
    <div className="w-full h-full bg-slate-950 rounded-xl overflow-hidden border border-slate-800 shadow-2xl relative">
      <Canvas shadows gl={{ antialias: true, logarithmicDepthBuffer: true }}>
        <PerspectiveCamera makeDefault position={[150, 150, 150]} fov={45} />
        <OrbitControls makeDefault />
        <ProfessionalLighting intensity={2.5} enableShadows={true} />
        
        <Suspense fallback={null}>
          <Center top>
            {meshData && (
              <MeshModel 
                meshData={meshData} 
                sectionPlane="none" 
                sectionPosition={0} 
                showEdges={true} 
                displayStyle="solid"
              />
            )}
          </Center>
        </Suspense>
      </Canvas>
    </div>
  );
};

export default CADViewer;
