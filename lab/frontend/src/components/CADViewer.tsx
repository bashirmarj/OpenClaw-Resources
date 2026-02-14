import { useEffect, useState, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Center, Environment, ContactShadows } from '@react-three/drei';
import * as THREE from 'three';
// @ts-ignore
import { ReadStepFile } from 'occt-import-js';

interface CADModelProps {
  partName: string;
  onFaceClick?: (faceId: number) => void;
}

const CADModel = ({ partName, onFaceClick }: CADModelProps) => {
  const [meshes, setMeshes] = useState<THREE.Mesh[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadModel() {
      setMeshes([]);
      setLoading(true);
      try {
        const backendUrl = "";
        const response = await fetch(`${backendUrl}/resources/file/${partName}/step`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const buffer = await response.arrayBuffer();
        const uint8Array = new Uint8Array(buffer);
        
        // @ts-ignore
        const initFn = window.occtImportJs || window.occtimportjs;
        if (!initFn) throw new Error("OCCT Import JS library not loaded. Check script tags.");
        const occt = await initFn();
        const result = occt.ReadStepFile(uint8Array, null);
        
        const newMeshes: THREE.Mesh[] = [];
        
        result.meshes.forEach((meshData: any) => {
          const geometry = new THREE.BufferGeometry();
          geometry.setAttribute('position', new THREE.Float32BufferAttribute(meshData.attributes.position.array, 3));
          if (meshData.attributes.normal) {
            geometry.setAttribute('normal', new THREE.Float32BufferAttribute(meshData.attributes.normal.array, 3));
          }
          if (meshData.attributes.index) {
            geometry.setIndex(new THREE.Uint32BufferAttribute(meshData.attributes.index.array, 1));
          }
          
          const material = new THREE.MeshStandardMaterial({ 
            color: 0x94a3b8,
            metalness: 0.6,
            roughness: 0.4,
            transparent: true,
            opacity: 1.0
          });
          
          const mesh = new THREE.Mesh(geometry, material);
          mesh.userData = { faceId: meshData.face_index }; 
          newMeshes.push(mesh);
        });
        
        setMeshes(newMeshes);
      } catch (err) {
        console.error("Failed to load STEP:", err);
      } finally {
        setLoading(false);
      }
    }
    loadModel();
  }, [partName]);

  if (loading) return null;

  return (
    <group>
      {meshes.map((mesh, i) => (
        <primitive 
          key={i} 
          object={mesh} 
          onClick={(e: any) => {
            e.stopPropagation();
            if (onFaceClick) onFaceClick(mesh.userData.faceId);
          }}
        />
      ))}
    </group>
  );
};

const CADViewer = ({ partName, onFaceClick }: { partName: string, onFaceClick?: (id: number) => void }) => {
  return (
    <div className="w-full h-full bg-slate-950 rounded-xl overflow-hidden border border-slate-800 shadow-2xl relative">
      <Canvas shadows gl={{ antialias: true }}>
        <PerspectiveCamera makeDefault position={[150, 150, 150]} fov={35} />
        <OrbitControls makeDefault minPolarAngle={0} maxPolarAngle={Math.PI / 1.75} />
        
        <ambientLight intensity={0.5} />
        <pointLight position={[100, 100, 100]} intensity={1} castShadow />
        <spotLight position={[-100, 100, 100]} angle={0.15} penumbra={1} intensity={1} />
        
        <Suspense fallback={null}>
          <Center top>
            <CADModel partName={partName} onFaceClick={onFaceClick} />
          </Center>
          <Environment preset="city" />
          <ContactShadows position={[0, -10, 0]} opacity={0.4} scale={20} blur={2} far={4.5} />
        </Suspense>
      </Canvas>
      
      <div className="absolute bottom-4 left-4 bg-slate-900/80 backdrop-blur border border-slate-700 p-2 rounded text-[10px] font-mono text-slate-400 uppercase tracking-wider">
        Renderer: WebGL / OCCT-JS Bridge
      </div>
    </div>
  );
};

export default CADViewer;
