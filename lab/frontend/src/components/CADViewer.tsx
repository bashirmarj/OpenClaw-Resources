import { useEffect, useState, Suspense, useRef } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Center, Environment, ContactShadows } from '@react-three/drei';
import * as THREE from 'three';

interface CADModelProps {
  partName: string;
  onFaceClick?: (faceId: number) => void;
}

const CADModel = ({ partName, onFaceClick }: CADModelProps) => {
  const [meshes, setMeshes] = useState<THREE.Mesh[]>([]);
  const [loading, setLoading] = useState(true);
  const { camera, controls } = useThree();

  useEffect(() => {
    async function loadModel() {
      setMeshes([]);
      setLoading(true);
      try {
        const response = await fetch(`/resources/file/${partName}/step`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const buffer = await response.arrayBuffer();
        const uint8Array = new Uint8Array(buffer);
        
        // @ts-ignore
        const initFn = window.occtimportjs || window.occtImportJs;
        if (!initFn) throw new Error("OCCT library not found on window object.");

        const occt = await initFn();
        const result = occt.ReadStepFile(uint8Array, null);
        
        if (!result || !result.success) throw new Error("OCCT failed to parse STEP file.");

        const newMeshes: THREE.Mesh[] = [];
        const boundingBox = new THREE.Box3();
        
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
          
          geometry.computeBoundingBox();
          if (geometry.boundingBox) boundingBox.expandByPoint(geometry.boundingBox.min).expandByPoint(geometry.boundingBox.max);
        });
        
        setMeshes(newMeshes);

        // Auto-focus camera
        if (!boundingBox.isEmpty()) {
            const center = new THREE.Vector3();
            boundingBox.getCenter(center);
            const size = new THREE.Vector3();
            boundingBox.getSize(size);
            const maxDim = Math.max(size.x, size.y, size.z);
            const fov = (camera as THREE.PerspectiveCamera).fov * (Math.PI / 180);
            let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
            cameraZ *= 2.5; // Zoom out a bit

            camera.position.set(center.x + cameraZ, center.y + cameraZ, center.z + cameraZ);
            camera.lookAt(center);
            if (controls) {
                // @ts-ignore
                controls.target.copy(center);
                // @ts-ignore
                controls.update();
            }
        }

      } catch (err) {
        console.error("Failed to load STEP:", err);
      } finally {
        setLoading(false);
      }
    }
    loadModel();
  }, [partName, camera, controls]);

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
        <PerspectiveCamera makeDefault position={[200, 200, 200]} fov={45} />
        <OrbitControls makeDefault />
        
        <ambientLight intensity={1.5} />
        <pointLight position={[100, 100, 100]} intensity={2.5} castShadow />
        <spotLight position={[-100, 100, 100]} angle={0.15} penumbra={1} intensity={2.5} />
        
        <Suspense fallback={null}>
          <CADModel partName={partName} onFaceClick={onFaceClick} />
          <Environment preset="city" />
          <ContactShadows position={[0, -10, 0]} opacity={0.4} scale={50} blur={2} far={10} />
        </Suspense>
      </Canvas>
      
      <div className="absolute bottom-4 left-4 bg-slate-900/80 backdrop-blur border border-slate-700 p-2 rounded text-[10px] font-mono text-slate-400 uppercase tracking-wider">
        Renderer: WebGL / OCCT Engine
      </div>
    </div>
  );
};

export default CADViewer;
