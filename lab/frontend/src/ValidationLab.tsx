import { useEffect, useState, Suspense } from 'react';
import { Layers, Activity, FileCode, CheckCircle2, AlertCircle, ChevronRight, Database } from 'lucide-react';
import CADViewer from './components/CADViewer';

const ValidationLab = () => {
  const [parts, setParts] = useState<string[]>([]);
  const [selectedPart, setSelectedPart] = useState<string | null>(null);
  const [status, setStatus] = useState<'loading' | 'online' | 'offline'>('loading');
  const [selectedFaceId, setSelectedFaceId] = useState<number | null>(null);

  useEffect(() => {
    const backendUrl = "";
    fetch(`${backendUrl}/status`)
      .then(res => res.json())
      .then(() => setStatus('online'))
      .catch(() => setStatus('offline'));

    fetch(`${backendUrl}/resources/list`)
      .then(res => res.json())
      .then(data => setParts(data.parts || []))
      .catch(console.error);
  }, []);

  return (
    <div className="flex h-screen w-screen flex-col bg-slate-950 text-slate-200 font-sans">
      {/* Header */}
      <header className="flex h-14 items-center justify-between border-b border-slate-800 px-6 bg-slate-900/50 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-1.5 rounded-lg">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <h1 className="font-bold tracking-tight text-lg">VECTIS <span className="text-blue-500">LAB</span></h1>
          <span className="text-xs bg-slate-800 px-2 py-0.5 rounded text-slate-400 font-mono">v1.0-alpha</span>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full ${status === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
              {status === 'online' ? 'Backend Live' : 'Backend Offline'}
            </span>
          </div>
        </div>
      </header>

      <main className="flex flex-1 overflow-hidden">
        {/* Sidebar: Parts List */}
        <aside className="w-64 border-r border-slate-800 bg-slate-900/30 overflow-y-auto">
          <div className="p-4 border-b border-slate-800 flex items-center gap-2">
            <Database className="w-4 h-4 text-blue-400" />
            <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Benchmark Corpus</h2>
          </div>
          <div className="py-2">
            {parts.map(part => (
              <button
                key={part}
                onClick={() => {
                  setSelectedPart(part);
                  setSelectedFaceId(null);
                }}
                className={`flex w-full items-center gap-3 px-4 py-3 text-sm transition-colors hover:bg-slate-800/50 ${
                  selectedPart === part ? 'bg-blue-600/10 text-blue-400 border-r-2 border-blue-500' : 'text-slate-400'
                }`}
              >
                <div className={`p-1 rounded ${selectedPart === part ? 'bg-blue-500/20' : 'bg-slate-800'}`}>
                  <FileCode className="w-3.5 h-3.5" />
                </div>
                <span className="truncate font-medium">{part}</span>
                <ChevronRight className={`ml-auto w-4 h-4 opacity-30 ${selectedPart === part ? 'opacity-100' : ''}`} />
              </button>
            ))}
          </div>
        </aside>

        {/* Main Viewport */}
        <section className="flex-1 flex flex-col relative">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-black pointer-events-none opacity-50" />
          
          {/* Viewport Toolbar */}
          <div className="h-12 border-b border-slate-800 flex items-center px-4 gap-4 bg-slate-900/20 z-10">
             <div className="flex bg-slate-800/50 rounded-md p-0.5">
                <button className="px-3 py-1 text-xs font-medium rounded bg-blue-600 text-white shadow-lg">3D Viewer</button>
                <button className="px-3 py-1 text-xs font-medium rounded text-slate-400 hover:text-slate-200">Topology Graph</button>
             </div>
             <div className="h-4 w-[1px] bg-slate-800" />
             <div className="flex gap-2">
                <button className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-all">
                   <Layers className="w-4 h-4" />
                </button>
             </div>
             {selectedFaceId !== null && (
               <div className="ml-auto text-[10px] font-mono bg-blue-500/20 text-blue-400 px-2 py-1 rounded border border-blue-500/30">
                 ACTIVE FACE: {selectedFaceId}
               </div>
             )}
          </div>

          <div className="flex-1 flex items-center justify-center relative z-0 p-8">
            {selectedPart ? (
              <Suspense fallback={<div className="text-slate-500 animate-pulse">Initializing CAD Engine...</div>}>
                <CADViewer partName={selectedPart} onFaceClick={(id) => setSelectedFaceId(id)} />
              </Suspense>
            ) : (
              <div className="text-center text-slate-600">
                <Layers className="w-12 h-12 mx-auto mb-4 opacity-20" />
                <p>Select a part from the sidebar to begin validation</p>
              </div>
            )}
          </div>
        </section>

        {/* Right Sidebar: Analysis Situs Comparison */}
        <aside className="w-80 border-l border-slate-800 bg-slate-900/50 backdrop-blur-sm overflow-y-auto">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Ground Truth (AS)</h2>
            <div className="flex gap-1">
               <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
               <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </div>
          </div>
          
          <div className="p-4 space-y-6">
            {!selectedPart ? (
               <div className="py-12 text-center text-slate-600 italic text-sm">No part selected</div>
            ) : (
              <>
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 font-medium">Feature Set</span>
                    <span className="text-emerald-400 bg-emerald-400/10 px-1.5 rounded">Verified</span>
                  </div>
                  <div className="bg-slate-800/40 rounded-lg p-3 border border-slate-800/60">
                    <div className="flex items-center gap-3 mb-3">
                       <div className="h-8 w-8 rounded-md bg-blue-500/10 flex items-center justify-center">
                          <CheckCircle2 className="w-4 h-4 text-blue-400" />
                       </div>
                       <div>
                          <div className="text-xs font-bold text-white uppercase">Holes</div>
                          <div className="text-[10px] text-slate-500 tracking-tighter uppercase font-mono">AS LOG LOADED</div>
                       </div>
                       <div className="ml-auto text-lg font-mono font-bold text-blue-400">--</div>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                       <div className="bg-blue-500 h-full w-[0%]" />
                    </div>
                  </div>
                </div>

                <div className="space-y-3 pt-4 border-t border-slate-800/50">
                   <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">Live Extraction Logs</h3>
                   <div className="space-y-2">
                      <div className="flex items-start gap-2 text-xs text-slate-400">
                         <AlertCircle className="w-3.5 h-3.5 mt-0.5 text-amber-500 shrink-0" />
                         <span className="font-mono">Waiting for geometry-service heartbeat...</span>
                      </div>
                   </div>
                </div>
              </>
            )}
          </div>
        </aside>
      </main>
    </div>
  );
};

export default ValidationLab;
