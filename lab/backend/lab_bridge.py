from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import uvicorn
from pydantic import BaseModel
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
        return {"error": f"Resource path not found at {resource_path}"}
    
    parts = []
    for item in os.listdir(resource_path):
        full_path = os.path.join(resource_path, item)
        if os.path.isdir(full_path) and not item.startswith('.'):
            parts.append(item)
    return {"parts": parts}

@app.get("/resources/data/{part_name}/mesh")
async def get_mesh_data(part_name: str):
    resource_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Analysis Situs logs"))
    # Find the STEP file
    base_path = os.path.join(resource_path, part_name, part_name)
    step_file = None
    for ext in [".step", ".stp", ".STEP", ".STP"]:
        full_path = base_path + ext
        if os.path.exists(full_path):
            step_file = full_path
            break
            
    if not step_file:
        # Check for any .step file in directory
        dir_path = os.path.join(resource_path, part_name)
        if os.path.exists(dir_path):
            for f in os.listdir(dir_path):
                if f.lower().endswith((".step", ".stp")):
                    step_file = os.path.join(dir_path, f)
                    break
                    
    if not step_file:
        raise HTTPException(status_code=404, detail="STEP file not found")
        
    try:
        return processor.process_step_file(step_file)
    except Exception as e:
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
        raise HTTPException(status_code=404, detail=f"Data file not found at {file_path}")
        
    with open(file_path, "r") as f:
        return json.load(f)

# Serve static files from the 'static' directory
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    uvicorn.run("lab_bridge:app", host="0.0.0.0", port=8000, reload=True)
