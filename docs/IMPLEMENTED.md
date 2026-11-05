# Fieldwork 0.2 implementation status

This release implements the practical planner workflows from the research plan. It remains an engineering planning tool with a draft electrical rule pack, not a universal code-compliance determination.

| Area | Implemented behavior | Validation |
|---|---|---|
| Imperial | Feet/inches, fractions, decimal inches, square feet, configurable display precision; full-precision canonical geometry | Parser, unchanged-blur, serialization and unit export tests |
| Editing | Multi-selection, marquee, direct editable measured gaps, relative move, axis lock, face/center snaps, arrays, align/distribute, mirror, rotation, overlap cycling | React interaction regressions and pure geometry tests; live browser gap and assembly checks |
| History | Atomic complete actions, undo/redo, Escape/cancel, previous autosave recovery; autosave skips in-progress drags | Drag, cancellation, repeated undo/redo regressions |
| Architecture | Polygon boundary/holes, exact vertex coordinates, rectangles/L shapes, multiple editable doors and obstructions, pads/overhead elevations | Polygon validity, hole, sector-sweep, elevation tests |
| References | Local images and first PDF page, opacity, rotation, two-point calibration and independent scale verification | Native PDF import and raster rendering checked |
| DXF import | Explicit drawing units, largest closed straight LWPOLYLINE as boundary; interior polylines conservatively bounded as obstructions | Inch round-trip and room-extents tests |
| Equipment | Custom items, ratings, dimensions, front/rear/side/top/bottom envelopes, access-panel swing, elevations, provenance | Directional zone and height-aware fixtures |
| Libraries | Favorites, versioned definitions, import/export tool sets, explicit reviewed instance updates; placed items retain geometry until accepted | Project definition serialization; UI implementation |
| Lineups | Assemblies keep relative offsets on move/rotation/solver translation; lock guards prevent partially moving a locked assembly | Rigid assembly solve fixture and browser multi-selection check |
| Clearance review | Independent Shapely containment/interference, working space, known manufacturer envelopes, required/forbidden/future regions, room height; coverage grouped once | Backend regression fixtures and structured findings |
| Access | Optional user-width conservative planar corridor connectivity to designated doors | Connected/blocked route fixtures |
| Replacement | Separate rectangular rigid-load study, user load size/handling allowance; exact straight-move sweeps and conservative full-circle turns on a 6-inch grid | Native executable study and automated route fixture |
| Layout assistance | Repair selection, improve arrangement, explore distinct alternatives; locks, wall restrictions, reservations, rigid assembly translation; cancellation and time budget | Deterministic, locked, repair, cancellation and diversity tests |
| Comparison | Movement overlay, alternative positions/moved counts, named room/equipment scenarios | Live scenario save and restoration; portable project persistence |
| Workspace | Collapsible/width-configurable panels, light/dark, text size, layer controls, imperial precision, snap increment, CAD/simple navigation, remappable rotate/measure/fit keys, command palette | Persisted local preferences; live browser inspection |
| Review outputs | Vector scaled PDF plan, equipment schedule and validation pages; XLSX/CSV schedules; inch DXF; SVG/PNG view exports; project/report/library JSON | PDF rendered and visually inspected; native export/import smoke tests |
| Windows | Bundled offline executable and per-user PowerShell installer; local server lifecycle and stop action | Executable-level API smoke test with no Python/Node used by the application |

## Explicit limits

- The electrical rule pack is a draft. Adopted edition/jurisdiction, source applicability and manufacturer values require responsible-engineer review. Project text fields do not silently select a different implemented code table.
- Code-specific large-equipment egress triggers and dedicated overhead-space classification are not implemented. Opposing-condition inference remains a user responsibility. These are shown as unresolved coverage, not passed checks.
- Access connectivity is a conservative 2D user-width model, not a complete code-specific egress analysis. It does not establish overhead clearance along the route or travel-distance compliance.
- Replacement analysis handles a rigid rectangle, straight translations and full-circle turns. It does not model articulated loads, lifting gear, stairs, vertical handling, or flexible/simultaneous curved maneuvers. A failed sampled search is unresolved, not proof of impossibility. Door openings must be explicitly verified; leaf operation is outside this route study.
- Manual validation is height-aware. CP-SAT placement still uses conservative 2D footprint exclusion, which can exclude otherwise valid vertically stacked arrangements. Wall candidate generation supports orthogonal wall segments; diagonal boundary segments are valid architecture but are not mounting candidate walls.
- The optimizer's access objective uses a physical-neighbor separation proxy; it is not an optimal aisle-width/egress certificate. Scores are preferences within the implemented model, not engineering quality grades.
- Current solver limit: 20 equipment items. Larger manual projects can contain up to 100 items. Results are sampled candidates and may be time-limited.
- PDF underlay imports the first page. DXF import does not infer architectural intent from arbitrary blocks, arcs, bulges or open lines. Text and complex entities are not automatically traced. DWG is unsupported.
- The Windows package is unsigned; no certificate was provided. It is a portable executable plus an optional PowerShell installer, not a signed MSI/NSIS/Tauri shell. Clean-machine validation beyond this Windows workstation remains a release gate.
- Named scenarios retain room/equipment/notes. Library sources and project-level rule settings stay with the project; underlay and preferences are shared across scenarios. Workspace preferences remain personal browser state.

## Verification record

- 92 backend tests passed, including polygon rooms, holes, true door sectors, height bands, service zones, assemblies, local repair, corridor connectivity, replacement studies, PDF/underlay rendering, DXF units, XLSX and cancellation.
- 55 frontend/domain/React interaction tests passed. The drag crash regression remains covered.
- TypeScript type check and production frontend build passed.
- Native Fieldwork.exe: health/session, independent validation, CP-SAT with 3 alternatives, PDF/XLSX/DXF/JSON export, PDF import, DXF import and replacement study passed.
- The three-page sample PDF was rendered and visually reviewed for clipping, label readability, schedule alignment and report coverage.

The application does not claim that these software tests constitute engineer approval or a representative-site performance acceptance.

## Starting a new design

Choose **New blank project**, name the room, then choose **Start blank project**. The canvas starts with no room, walls, dimensions, equipment, doors, obstructions, references, or scenarios. Choose **Draw my room** to click a custom outline. **Rectangle** and **L-shaped room** remain optional presets. Incomplete projects retain their no-room state in browser autosave, JSON and database revisions. Checks, optimization and plan exports wait for a defined room. Your saved equipment definitions remain available. **Scenarios → Restore previous project** restores the complete design saved immediately before the most recent new project, even after subsequent edits. This backup is held in this browser; export important projects for a separate file copy.

Walls and corners now drag directly on the plan. Walls have screen-sized hit areas and clickable imperial dimensions. Attached equipment, complete assemblies and doors follow supporting walls; conflicting or locked attachments reject the edit. Split walls can be dragged into jogs. Doors slide along valid wall openings; obstructions drag; single unlocked, ungrouped equipment has rotation-aware resize handles and an on-plan rotate control. The camera remains fixed during dragging. Geometry and interaction checks cover invalid shapes, holes, origin translation, locks, assemblies, cancellation, undo and repeated pointer events. The live Windows app was checked with a wall drag, exact dimension entry, and Undo; the original design was restored.

The empty-canvas update passed 92 backend and 55 frontend checks, including custom outline creation, both presets, cancellation, Undo, legacy-room migration, database roundtrip, and export gating. Narrow screens show the drawing canvas before the side panels.
