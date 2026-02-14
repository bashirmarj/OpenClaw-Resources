from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import uvicorn
from pydantic import BaseModel
from typing import List, Optional
import json

app = FastAPI(title="Vectis Validation Lab Bridge")

# Serve Frontend
app.mount("/lab", StaticFiles(directory="static", html=True), name="lab")

@app.get("/")
async def redirect_to_lab():
    return FileResponse("static/index.html")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status")
async def get_status():
    return {"status": "online", "mode": "watcher", "project": "Vectis Lab"}

@app.get("/resources/list")
async def list_resources():
    resource_path = "../../Analysis Situs logs"
    if not os.path.exists(resource_path):
        return {"error": "Resource path not found"}
    
    parts = []
    for item in os.listdir(resource_path):
        full_path = os.path.join(resource_path, item)
        if os.path.isdir(full_path):
            parts.append(item)
    return {"parts": parts}

@app.get("/resources/data/{part_name}/{data_type}")
async def get_resource_data(part_name: str, data_type: str):
    # data_type can be 'holes', 'blends', 'step_path', etc.
    file_map = {
        "holes": "holes.json",
        "blends": "blends.json",
        "contours": "contours.json"
    }
    
    if data_type not in file_map:
        raise HTTPException(status_code=400, detail="Invalid data type")
        
    file_path = f"../../Analysis Situs logs/{part_name}/{file_map[data_type]}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Data file not found")
        
    with open(file_path, "r") as f:
        return json.load(f)

@app.get("/resources/file/{part_name}/step")
async def get_step_file(part_name: str):
    # Try different common step extensions
    base_path = f"../../Analysis Situs logs/{part_name}/{part_name}"
    for ext in [".step", ".stp", ".STEP", ".STP"]:
        full_path = base_path + ext
        if os.path.exists(full_path):
            from fastapi.responses import FileResponse
            return FileResponse(full_path)
    
    # Fallback: check all files in directory for any .step/.stp
    dir_path = f"../data/resources/Analysis Situs logs/{part_name}"
    if os.path.exists(dir_path):
        for f in os.listdir(dir_path):
            if f.lower().endswith((".step", ".stp")):
                from fastapi.responses import FileResponse
                return FileResponse(os.path.join(dir_path, f))
                
    raise HTTPException(status_code=404, detail="STEP file not found")

if __name__ == "__main__":
    uvicorn.run("lab_bridge:app", host="0.0.0.0", port=8000, reload=True)
