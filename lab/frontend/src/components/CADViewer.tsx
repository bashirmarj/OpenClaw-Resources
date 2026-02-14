import { useEffect, useState, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Center, Environment, ContactShadows } from '@react-three/drei';
import * as THREE from 'three';

interface CADModelProps {
  partName: string;
  onFaceClick?: (faceId: number) => void;
}

const CADModel = ({ partName, onFaceClick }: CADModelProps) => {
  const [mesh, setMesh] = useState<THREE.Mesh | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadModel() {
      setMesh(null);
      setLoading(true);
      try {
        const backendUrl = "";
        const response = await fetch(`${backendUrl}/resources/data/${partName}/mesh`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const data = await response.json();
        
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(data.vertices, 3));
        if (data.normals && data.normals.length > 0) {
            geometry.setAttribute('normal', new THREE.Float32BufferAttribute(data.normals, 3));
        } else {
            geometry.computeVertexNormals();
        }
        
        if (data.indices) {
            geometry.setIndex(data.indices);
        }
        
        const material = new THREE.MeshStandardMaterial({ 
            color: 0x60a5fa,
            metalness: 0.5,
            roughness: 0.5,
            side: THREE.DoubleSide
        });
        
        const newMesh = new THREE.Mesh(geometry, material);
        setMesh(newMesh);
      } catch (err) {
        console.error("Failed to load Mesh Data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadModel();
  }, [partName]);

  if (loading || !mesh) return null;

  return (
    <primitive 
        object={mesh} 
        onClick={(e: any) => {
            e.stopPropagation();
            // Face selection logic can be enhanced here using face_mapping
            if (onFaceClick) onFaceClick(0); 
        }}
    />
  );
};

const CADViewer = ({ partName, onFaceClick }: { partName: string, onFaceClick?: (id: number) => void }) => {
  return (
    <div className="w-full h-full bg-slate-950 rounded-xl overflow-hidden border border-slate-800 shadow-2xl relative">
      <Canvas shadows gl={{ antialias: true }}>
        <PerspectiveCamera makeDefault position={[150, 150, 150]} fov={35} />
        <OrbitControls makeDefault minPolarAngle={0} maxPolarAngle={Math.PI / 1.75} />
        
        <ambientLight intensity={1.5} />
        <pointLight position={[100, 100, 100]} intensity={2} castShadow />
        <spotLight position={[-100, 100, 100]} angle={0.15} penumbra={1} intensity={2} />
        
        <Suspense fallback={null}>
          <Center top>
            <CADModel partName={partName} onFaceClick={onFaceClick} />
          </Center>
          <Environment preset="city" />
          <ContactShadows position={[0, -10, 0]} opacity={0.4} scale={20} blur={2} far={4.5} />
        </Suspense>
      </Canvas>
      
      <div className="absolute bottom-4 left-4 bg-slate-900/80 backdrop-blur border border-slate-700 p-2 rounded text-[10px] font-mono text-slate-400 uppercase tracking-wider">
        Renderer: WebGL / Backend Processed
      </div>
    </div>
  );
};

export default CADViewer;
