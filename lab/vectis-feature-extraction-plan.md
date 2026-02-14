# Vectis Machining - Feature Extraction Technical Plan
**Version 1.0** | Date: 2026-02-10 | Prepared by: Neo 🚀

---

## Executive Summary

**Current State:** Feature extraction accuracy is failing across all attempted methods (hard-coded algorithms, BRepNet ML, AAGNet, geometric heuristics).

**Root Cause:** All previous approaches were built before modern LLMs with vision capabilities existed. They're either too simple (rule-based) or too specialized (require specific training data).

**Proposed Solution:** Hybrid AI-augmented geometric analysis leveraging 2026 AI capabilities (Claude Sonnet 4, GPT-4 Vision) combined with solid OpenCascade B-Rep topology analysis.

**Expected Outcome:** 80-90% accuracy, processing time <2 minutes, modular architecture with graceful fallbacks.

---

## Technical Architecture

### Phase 1: Enhanced Geometric Foundation (Build on What Works)
**Goal:** Extract clean, reliable B-Rep topology + surface data

**What to Keep:**
- OpenCascade STEP parsing (working)
- Tessellation pipeline (working)
- Volume/surface area calculation (working)
- Part classification (prismatic/turning/hybrid) (working)

**What to Enhance:**
1. **Topology Graph Construction**
   - Extract full face adjacency graph
   - Build edge-loop relationships
   - Compute face normals, curvature, surface types
   - **Output:** JSON graph with nodes (faces) and edges (adjacencies)

2. **Surface Classification Enhancement**
   - Current: Plane, Cylinder, Cone, Sphere, Torus
   - Add: B-spline surface characterization (degree, control points)
   - Add: Surface orientation relative to principal axes
   - Add: Boundary curve analysis (open/closed loops)

3. **Dimensional Extraction**
   - For each cylindrical face: extract axis, radius, height
   - For each planar face: extract normal vector, area, bounding rectangle
   - For each edge: extract type (line, arc, spline), length
   - **Output:** Structured dimensional data per face/edge

**Implementation:**
- Extend existing `brep_feature_extractor.py` (already has most infrastructure)
- Create `enhanced_topology_extractor.py` for graph + dimensions
- Keep it modular — this becomes input for both geometric and AI analysis

---

### Phase 2: Rule-Based Feature Recognition (Fast Path)
**Goal:** Handle 60-70% of common features with deterministic rules

**Approach:** Multi-level heuristic cascade

**Level 1: Simple Features (High Confidence)**
```python
# Hole Detection (Geometric Rules)
def detect_simple_hole(topology_graph, face_data):
    """
    Criteria:
    - Single cylindrical face OR cylinder + 2 planar caps
    - Cylinder axis perpendicular to stock face (Z-axis typically)
    - Depth-to-diameter ratio > 0.5
    - No adjacent cylindrical faces with different radii (counterbore handled separately)
    """
    # Implementation: Traverse topology, check surface types, measure dimensions
    # Confidence: 95% for simple through-holes, 85% for blind holes
```

**Level 2: Compound Features (Medium Confidence)**
```python
# Pocket Detection
def detect_pocket(topology_graph, volume_decomposition):
    """
    Criteria:
    - Primarily planar bottom face
    - Vertical or near-vertical walls (planes or cylinders)
    - Enclosed boundary (closed edge loops)
    - Volume removed from stock
    """
    # Use existing volume_decomposer.py + lump_classifier.py as foundation
    # Add edge-loop closure detection
    # Confidence: 80% for rectangular pockets, 70% for complex shapes
```

**Level 3: Pattern Features (Lower Confidence)**
```python
# Fillet/Chamfer Detection
def detect_blend_features(topology_graph, face_data):
    """
    Criteria:
    - Small blend surfaces (cylinder, torus, cone)
    - Adjacent to two primary faces (plane-plane or plane-cylinder)
    - Radius/angle within typical machining ranges
    """
    # Leverage existing aag_pattern_engine/fillet_chamfer_recognizer.py
    # Confidence: 75% (fillets often ambiguous)
```

**Coverage Estimate:** 
- Simple prismatic parts: 85% features detected
- Complex parts: 60% features detected
- Turning parts: 70% features detected (leverage existing geometric_fallback.py)

**Output Format:**
```json
{
  "feature_id": "hole_001",
  "type": "hole",
  "subtype": "simple_through_hole",
  "confidence": 0.95,
  "method": "geometric_rules",
  "dimensions": {
    "diameter": 10.0,
    "depth": 25.0,
    "axis": [0, 0, 1],
    "position": [50, 50, 0]
  },
  "affected_faces": [12, 13, 14],
  "machining_time_estimate": "2.5min"
}
```

---

### Phase 3: AI-Augmented Recognition (The Game Changer)
**Goal:** Handle the remaining 30-40% of ambiguous/complex features

**Key Insight:** Modern LLMs can interpret engineering drawings and 3D views in ways rule-based systems can't.

**Input Preparation:**
1. **Multi-View Rendering** (Three.js from existing mesh)
   - Orthographic: Front, Top, Right, Isometric
   - Render resolution: 1024x1024
   - Apply edge highlighting for feature boundaries
   - Annotate with dimension callouts (arrow + text)

2. **B-Rep Data Serialization**
   - Convert topology graph to text format
   - Include surface types, adjacencies, dimensions
   - Example:
     ```
     Face 12: Cylinder, radius=5mm, axis=Z, adjacent to [Face 13 (Plane), Face 14 (Plane)]
     Face 13: Plane, normal=[0,0,-1], area=314mm², bottom cap
     ```

3. **Feature Candidates from Phase 2**
   - Include low-confidence detections from geometric rules
   - Provide context: "Possible pocket or slot at position X,Y,Z"

**AI Prompt Engineering:**
```
You are an expert CNC machining engineer analyzing a CAD part for cost estimation.

PART DATA:
- Type: Prismatic
- Material: Aluminum 6061
- Bounding box: 100mm x 80mm x 50mm

B-REP TOPOLOGY:
[face_data_text]

GEOMETRIC ANALYSIS (Phase 2 Results):
- Detected: 3 holes (confidence: 0.95, 0.88, 0.92)
- Detected: 1 pocket (confidence: 0.65) ← LOW CONFIDENCE, REVIEW NEEDED
- Detected: 2 fillets (confidence: 0.70, 0.75)
- Unclassified faces: [Face 23, Face 24, Face 25] ← NEED CLASSIFICATION

IMAGES: [Attach 4 orthographic views]

TASK:
1. Verify the low-confidence features (pocket, fillets)
2. Classify unclassified face groups (Face 23-25)
3. Identify any missed features visible in the views
4. For each feature, provide:
   - Type (hole, pocket, slot, step, boss, chamfer, fillet, thread, counterbore, etc.)
   - Dimensions (depth, diameter, width, etc.)
   - Machining approach (drill, end mill, face mill, etc.)
   - Confidence (0.0-1.0)

OUTPUT FORMAT: JSON array of features
```

**Expected AI Response:**
```json
[
  {
    "feature_id": "ai_001",
    "type": "pocket",
    "verification": "CONFIRMED",
    "original_confidence": 0.65,
    "ai_confidence": 0.92,
    "reasoning": "Rectangular depression with rounded corners (R3mm fillet). Clear planar bottom, vertical walls visible in front view.",
    "dimensions": {
      "length": 40.0,
      "width": 25.0,
      "depth": 15.0,
      "corner_radius": 3.0
    }
  },
  {
    "feature_id": "ai_002",
    "type": "slot",
    "verification": "NEW_DETECTION",
    "ai_confidence": 0.88,
    "reasoning": "Faces 23-25 form an elongated channel along X-axis. Not detected by geometric rules because end caps have curved profiles.",
    "dimensions": {
      "length": 60.0,
      "width": 10.0,
      "depth": 20.0
    }
  }
]
```

**Integration Strategy:**
1. Run Phase 2 (geometric rules) first → fast, deterministic
2. Identify low-confidence features + unclassified face groups
3. If confidence threshold met (>90% features above 0.85 confidence) → DONE, skip AI
4. Otherwise → trigger AI analysis for ambiguous cases only
5. Merge results: geometric (high conf) + AI-verified (medium conf) + AI-detected (new)

**Cost Control:**
- Only invoke AI for complex parts (>50 faces) or low geometric confidence
- Single API call per part (batch all questions)
- Estimated cost: $0.02-0.05 per part (Claude Sonnet 4 with vision)
- Simple parts: $0 AI cost (geometric rules sufficient)

---

### Phase 4: Feature Tree Construction
**Goal:** Build SolidWorks-style hierarchical feature tree

**Hierarchy Rules:**
1. **Base Feature** (stock material)
   - Type: `extrusion` or `revolve`
   - Dimensions: bounding box

2. **Primary Features** (major material removal)
   - Pockets, slots, steps, bosses
   - Parent: Base Feature

3. **Secondary Features** (refined machining)
   - Holes, countersinks, counterbores, threads
   - Parent: Primary feature they're attached to (if applicable) or Base

4. **Finishing Features** (surface treatments)
   - Fillets, chamfers
   - Parent: Edges they modify

**Parent-Child Detection:**
- If Feature B's volume is fully contained in Feature A's affected volume → B is child of A
- If Feature B is on the boundary/edge of Feature A → B modifies A
- Example: Hole in pocket wall → Hole is child of Pocket

**Tree JSON Output:**
```json
{
  "root": {
    "id": "base_001",
    "type": "stock",
    "dimensions": {"length": 100, "width": 80, "height": 50},
    "children": [
      {
        "id": "pocket_001",
        "type": "pocket",
        "dimensions": {...},
        "children": [
          {
            "id": "hole_001",
            "type": "hole",
            "dimensions": {...},
            "children": []
          },
          {
            "id": "fillet_001",
            "type": "fillet",
            "radius": 3.0,
            "children": []
          }
        ]
      },
      {
        "id": "hole_002",
        "type": "hole",
        "dimensions": {...},
        "children": []
      }
    ]
  }
}
```

**Visualization Component:**
- Reuse existing Three.js viewer
- Add feature tree panel (react component)
- Click feature in tree → highlight affected faces in 3D view
- Use `face_mapping` from tessellation to map features to mesh triangles

---

### Phase 5: Validation & Feedback Loop
**Goal:** Continuous accuracy improvement

**Manual Review Interface:**
1. Display feature tree + 3D view side-by-side
2. For each feature, show:
   - Type, dimensions, confidence
   - Method (geometric/AI/hybrid)
   - Affected faces (highlighted in 3D)
3. User actions:
   - ✅ Confirm (correct)
   - ✏️ Edit (wrong dimensions but right type)
   - ❌ Delete (false positive)
   - ➕ Add missing feature (false negative)

**Feedback Data Collection:**
- Log user corrections to Supabase
- Track accuracy by part type, feature type, method
- Build ground truth dataset

**Improvement Strategy:**
- Week 1-2: Collect 50-100 validated parts
- Week 3: Analyze common failure modes
- Week 4: Tune geometric rule thresholds, refine AI prompts
- Month 2: Consider training custom ML model on ground truth (optional)

---

## Implementation Roadmap

### Sprint 1 (Week 1): Enhanced Topology Extraction
**Goal:** Build solid geometric foundation

**Tasks:**
1. Create `enhanced_topology_extractor.py`
   - Face adjacency graph
   - Surface classification with dimensions
   - Edge-loop analysis
2. Integrate into `app.py`
3. Add `/analyze-v2` endpoint with enhanced data
4. Test with 5-10 sample STEP files

**Deliverables:**
- Working endpoint returning rich topology JSON
- Unit tests for topology extraction
- Sample output files for review

---

### Sprint 2 (Week 2): Rule-Based Recognition
**Goal:** Implement deterministic feature detection

**Tasks:**
1. Refactor existing `lump_classifier.py` into modular recognizers:
   - `hole_recognizer.py`
   - `pocket_recognizer.py`
   - `slot_recognizer.py`
   - `fillet_recognizer.py` (leverage existing AAG)
2. Implement confidence scoring
3. Add feature tree builder
4. Test on 20 parts (simple prismatic)

**Deliverables:**
- Modular recognizer modules
- Feature tree JSON output
- Accuracy report on test set

**Expected Accuracy at This Stage:** 60-70% on complex parts, 85% on simple parts

---

### Sprint 3 (Week 3): AI Integration
**Goal:** Add AI-augmented recognition

**Tasks:**
1. Implement multi-view renderer (Three.js screenshots)
2. Build AI prompt generator
3. Integrate Claude Sonnet 4 API (or GPT-4 Vision as fallback)
4. Implement hybrid merging logic (geometric + AI)
5. Add cost tracking (API calls)

**Deliverables:**
- Working AI analysis pipeline
- Hybrid feature recognition endpoint
- Cost monitoring dashboard

**Expected Accuracy:** 80-90% on all part types

---

### Sprint 4 (Week 4): UI Integration & Validation
**Goal:** Build review interface, test with real users

**Tasks:**
1. Build feature tree React component
2. Integrate 3D viewer highlighting
3. Implement manual review UI
4. Connect feedback loop to Supabase
5. Deploy to staging

**Deliverables:**
- Full-stack feature extraction + review system
- User testing with 5 beta customers
- Initial accuracy metrics

---

## Risk Mitigation

### Risk 1: AI API Costs Spiral
**Mitigation:**
- Implement strict gating: only invoke AI when geometric confidence <0.85
- Cache AI responses by file hash
- Set monthly budget cap with alerts
- Fallback to geometric-only mode if budget exceeded

### Risk 2: AI Hallucinations (False Positives)
**Mitigation:**
- Always run geometric rules first (ground truth)
- AI can only VERIFY or ADD, never override high-confidence geometric detections
- Implement sanity checks (feature dimensions must fit within bounding box, etc.)
- Log all AI responses for review

### Risk 3: Processing Time Exceeds User Tolerance
**Mitigation:**
- Run async with progress updates
- Optimize geometric phase (<15 seconds)
- Only invoke AI for complex parts (adds 20-40 seconds)
- Total: <60 seconds for 90% of parts

### Risk 4: Integration with Existing Codebase Breaks
**Mitigation:**
- Build new endpoints (`/analyze-v3`) alongside existing ones
- Keep `SKIP_FEATURE_RECOGNITION` flag for rollback
- Gradual rollout: 10% → 50% → 100% traffic
- Feature flag per customer for A/B testing

---

## Success Metrics

### Technical Metrics
- **Precision:** % of detected features that are correct (target: >85%)
- **Recall:** % of actual features that are detected (target: >80%)
- **Processing Time:** Average time per part (target: <90 seconds)
- **AI Invocation Rate:** % of parts requiring AI (target: <40%)
- **Cost Per Part:** AI API cost (target: <$0.05 average)

### Business Metrics
- **Manual Review Time:** Hours spent correcting features (target: <20% reduction)
- **Quote Accuracy:** % of quotes within 10% of actual cost (target: >75%)
- **Customer Satisfaction:** User rating of feature detection (target: >4.0/5.0)

---

## Cost Estimate

### Development Time
- Sprint 1: 40 hours (topology extraction)
- Sprint 2: 60 hours (rule-based recognition)
- Sprint 3: 50 hours (AI integration)
- Sprint 4: 40 hours (UI + testing)
- **Total:** 190 hours

### Infrastructure Costs (Monthly)
- Render.com (geometry-service): $10
- Claude API (1000 parts/month @ $0.03 avg): $30
- Supabase (existing): $0
- **Total:** $40/month

### ROI Calculation
- Current: 2 hours manual review per 10 parts = 12 minutes per part
- With system: 3 minutes review per part (80% reduction)
- Time saved: 9 minutes per part
- At 100 parts/month: 15 hours saved
- At $50/hour: **$750/month value** vs $40/month cost = **18x ROI**

---

## Alternative Approaches (Considered & Rejected)

### Option A: Commercial CAD API (Onshape, Fusion 360)
**Pros:** High accuracy (95%+), proven
**Cons:** $500-2000/month, vendor lock-in, API rate limits
**Verdict:** Too expensive for startup phase

### Option B: Train Custom ML Model (BRepNet-style)
**Pros:** Potentially highest accuracy with enough data
**Cons:** Requires 10,000+ labeled parts, months of training, GPU infrastructure
**Verdict:** Not feasible without significant funding

### Option C: Pure AI (no geometric rules)
**Pros:** Simplest implementation
**Cons:** Higher cost per part ($0.10+), slower, less reliable, no explainability
**Verdict:** Hybrid approach is better

---

## Open Questions (For OBash to Answer)

1. **Priority:** Do we optimize for accuracy or speed first?
   - My recommendation: Accuracy (you said >1 minute is acceptable)

2. **AI Provider:** Claude Sonnet 4 vs GPT-4 Vision?
   - My recommendation: Claude (better at technical reasoning, slightly cheaper)

3. **Rollout Strategy:** Big bang or gradual?
   - My recommendation: Gradual (10% → 50% → 100% over 2 weeks)

4. **Feedback Loop:** Mandatory review or optional?
   - My recommendation: Optional but incentivized (show accuracy improvement over time)

5. **ML Future:** If we collect 1000+ validated parts, train custom model?
   - My recommendation: Revisit in 6 months after hybrid system proven

---

## Conclusion

**This is NOT incremental improvement.** This is a fundamental architecture shift from:
- Pure rule-based (60% accuracy) 
- Pure ML-based (70% accuracy, high complexity)
→ **Hybrid AI-augmented (85% accuracy, manageable complexity)**

**The key innovation:** Using 2026 AI capabilities that didn't exist when you tried BRepNet/AAGNet. Modern LLMs can reason about 3D geometry from drawings + text descriptions in ways that would have required custom-trained models 6 months ago.

**Timeline:** 4-6 weeks to production-ready system
**Cost:** $40/month operating, ~$10K development (at $50/hour freelance rate)
**Expected Outcome:** 80-90% accuracy, <90 second processing, $0.03/part cost

Ready to start? I recommend beginning with Sprint 1 (topology extraction) this week.
