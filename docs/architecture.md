# Architecture decisions and release status

## ADR-001 — Canonical geometry
Accepted. Persist full-precision Cartesian millimeters with +Y up. Equipment x/y is the lower-left corner of the rotated axis-aligned footprint. Rotation 0 faces +Y, 90 faces -X, 180 faces -Y, 270 faces +X. World-to-screen inversion is applied once in the SVG group, labels are counter-inverted. The entire interface uses imperial feet/inches with fractional inputs; area uses square feet. Canonical world coordinates stay millimeters. Input preserves fractional-inch precision instead of rounding to integer millimeters. Unchanged blur never quantizes existing geometry to the rounded display. CP optional intervals use conservative whole-millimeter enclosing bounds and exact final Shapely validation. Shapely geometry uses full floating-point millimeters, positive-area intersection tolerance 0.01 mm², and containment buffer 0.001 mm.

## ADR-002 — Domain/solver separation
Accepted. `models.py` owns input contracts, `geometry.py` owns exact polygons, `rules.py` owns independent validation, and `solver.py` builds candidates/CP constraints. API routes call these services. Every candidate solution is reconstructed and independently validated before being returned. Solver pair constraints are cached axis-aligned bounds for speed and are not the authority for acceptance.

## ADR-003 — Rule packs
Accepted for MVP. Rule identity `nec-2023-draft@0.1.0` and explicit review/unimplemented status accompany reports. Front clearance derives from a draft table only for validation of a user-selected condition. Generic dimensions and unknown rear access are warnings. No rule has licensed-source/engineering approval. Gate to production: licensed-source review, equipment-specific provenance, applicability inputs, required compliant/noncompliant/boundary/ambiguous fixtures with named engineer review, and access/egress/overhead rules.

## ADR-004 — Candidate CP-SAT
Accepted. Four wall-facing orientations, imperial ½/1/2/4-inch grid discretization, max 25 sampled candidates per physical wall segment. Wall assignments, locks, architecture and known rear offsets are hard conditions. Exactly-one literals, optional intervals and NoOverlap2D enforce placement; pair constraints block physical equipment in another item's working/rear space. Working zones may overlap each other. The objective preserves the current design. Alternative diversity uses a 500 mm/rotation neighborhood exclusion. Candidate domain exhaustion is reported by equipment ID. Coupled conflicts without a solution receive a limited, honest diagnostic, not a claim that the room is too small.

## ADR-005 — Persistence/reproducibility
Accepted. Portable compact JSON schema v1.0.0 and browser autosave are the interactive workflow. SQLite API revision records include a parent ID, SHA-256 canonical input hash and UTC timestamp. Solves store canonical input/settings hash, exact runtime package versions, seed, one worker, settings and results. The save icon commits a database revision; editor autosave targets local storage. Schema is intentionally compact and not yet an implementation of the complete target interchange model.

## ADR-006 — Desktop packaging
Implemented as an offline PyInstaller one-folder Windows application serving bundled React assets in the default browser. The local engine, native geometry/solver libraries, PDF renderer and export dependencies are included. An optional per-user PowerShell installer copies the package and adds a Start menu shortcut. The executable passed native health, validation, optimization, export/import and replacement-study checks. It is unsigned; this is not a Tauri/MSI/NSIS distribution. A signing certificate and clean-machine/site pilot remain release gates.

## Module map
- `apps/web/src/domain.ts`: compact browser model, immediate preliminary checks, vector export.
- `apps/web/src/ProApp.tsx`: command/history state, manual editor, API, scenarios, libraries and alternatives. `PlanCanvas.tsx`, `Inspector.tsx`, `RoomPanel.tsx` and `Fields.tsx` own the principal views. `main.tsx` provides recovery rendering.
- `backend/app/models.py`: strict Pydantic types and architectural input checks.
- `backend/app/geometry.py`: Shapely rectangles/polygons and envelope semantics.
- `backend/app/rules.py`: structured rule findings and explicit unresolved coverage.
- `backend/app/solver.py`: wall candidates, CP-SAT, independent final gate and scoring.
- `backend/app/persistence.py`: SQLite revisions/solve records.
- `backend/app/exporters.py`: inch-based DXF layers.
- `backend/app/main.py`: loopback API, host/origin/token checks, static frontend.

## API shape
GET `/api/v1/health`, `/session`, `/rulepacks`; POST `/validate` takes a Project; POST `/solve` takes `{project, settings}`; POST `/projects` creates a revision; GET/PUT `/projects/{id}` loads/saves; POST `/export/dxf` returns DXF; POST `/export/report` returns project+diagnostics JSON. OpenAPI definitions are available at `/docs` while running. JSON schemas are generated from the same Pydantic types used at the API boundary.

## Catalog and rule authoring
Catalog records are generic sizes in `domain.ts`; no real manufacturer applicability is implied. Add a type by adding its definition, semantic orientation and color. Production records must add source document/revision/model applicability and independently reviewed installation envelopes. Add engineering rules only in `rules.py`/geometry services, with matching browser preview where appropriate and regression cases in `backend/tests`. Never add a hard solver-only engineering rule. Keep unimplemented checks visible until they have reviewed fixtures.

## Release gates still open
- Responsible-engineer review of source applicability, licensed adopted code and manufacturer data.
- Code-specific egress triggers, dedicated-space classification and automatic opposing-condition inference.
- Clean-machine installer acceptance and representative real-room performance/usability pilot.
- Signing certificate and signed enterprise distribution, if required.

See `IMPLEMENTED.md` for the current feature-by-feature scope and conservative algorithm limits.
