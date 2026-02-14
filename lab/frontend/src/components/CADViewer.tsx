import { useEffect, useState, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Center, Environment, ContactShadows } from '@react-three/drei';
import * as THREE from 'three';

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
        const response = await fetch(`/resources/file/${partName}/step`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const buffer = await response.arrayBuffer();
        const uint8Array = new Uint8Array(buffer);
        
        // Find the OCCT function (handle various potential names)
        // @ts-ignore
        const initFn = window.occtimportjs || window.occtImportJs;
        if (!initFn) {
            console.error("Available on window:", Object.keys(window));
            throw new Error("OCCT library not found on window object.");
        }

        const occt = await initFn();
        const result = occt.ReadStepFile(uint8Array, null);
        
        if (!result || !result.success) {
            throw new Error("OCCT failed to parse STEP file.");
        }

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
            color: 0x60a5fa,
            metalness: 0.5,
            roughness: 0.5,
            side: THREE.DoubleSide
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
    </div>
  );
};

export default CADViewer;
