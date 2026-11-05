"""Versioned, millimeter-based domain. No solver or HTTP dependencies."""
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class Zone(BaseModel):
    id: str
    kind: Literal['service','ventilation','removal','future','buffer']
    side: Literal['front','rear','left','right','top','bottom']
    distance: float = Field(ge=0,le=20000)
    hard: bool = True
    source: str = ''
    bottom: float = 0
    top: float = 10000

class Door(BaseModel):
    id: str
    x: float
    y: float
    width: float = Field(gt=0,le=10000)
    angle: float = 0
    sweep: float = Field(default=90,ge=-180,le=180)
    egress: bool = True

class Obstacle(BaseModel):
    id: str
    kind: str = 'column'
    x: float
    y: float
    width: float = Field(gt=0,le=50000)
    depth: float = Field(gt=0,le=50000)
    bottom: float = Field(default=0,ge=0)
    top: float = Field(default=10000,gt=0)

class Equipment(BaseModel):
    id: str = Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    category: Literal['switchboard','switchgear','panelboard','transformer','ats','ups','disconnect','custom']
    name: str = Field(max_length=200)
    x: float = Field(ge=-100000, le=100000)
    y: float = Field(ge=-100000, le=100000)
    width: float = Field(gt=0, le=20000)
    depth: float = Field(gt=0, le=20000)
    rotation: Literal[0,90,180,270] = 0
    locked: bool = False
    working: float = Field(default=1000, ge=0, le=10000)
    rear: float | None = Field(default=None, ge=0, le=10000)
    voltage: int = Field(default=120, ge=0, le=100000)
    condition: Literal[1,2,3] = 1
    status: Literal['generic','user_entered','unknown','verified'] = 'generic'
    wall: Literal['any','north','east','south','west'] = 'any'
    height: float = Field(default=2133.6,gt=0,le=20000)
    bottom: float = Field(default=0,ge=0,le=20000)
    zones: list[Zone] = Field(default_factory=list,max_length=30)
    group: str = ''
    definition: str = ''
    source: str = ''
    manufacturer: str = ''
    model: str = ''
    panelSwing: float = Field(default=0,ge=0,le=180)

class Room(BaseModel):
    defined: bool = True
    width: float = Field(ge=610, le=50000)
    depth: float = Field(ge=610, le=50000)
    notch: float = Field(default=0, ge=0, le=10000)
    door: float = Field(default=1100, ge=600, le=2000)
    column: bool = True
    height: float = Field(default=3048,gt=0,le=30000)
    boundary: list[tuple[float,float]] | None = Field(default=None,max_length=200)
    holes: list[list[tuple[float,float]]] = Field(default_factory=list,max_length=50)
    doors: list[Door] | None = Field(default=None,max_length=50)
    obstacles: list[Obstacle] | None = Field(default=None,max_length=100)
    access_width: float = Field(default=914.4,gt=0,le=5000)
    check_access: bool = False

    @model_validator(mode='after')
    def valid_architecture(self):
        if self.notch >= min(self.width, self.depth):
            raise ValueError('Notch must be smaller than both room dimensions.')
        if self.doors is None and self.width < 3300 + self.door:
            raise ValueError('The fixed door opening must lie within the south wall (X 3300).')
        if self.obstacles is None and self.column and (self.width < 4000 or self.depth < 3050):
            raise ValueError('The fixed column must lie within the room.')
        if self.boundary is not None:
            from shapely.geometry import Polygon
            polygon=Polygon(self.boundary,self.holes)
            if not polygon.is_valid or polygon.area<=0:raise ValueError('Room boundary must be a simple polygon with valid interior holes.')
            if any(not (0<=x<=self.width and 0<=y<=self.depth) for x,y in self.boundary):raise ValueError('Room vertices must remain inside the room extents.')
        if any(o.top<=o.bottom for o in self.obstacles or []):raise ValueError('Obstacle top must be above its bottom.')
        return self

class Region(BaseModel):
    id:str
    name:str = ''
    x:float
    y:float
    width:float=Field(gt=0)
    depth:float=Field(gt=0)
    kind:Literal['forbidden','future','required']
    hard:bool=True

class Project(BaseModel):
    schema_version: Literal['1.0.0'] = '1.0.0'
    name: str = Field(max_length=200)
    units: Literal['mm','ft'] = 'ft'
    room: Room
    equipment: list[Equipment] = Field(max_length=100)
    regions:list[Region] = Field(default_factory=list,max_length=100)
    scenarios:list[dict] = Field(default_factory=list,max_length=50)
    definitions:list[dict] = Field(default_factory=list,max_length=200)
    underlay:dict|None=None
    notes:str=''
    jurisdiction:str=''
    ruleEdition:str='2023'

    @model_validator(mode='after')
    def unique_ids(self):
        ids = [e.id for e in self.equipment]
        if len(set(ids)) != len(ids):
            raise ValueError('Equipment IDs must be unique.')
        return self

class Settings(BaseModel):
    grid_mm: Literal[10,25,50,100,12.7,25.4,50.8,101.6] = 101.6
    max_time_seconds: int = Field(default=10, ge=1, le=30)
    random_seed: int = Field(default=481516, ge=0, le=2147483647)
    return_limit: int = Field(default=3, ge=1, le=3)
    mode:Literal['explore','improve','repair']='explore'
    selected_ids:list[str]=Field(default_factory=list)
    objective:Literal['preserve','access','future','balanced']='preserve'
    job_id:str=''

class SolveRequest(BaseModel):
    project: Project
    settings: Settings = Field(default_factory=Settings)
