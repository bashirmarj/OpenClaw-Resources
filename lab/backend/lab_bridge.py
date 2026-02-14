from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import uvicorn
import traceback
from typing import List, Optional
import json
import mimetypes
from geometry_processor import GeometryProcessor

# Fix for Windows wasm mime type
mimetypes.add_type('application/wasm', '.wasm')

app = FastAPI(title="Vectis Validation Lab Bridge")
processor = GeometryProcessor()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
@app.get("/status")
async def get_status():
    return {"status": "online", "mode": "watcher", "project": "Vectis Lab"}

@app.get("/resources/list")
async def list_resources():
    resource_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Analysis Situs logs"))
    if not os.path.exists(resource_path):
        print(f"ERROR: Resource path not found: {resource_path}")
        return {"error": "Resource path not found"}
    
    parts = []
    for item in os.listdir(resource_path):
        full_path = os.path.join(resource_path, item)
        if os.path.isdir(full_path) and not item.startswith('.'):
            parts.append(item)
    return {"parts": parts}

@app.get("/resources/data/{part_name}/mesh")
async def get_mesh_data(part_name: str):
    resource_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Analysis Situs logs"))
    part_folder = os.path.join(resource_path, part_name)
    
    if not os.path.exists(part_folder):
        raise HTTPException(status_code=404, detail=f"Part folder not found: {part_name}")
        
    # Find any .step or .stp file
    step_file = None
    for f in os.listdir(part_folder):
        if f.lower().endswith((".step", ".stp")):
            step_file = os.path.join(part_folder, f)
            break
            
    if not step_file:
        raise HTTPException(status_code=404, detail="No STEP file found in part folder")
        
    try:
        print(f"Processing: {step_file}")
        return processor.process_step_file(step_file)
    except Exception as e:
        print(f"CRASH in process_step_file: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/resources/data/{part_name}/{data_type}")
async def get_resource_data(part_name: str, data_type: str):
    file_map = {
        "holes": "holes.json",
        "blends": "blends.json",
        "contours": "contours.json"
    }
    
    if data_type not in file_map:
        raise HTTPException(status_code=400, detail="Invalid data type")
        
    resource_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Analysis Situs logs"))
    file_path = os.path.join(resource_path, part_name, file_map[data_type])
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Data file not found")
        
    with open(file_path, "r") as f:
        return json.load(f)

# Serve static files
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
