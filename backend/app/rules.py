"""Draft rule pack. Engineering review is explicitly outstanding.

Working depth is contextual USER-SELECTED condition, not inferred from a catalog.
No universal compliance claim is generated. Shared working zones may overlap.
"""
from .geometry import footprint, working_zone, rear_zone, room_polygon, obstacles, overlap, extra_zones, height_overlap,zone_elevation
PACK = 'nec-2023-draft@0.1.0'
UNIMPLEMENTED = ['Code-specific large-equipment egress applicability','Dedicated overhead space classification',
                 'Automatic opposing-condition inference','Replacement route not included in ordinary layout validation; run the separate rigid-load study']

def depth_requirement(e):
    if e.voltage <= 150: return 914
    if e.voltage <= 600: return [914,1067,1219][e.condition-1]
    return None

def validate(p):
    if not p.room.defined:
        return {'rule_pack':PACK,'status':'room_not_defined','diagnostics':[dict(rule_id='ROOM-NOT-DRAWN',status='unresolved',severity='warning',equipment_ids=[],message='Draw a room outline or choose a room shape before checking clearances.')],'unimplemented':UNIMPLEMENTED}
    findings=[]; room=room_polygon(p)
    def add(rule,ids,message,severity='error',required=None,actual=None):
        findings.append(dict(rule_id=rule,status='fail' if severity=='error' else 'unresolved',severity=severity,
                             equipment_ids=ids,message=message,required=required,actual=actual,
                             source={'standard':'NFPA 70' if rule.startswith('NEC') else 'Project geometry',
                                     'edition':'2023' if rule.startswith('NEC') else None,'review_status':'unreviewed'}))
    for e in p.equipment:
        f,z=footprint(e),working_zone(e)
        if not room.buffer(.001).covers(f): add('GEO-CONTAINMENT',[e.id],'Equipment footprint extends outside the room.')
        if not room.buffer(.001).covers(z): add('SPACE-CONTAINMENT',[e.id],'Working space extends outside the room.')
        for oid,o in obstacles(p,e):
            if overlap(f,o) or overlap(z,o): add('GEO-OBSTACLE',[e.id],f'Footprint or working space obstructed by {oid}.')
        rear=rear_zone(e)
        if rear is not None and (not room.buffer(.001).covers(rear) or any(overlap(rear,o) for _,o in obstacles(p,e))):
            add('MFR-REAR',[e.id],'Manufacturer rear clearance obstructed by architecture.')
        for other in p.equipment:
            if e.id == other.id: continue
            if e.id < other.id and height_overlap(e,other) and overlap(f,footprint(other)): add('GEO-COLLISION',[e.id,other.id],'Equipment footprints overlap at the same elevation.')
            if other.bottom<e.bottom+max(e.height,1981.2) and other.bottom+other.height>e.bottom and overlap(z,footprint(other)): add('NEC2023-110.26-A2',[e.id,other.id],'Working space is obstructed by equipment.')
            if rear is not None and height_overlap(e,other) and overlap(rear,footprint(other)): add('MFR-REAR',[e.id,other.id],'Manufacturer rear clearance is obstructed.')
        if e.bottom+e.height>p.room.height:add('HEIGHT-ROOM',[e.id],'Equipment top exceeds the room height.',required={'top_mm':p.room.height},actual={'top_mm':e.bottom+e.height})
        for record,poly in extra_zones(e,False):
            kind=record.kind if record else 'panel_swing';hard=record.hard if record else True
            low,high=zone_elevation(e,record);probe=e.model_copy(update={'bottom':low,'height':high-low})
            blocked=high>p.room.height or low<0 or not room.buffer(.001).covers(poly) or any(overlap(poly,o) for _,o in obstacles(p,probe)) or any(other.id!=e.id and low<other.bottom+other.height and high>other.bottom and overlap(poly,footprint(other)) for other in p.equipment)
            if blocked:add('ZONE-'+kind.upper(),[e.id],f'{kind.replace("_"," ").title()} envelope is obstructed.','error' if hard else 'warning')
            if record and not record.source:add('ZONE-SOURCE',[e.id],f'{kind.title()} zone has no source reference.','warning')
        for region in p.regions:
            if region.kind=='required':
                from shapely.geometry import box
                if not box(region.x,region.y,region.x+region.width,region.y+region.depth).covers(f):add('REGION-REQUIRED',[e.id],f'Footprint is outside required region {region.name or region.id}.','error' if region.hard else 'warning')
        required=depth_requirement(e)
        if required is None: add('NEC-VOLTAGE-UNSUPPORTED',[e.id],'Voltage exceeds draft rule-pack scope.','warning')
        elif e.working < required: add('NEC2023-110.26-A1',[e.id],f'Working depth {e.working} mm is less than draft minimum {required} mm for selected condition {e.condition}.',required={'depth_mm':required},actual={'depth_mm':e.working})
        if e.rear is None: add('MFR-REAR-UNKNOWN',[e.id],'Manufacturer rear service requirement is unknown.','warning')
        if e.status != 'verified': add('DATA-PROVENANCE',[e.id],'Generic or user-entered equipment dimensions require source review.','warning')
        if e.status=='verified' and not e.source:add('DATA-SOURCE-MISSING',[e.id],'Verified status has no attached source reference. Source verification remains unresolved.','warning')
    add('RULEPACK-REVIEW',[],'Draft NEC values and selected opposing conditions require licensed-source engineering review.','warning')
    for missing in UNIMPLEMENTED: add('NOT-IMPLEMENTED',[],f'Not evaluated: {missing}.','warning')
    if p.room.check_access:
        from .access import check_access
        findings.extend(check_access(p))
    return {'rule_pack':PACK,'diagnostics':findings,'status':'failed_implemented_checks' if any(f['severity']=='error' for f in findings) else 'passed_implemented_checks_with_unresolved_items','unimplemented':UNIMPLEMENTED}
