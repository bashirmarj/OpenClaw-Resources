import { useEffect, useState, Suspense } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment, ContactShadows } from '@react-three/drei';
import * as THREE from 'three';

interface CADModelProps {
  partName: string;
  onFaceClick?: (faceId: number) => void;
}

const CADModel = ({ partName, onFaceClick }: CADModelProps) => {
  const [group, setGroup] = useState<THREE.Group | null>(null);
  const [loading, setLoading] = useState(true);
  const { camera, controls } = useThree();

  useEffect(() => {
    async function loadModel() {
      setGroup(null);
      setLoading(true);
      try {
        const response = await fetch(`/resources/file/${partName}/step`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const buffer = await response.arrayBuffer();
        const uint8Array = new Uint8Array(buffer);
        
        // @ts-ignore
        const initFn = window.occtimportjs || window.occtImportJs;
        if (!initFn) throw new Error("OCCT library not found.");

        const occt = await initFn();
        // High precision params
        const result = occt.ReadStepFile(uint8Array, {
            linear_deflection: 0.05,
            angular_deflection: 0.5
        });
        
        if (!result || !result.success) throw new Error("OCCT failed to parse.");

        const modelGroup = new THREE.Group();
        const fullBounds = new THREE.Box3();
        
        result.meshes.forEach((meshData: any) => {
          const geometry = new THREE.BufferGeometry();
          geometry.setAttribute('position', new THREE.Float32BufferAttribute(meshData.attributes.position.array, 3));
          
          if (meshData.attributes.normal) {
            geometry.setAttribute('normal', new THREE.Float32BufferAttribute(meshData.attributes.normal.array, 3));
          } else {
            geometry.computeVertexNormals();
          }
          
          if (meshData.attributes.index) {
            geometry.setIndex(new THREE.Uint32BufferAttribute(meshData.attributes.index.array, 1));
          }
          
          // Matte CAD Material
          const material = new THREE.MeshStandardMaterial({ 
            color: 0xf1f5f9,
            metalness: 0.2,
            roughness: 0.7,
            side: THREE.DoubleSide
          });
          
          const mesh = new THREE.Mesh(geometry, material);
          mesh.userData = { faceId: meshData.face_index }; 
          
          // Add wireframe edges for definition
          const edges = new THREE.EdgesGeometry(geometry, 25);
          const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x334155, linewidth: 1 }));
          
          mesh.add(line);
          modelGroup.add(mesh);
          
          geometry.computeBoundingBox();
          if (geometry.boundingBox) fullBounds.expandByPoint(geometry.boundingBox.min).expandByPoint(geometry.boundingBox.max);
        });
        
        setGroup(modelGroup);

        // Centering and Zoom
        if (!fullBounds.isEmpty()) {
            const center = new THREE.Vector3();
            fullBounds.getCenter(center);
            const size = new THREE.Vector3();
            fullBounds.getSize(size);
            const maxDim = Math.max(size.x, size.y, size.z);
            
            // Move model to origin
            modelGroup.position.x = -center.x;
            modelGroup.position.y = -center.y;
            modelGroup.position.z = -center.z;

            const fov = (camera as THREE.PerspectiveCamera).fov * (Math.PI / 180);
            let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
            cameraZ *= 2.0; 

            camera.position.set(cameraZ, cameraZ, cameraZ);
            camera.lookAt(0, 0, 0);
            if (controls) {
                // @ts-ignore
                controls.target.set(0, 0, 0);
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

  if (loading || !group) return null;

  return <primitive object={group} />;
};

const CADViewer = ({ partName, onFaceClick }: { partName: string, onFaceClick?: (id: number) => void }) => {
  return (
    <div className="w-full h-full bg-slate-950 rounded-xl overflow-hidden border border-slate-800 shadow-2xl relative">
      <Canvas shadows gl={{ antialias: true, logarithmicDepthBuffer: true }}>
        <PerspectiveCamera makeDefault position={[200, 200, 200]} fov={45} />
        <OrbitControls makeDefault />
        
        <ambientLight intensity={1.0} />
        <directionalLight position={[100, 100, 100]} intensity={2} castShadow />
        <directionalLight position={[-100, -100, 100]} intensity={1} />
        
        <Suspense fallback={null}>
          <CADModel partName={partName} onFaceClick={onFaceClick} />
          <Environment preset="studio" />
          <ContactShadows position={[0, -50, 0]} opacity={0.3} scale={100} blur={2.5} far={20} />
        </Suspense>
      </Canvas>
      
      <div className="absolute bottom-4 left-4 bg-slate-900/80 backdrop-blur border border-slate-700 p-2 rounded text-[10px] font-mono text-slate-400 uppercase tracking-wider">
        Renderer: WebGL / High-Def OCCT
      </div>
    </div>
  );
};

export default CADViewer;
