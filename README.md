# Fieldwork Room Planner 0.2

An offline, imperial-first equipment room planner. It combines a plan-first editor, editable architecture, service/working envelopes, height-aware validation, reusable libraries and assemblies, layout assistance, scenarios, and review exports.

## Run

**Windows package:** extract `Fieldwork-Windows.zip`, keep the complete folder together, and launch `Fieldwork/Fieldwork.exe`. No Python or Node installation is required. The planner opens in your default browser at **http://127.0.0.1:8765**. The optional `Install-Fieldwork.ps1` installs it for the current user and creates a Start menu shortcut. The package is unsigned.

**This workspace:** run `start.ps1` from this project folder. The launcher can use the dependencies installed for this task.

**Developer setup:** Python 3.12 and Node 24 are the tested environment:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
npm ci
npm run build
.venv\Scripts\python backend/run.py
```

The bundled app remains a local server when the browser closes. Stop it from **Workspace → Stop local app**, or close the source launcher. It binds only to loopback and uses session-token/host/origin checks for local mutation calls. Projects never upload to a cloud service.

## Plan and place

- **New blank project:** start an empty canvas with no room walls; draw your own outline or choose an optional rectangle/L-shaped preset; the previous complete design is backed up under Scenarios → Restore previous project.
- **Direct architecture:** drag walls, corners, doors and columns; click a wall dimension for an exact length. Click a wall and split it to form a jog. Attached objects follow their supporting wall.
- **Resize and rotate:** select one unlocked, ungrouped item and use its square resize handles or on-plan rotate control.
- **Equipment:** add generic or custom items, search favorites, reuse versioned definitions, and select objects in the schedule.
- **Room & references:** draw a polygon or hole, enter exact vertices, add/edit doors and obstructions, set elevations, reserve future areas, and import PDF/image/DXF references.
- **Direct dimensions:** select an item and click a green gap label or edit a measured gap in Properties. The item moves; its physical dimensions stay fixed.
- **Selection:** Shift-click adds items. Drag empty space to select several objects. Use the inspector to align, distribute, group, array, mirror, rotate, or lock. Assemblies retain relative offsets during group moves.
- **Precision:** type `3' 6 1/2"`, `42.5"`, or `3.5 ft`. Bare numbers mean inches. Enter/blur commits; Escape cancels. Changing display precision does not modify geometry.
- **Navigation:** wheel zooms around the pointer. Middle-button or Space drag pans. The hand tool provides an explicit alternative. Fit restores the complete room.

Shortcuts: V select; R rotate; L lock; M measure; F fit; Ctrl+D duplicate; Ctrl+G assembly; Ctrl+K command palette; Ctrl+Z undo; Ctrl+Shift+Z redo; Ctrl+S database revision. Rotate/measure/fit shortcuts can be remapped in Workspace. Arrow keys move 1 inch, Shift+Arrow 6 inches. Shift-drag locks the dominant axis; Alt-drag uses a fine 1/16 in. grid. Enter finishes an outline; Backspace removes its last corner.

## Reference drawings

Import an image or PDF (first page), pick two points of a known dimension, and enter the true imperial distance. Verify with a second independent known dimension. Adjust opacity/rotation and lock the reference before tracing.

DXF import requires explicit supported units and a closed straight-segment LWPOLYLINE room outline. The largest valid outline becomes the room. Interior closed polylines become conservative rectangular obstructions. Verify the result and add doors. Unsupported blocks, arcs, bulges and open lines are not automatically converted into walls.

## Clearances and height

The independent engine evaluates room containment, equipment interference, front working space, entered rear clearances, directional service/ventilation/removal/future/buffer zones, access-panel sweeps, room height, and user-defined regions. Zone sources and hard/soft intent are explicit. The section view shows projected elevations.

An optional planar corridor check evaluates connectivity at a user-entered width to a designated door. A separate replacement study checks a rectangular load and handling allowance using complete straight sweeps and conservative full-circle turns on a six-inch grid. These are bounded geometric studies, not comprehensive egress or handling certifications.

The NEC pack is **draft and unreviewed**. Generic/unknown manufacturer data stays unresolved. Code-specific egress triggers, dedicated-space classification and automatic opposing-condition inference remain explicitly unevaluated. Project edition/jurisdiction text records your basis; it does not silently install or approve a different rule table.

## Layout assistance

- **Repair selection:** hold unselected equipment fixed and search locally.
- **Improve arrangement:** return one improved candidate under the chosen objective.
- **Explore alternatives:** return distinct arrangements for comparison.

Locks, wall restrictions, assemblies, hard service envelopes and hard future reservations remain constraints. Compare a blue overlay before applying. Applying is one undoable action. Cancellation leaves the working design unchanged. Every accepted result is independently validated.

Candidate generation supports orthogonal walls. Diagonal room walls are valid boundaries but are not mounting candidate walls. The solver uses conservative 2D footprint exclusion and can reject valid vertically stacked placements. A sampled-domain failure or timeout does not prove the continuous physical problem is infeasible. Current limits: 20 items for solving and 100 for manual projects.

## Save, compare and issue

Browser autosave retains the working design; a prior autosave is available for recovery. Save named scenarios to compare room/equipment arrangements. The disk icon creates a local SQLite revision; Scenarios can browse/restore saved revisions. Download project JSON for a transferable backup including architecture, equipment, definitions and scenarios.

Export options: vector scaled **PDF** review plan/schedule/findings, inch-based **DXF**, **XLSX/CSV** schedules, **SVG/PNG** view images, and project/report/library JSON. Custom definitions are versioned; reviewed updates preview affected instances and preserve their placement.

Workspace controls include theme, text size, panel widths/visibility, snapping, navigation preset, imperial precision, keyboard mapping and clearance-layer visibility.

## Verify and build

```powershell
npm test
npm run build
$env:PYTHONPATH = 'backend'
.venv\Scripts\python -m pytest backend/tests -q
```

To build the offline executable, first build the frontend, install `requirements-desktop.txt`, then run `python scripts/build-windows.py`. Output is `release/Fieldwork/Fieldwork.exe` with its adjacent `_internal` runtime. Keep that runtime folder intact. Signing requires an organization-supplied certificate and is not part of this unsigned build.

See [the implemented-feature matrix](docs/IMPLEMENTED.md) for exact scope, limits and verification. The software regression suite and workstation tests do not substitute for engineering review or a clean-machine/site pilot.
