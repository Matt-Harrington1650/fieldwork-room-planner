"""Candidate-based CP-SAT. The independent validator is the final gate."""
import hashlib,json,time,platform,math,threading
from importlib.metadata import version
from ortools.sat.python import cp_model
from .geometry import dimensions, footprint, working_zone, rear_zone, valid_static,room_points,extra_zones
from .rules import validate, PACK, depth_requirement

def candidates(p,e,grid,mode='explore',deadline=None,cancel=None):
    if e.locked: return [e] if valid_static(p,e) else []
    # Working depth is never silently reduced to make a candidate fit.
    if depth_requirement(e) is not None and e.working < depth_requirement(e): return []
    w,h=p.room.width,p.room.depth
    n=p.room.notch
    # Stable wall IDs; two extra inward-facing segments of the L notch are included.
    walls=[('south',0,(0,0),(w,0)),('east',90,(w,0),(w,h-n)),
           ('north',180,(0,h),(w-n,h)),('west',270,(0,0),(0,h))]
    if n: walls += [('north',180,(w-n,h-n),(w,h-n)),('east',90,(w-n,h-n),(w-n,h))]
    if p.room.boundary:
        walls=[];points=room_points(p)
        area=sum(a[0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*a[1] for i,a in enumerate(points))
        if area<0:points=list(reversed(points))
        for a,b in zip(points,points[1:]+points[:1]):
            if abs(a[1]-b[1])<.001:
                wall='south' if b[0]>a[0] else 'north';walls.append((wall,0 if wall=='south' else 180,(min(a[0],b[0]),a[1]),(max(a[0],b[0]),a[1])))
            elif abs(a[0]-b[0])<.001:
                wall='east' if b[1]>a[1] else 'west';walls.append((wall,90 if wall=='east' else 270,(a[0],min(a[1],b[1])),(a[0],max(a[1],b[1]))))
    result=[];seen=set()
    if valid_static(p,e):result.append(e);seen.add((e.x,e.y,e.rotation))
    if mode=='repair':
        for dx in range(-8,9):
            for dy in range(-8,9):
                c=e.model_copy(update={'x':round(e.x+dx*grid,6),'y':round(e.y+dy*grid,6)})
                if valid_static(p,c):result.append(c)
        return sorted(result,key=lambda c:abs(c.x-e.x)+abs(c.y-e.y))[:100]
    for wall,rotation,start,end in walls:
        if e.wall not in ['any',wall]:continue
        rear=e.rear or 0
        candidate=e.model_copy(update={'rotation':rotation})
        bw,bh=dimensions(candidate)
        length=(end[0]-start[0]) if rotation%180==0 else (end[1]-start[1])
        span=bw if rotation%180==0 else bh
        # Enumerate whole wall deterministically, downsample only after static validation.
        options=[]
        for step in range(math.floor(max(0,length-span)/grid)+1):
            if (deadline and time.monotonic()>deadline) or (cancel and cancel.is_set()):break
            offset=round(step*grid,6)
            x,y=(start[0]+offset,start[1]+rear) if wall=='south' else ((start[0]-bw-rear,start[1]+offset) if wall=='east' else ((start[0]+offset,start[1]-bh-rear) if wall=='north' else (start[0]+rear,start[1]+offset)))
            c=candidate.model_copy(update={'x':x,'y':y})
            key=(x,y,rotation)
            if key not in seen and valid_static(p,c):options.append(c);seen.add(key)
        if len(options)>25:
            options=[options[round(i*(len(options)-1)/24)] for i in range(25)]
        result.extend(options)
    return result

def solve(p,settings,cancel=None):
    started=time.monotonic();deadline=started+settings.max_time_seconds
    canonical=json.dumps({'project':p.model_dump(),'settings':settings.model_dump()},sort_keys=True,separators=(',',':'))
    record={'input_hash':hashlib.sha256(canonical.encode()).hexdigest(),'rule_pack':PACK,
            'solver_version':version('ortools'),'python':platform.python_version(),
            'packages':{name:version(name) for name in ['shapely','ortools','fastapi','pydantic']},
            'seed':settings.random_seed,'worker_count':1,'settings':settings.model_dump()}
    if not p.room.defined:return {**record,'status':'NO_ROOM','layouts':[],'diagnostics':['Draw a room outline or choose a room shape before optimizing.'],'elapsed_ms':0}
    if len(p.equipment)>20: return {**record,'status':'LIMIT','layouts':[],'diagnostics':['Optimization supports up to 20 items in this release.'],'elapsed_ms':0}
    if not p.equipment: return {**record,'status':'EMPTY','layouts':[],'diagnostics':['Add equipment before optimizing.'],'elapsed_ms':0}
    if settings.mode=='repair':p=p.model_copy(update={'equipment':[e if e.id in settings.selected_ids else e.model_copy(update={'locked':True}) for e in p.equipment]})
    if cancel and cancel.is_set():return {**record,'status':'CANCELLED','layouts':[],'diagnostics':['Optimization cancelled.'],'elapsed_ms':0}
    domains=[candidates(p,e,settings.grid_mm,settings.mode,deadline,cancel) for e in p.equipment]
    if (cancel and cancel.is_set()) or time.monotonic()>deadline:return {**record,'status':'CANCELLED' if cancel and cancel.is_set() else 'TIME_LIMIT','layouts':[],'diagnostics':['Search stopped during candidate generation; no geometric infeasibility is proven.'],'elapsed_ms':round((time.monotonic()-started)*1000)}
    groups={}
    for i,e in enumerate(p.equipment):
        if e.group:groups.setdefault(e.group,[]).append(i)
    for members in groups.values():
        if len(members)<2:continue
        lead=members[0];origin=p.equipment[lead];joint=[]
        for c in domains[lead]:
            if c.rotation!=origin.rotation:continue
            batch=[p.equipment[i].model_copy(update={'x':p.equipment[i].x+c.x-origin.x,'y':p.equipment[i].y+c.y-origin.y}) for i in members]
            if all(valid_static(p,e) and (not p.equipment[i].locked or (e.x==p.equipment[i].x and e.y==p.equipment[i].y)) for i,e in zip(members,batch)):joint.append(batch)
        for k,i in enumerate(members):domains[i]=[batch[k] for batch in joint]
    exhausted=[f'{e.id}: no legal candidates after architecture, working depth, locks and wall restrictions.' for e,d in zip(p.equipment,domains) if not d]
    if exhausted: return {**record,'status':'INFEASIBLE','layouts':[],'diagnostics':exhausted,'elapsed_ms':round((time.monotonic()-started)*1000)}
    model=cp_model.CpModel(); choices=[];xs=[];ys=[]
    for i,domain in enumerate(domains):
        row=[]
        for j,c in enumerate(domain):
            use=model.new_bool_var(f'use_{i}_{j}');row.append(use)
            w,h=dimensions(c)
            xs.append(model.new_optional_fixed_size_interval_var(math.floor(c.x),math.ceil(c.x+w)-math.floor(c.x),use,f'x_{i}_{j}'))
            ys.append(model.new_optional_fixed_size_interval_var(math.floor(c.y),math.ceil(c.y+h)-math.floor(c.y),use,f'y_{i}_{j}'))
        model.add_exactly_one(row);choices.append(row)
    model.add_no_overlap_2d(xs,ys)
    for members in groups.values():
        for i in members[1:]:
            for j in range(len(domains[i])):model.add(choices[i][j]==choices[members[0]][j])
    # CP uses cached rectangular bounds; Shapely independently validates final geometry.
    cached=[[(footprint(c).bounds,working_zone(c).bounds,rear_zone(c).bounds if rear_zone(c) is not None else None) for c in d] for d in domains]
    def hits(a,b):
        return a is not None and b is not None and a[0]<b[2]-.001 and a[2]>b[0]+.001 and a[1]<b[3]-.001 and a[3]>b[1]+.001
    for i in range(len(domains)):
        for j in range(i+1,len(domains)):
            # Bounding filters reduce exact-geometry calls. All incompatible pairs remain forbidden.
            for a,ca in enumerate(domains[i]):
                for b,cb in enumerate(domains[j]):
                    if abs(ca.x-cb.x)>ca.width+ca.depth+cb.width+cb.depth+ca.working+cb.working+(ca.rear or 0)+(cb.rear or 0):continue
                    fa,za,ra=cached[i][a];fb,zb,rb=cached[j][b]
                    extra_conflict=any(poly.intersects(footprint(cb)) and poly.intersection(footprint(cb)).area>.01 for _,poly in extra_zones(ca)) or any(poly.intersects(footprint(ca)) and poly.intersection(footprint(ca)).area>.01 for _,poly in extra_zones(cb))
                    if hits(fa,fb) or hits(za,fb) or hits(zb,fa) or hits(ra,fb) or hits(rb,fa) or extra_conflict:
                        model.add(choices[i][a]+choices[j][b]<=1)
                if (cancel and cancel.is_set()) or time.monotonic()>deadline:
                    return {**record,'status':'CANCELLED' if cancel and cancel.is_set() else 'TIME_LIMIT','layouts':[],'diagnostics':['Search stopped while building candidate conflicts. Current design is unchanged; no geometric infeasibility is proven.'],'elapsed_ms':round((time.monotonic()-started)*1000)}
    # Objective: minimize displacement from current design; integer Manhattan distance.
    def objective(e,c):
        moved=abs(c.x-e.x)+abs(c.y-e.y)+(0 if c.rotation==e.rotation else 200)
        if settings.objective=='preserve':return moved
        # Maximize nearest physical-neighbor distance as a transparent access proxy.
        separation=min((footprint(c).distance(footprint(o)) for o in p.equipment if o.id!=e.id),default=0)
        future=sum(footprint(c).intersection(__import__('shapely').geometry.box(r.x,r.y,r.x+r.width,r.y+r.depth)).area for r in p.regions if r.kind=='future')
        return moved*(.2 if settings.objective=='access' else .5)-separation*.3+future/1000
    costs=[[objective(e,c) for c in domain] for e,domain in zip(p.equipment,domains)]
    model.minimize(sum(round(costs[i][j]*1000)*lit for i,row in enumerate(choices) for j,lit in enumerate(row)))
    layouts=[];status='UNKNOWN'
    for run in range(settings.return_limit):
        remaining=deadline-time.monotonic()
        if remaining<=0: break
        engine=cp_model.CpSolver();engine.parameters.max_time_in_seconds=remaining/(settings.return_limit-run)
        engine.parameters.num_search_workers=1;engine.parameters.random_seed=settings.random_seed
        monitor=threading.Thread(target=lambda: (cancel.wait(remaining),engine.stop_search()) if cancel else None,daemon=True)
        if cancel:monitor.start()
        result=engine.solve(model);status=engine.status_name(result)
        if result not in (cp_model.FEASIBLE,cp_model.OPTIMAL):break
        selected=[next(j for j,lit in enumerate(row) if engine.boolean_value(lit)) for row in choices]
        equipment=[domain[j] for domain,j in zip(domains,selected)]
        candidate=p.model_copy(update={'equipment':equipment})
        report=validate(candidate)
        if not any(f['severity']=='error' for f in report['diagnostics']):
            displacement=sum(costs[i][j] for i,j in enumerate(selected))
            score=round(min(100,max(0,100-100*displacement/(len(equipment)*(p.room.width+p.room.depth)))),1)
            layouts.append({'id':f'layout-{run+1}','score':score,'equipment':[e.model_dump() for e in equipment],
                            'diagnostics':report['diagnostics'],'metrics':{'displacement_mm':displacement,'score_basis':'100 minus normalized Manhattan displacement and rotation penalty'}})
        # Exclude whole neighborhoods: at least one movable item must move >=500 mm or rotate.
        far=[]
        for i,(domain,idx) in enumerate(zip(domains,selected)):
            old=domain[idx]
            if old.locked:continue
            far.extend(choices[i][j] for j,c in enumerate(domain) if c.rotation!=old.rotation or abs(c.x-old.x)+abs(c.y-old.y)>=500)
        if not far or settings.mode!='explore' or (cancel and cancel.is_set()):break
        model.add(sum(far)>=1)
    return {**record,'status':'FEASIBLE' if layouts else status,'layouts':layouts,
            'diagnostics':[] if layouts else ['No validated solution found within candidate domains and time budget. This does not prove the continuous placement problem is infeasible.'],
            'candidate_counts':{e.id:len(d) for e,d in zip(p.equipment,domains)},'elapsed_ms':round((time.monotonic()-started)*1000)}
