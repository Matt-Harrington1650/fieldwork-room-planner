"""Offline vector review sheets and imperial schedules."""
import io,math,textwrap
from datetime import datetime,timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape,letter
from reportlab.lib.colors import HexColor
from openpyxl import Workbook
from openpyxl.styles import Font,PatternFill,Alignment
from .geometry import room_points,footprint,working_zone,rear_zone,obstacles,extra_zones,door_sweep
from .rules import validate,PACK
from .exporters import imperial_length,export_report

def export_pdf(p):
    output=io.BytesIO();c=canvas.Canvas(output,pagesize=landscape(letter));c.setTitle(p.name+' - Fieldwork review');W,H=landscape(letter)
    def header(title):
        c.setFillColor(HexColor('#285f49'));c.rect(0,H-65,W,65,fill=1,stroke=0);c.setFillColorRGB(1,1,1);c.setFont('Helvetica-Bold',19);c.drawString(30,H-32,'FIELDWORK');c.setFont('Helvetica',10);c.drawString(30,H-50,title[:110])
    def footer(page):
        c.setFillColor(HexColor('#788a70'));c.setFont('Helvetica',8);c.drawString(30,20,'DRAFT - Implemented checks only. Engineering and manufacturer-source review required.');c.drawRightString(W-30,20,f'{PACK} | {page}')
    header(p.name);availableW=W-110;availableH=H-200
    denominator=next((d for d in [12,24,48,96,192,384] if (p.room.width+900)*72/(25.4*d)<availableW and (p.room.depth+900)*72/(25.4*d)<availableH),768)
    scale=72/(25.4*denominator);ox=(W-p.room.width*scale)/2;oy=105
    def poly(g,color,fill=False,dashed=False):
        if g.is_empty:return
        if g.geom_type=='MultiPolygon':
            for part in g.geoms:poly(part,color,fill,dashed)
            return
        if not hasattr(g,'exterior'):return
        c.setStrokeColor(HexColor(color));c.setFillColor(HexColor(color));c.setLineWidth(.7);c.setDash(3,2) if dashed else c.setDash()
        path=c.beginPath();pts=list(g.exterior.coords);path.moveTo(ox+pts[0][0]*scale,oy+pts[0][1]*scale)
        for x,y in pts[1:]:path.lineTo(ox+x*scale,oy+y*scale)
        path.close();c.drawPath(path,stroke=1,fill=int(fill));c.setDash()
    from shapely.geometry import Polygon,box
    poly(Polygon(room_points(p)),'#354f41')
    for hole in p.room.holes:poly(Polygon(hole),'#9aa88e',True)
    for e in p.equipment:
        poly(working_zone(e),'#9fb58b',False,True)
        if rear_zone(e) is not None:poly(rear_zone(e),'#8aa3bd',False,True)
        for z,g in extra_zones(e,False):poly(g,'#ad97bd',False,True)
    for oid,o in obstacles(p):poly(o,'#acb49c',False)
    colors={'panelboard':'#8db4c9','switchboard':'#8bad97','transformer':'#d1b17d','ats':'#b3a5c8'}
    for e in p.equipment:
        g=footprint(e);poly(g,colors.get(e.category,'#9bb7ad'),True);center=g.centroid;c.setFillColor(HexColor('#233b2f'));c.setFont('Helvetica-Bold',max(5,min(9,e.width*scale/max(len(e.id)*.6,1))));c.drawCentredString(ox+center.x*scale,oy+center.y*scale,e.id)
    c.setFillColor(HexColor('#3a5b46'));c.setFont('Helvetica',9);c.drawCentredString(W/2,oy+p.room.depth*scale+18,imperial_length(p.room.width));c.saveState();c.translate(ox-22,oy+p.room.depth*scale/2);c.rotate(90);c.drawCentredString(0,0,imperial_length(p.room.depth));c.restoreState()
    c.setFont('Helvetica',9);c.drawString(30,67,f'SCALE: 1:{denominator} at 100% print | Dimensions: feet and inches | Area: {(Polygon(room_points(p),p.room.holes).area/304.8**2):.1f} sq ft')
    c.drawString(30,51,'Solid: equipment / architecture. Dashed: working and service envelopes. Physical unit: inches.');footer(1);c.showPage()
    header('Equipment schedule - '+p.name);y=H-95;c.setFillColor(HexColor('#273e31'));columns=[30,100,260,390,490,600]
    for x,label in zip(columns,['TAG','TYPE','W x D x H','FRONT','REAR','DATA / SOURCE']):c.setFont('Helvetica-Bold',8);c.drawString(x,y,label)
    y-=23;page=2
    for e in p.equipment:
        if y<60:footer(page);c.showPage();page+=1;header('Equipment schedule (continued)');y=H-90
        values=[e.id,e.name[:28],f'{e.width/25.4:.2f} x {e.depth/25.4:.2f} x {e.height/25.4:.2f} in',imperial_length(e.working),'Unknown' if e.rear is None else imperial_length(e.rear),(e.status+' / '+e.source)[:30]]
        for x,value in zip(columns,values):c.setFont('Helvetica',8);c.drawString(x,y,str(value))
        c.setStrokeColor(HexColor('#dde6d5'));c.line(30,y-7,W-30,y-7);y-=26
    footer(page);c.showPage();page+=1;header('Validation, sources and unresolved coverage');y=H-90
    for f in export_report(p)['validation']['diagnostics']:
        text=f"{f['status'].upper()} | {', '.join(f['equipment_ids']) or 'PROJECT'} | {f['rule_id']}: {f['message']}"
        for line in textwrap.wrap(text,140):
            if y<55:footer(page);c.showPage();page+=1;header('Validation (continued)');y=H-90
            c.setFillColor(HexColor('#a55d47' if f['severity']=='error' else '#6e785e'));c.setFont('Helvetica',8);c.drawString(30,y,line);y-=13
        y-=8
    for line in textwrap.wrap('PROJECT NOTES: '+p.notes+' | JURISDICTION: '+p.jurisdiction,140):
        if y<55:footer(page);c.showPage();page+=1;header('Project notes');y=H-90
        c.setFillColor(HexColor('#4a5d40'));c.drawString(30,y,line);y-=13
    footer(page);c.save();return output.getvalue()

def export_xlsx(p):
    wb=Workbook();ws=wb.active;ws.title='Equipment (inches)';ws.append(['Tag','Category','Name','X (in)','Y (in)','Width (in)','Depth (in)','Height (in)','Bottom (in)','Front (in)','Rear (in)','Rotation','Locked','Assembly','Confidence','Manufacturer','Model','Source'])
    for e in p.equipment:ws.append([e.id,e.category,e.name,e.x/25.4,e.y/25.4,e.width/25.4,e.depth/25.4,e.height/25.4,e.bottom/25.4,e.working/25.4,None if e.rear is None else e.rear/25.4,e.rotation,e.locked,e.group,e.status,e.manufacturer,e.model,e.source])
    checks=wb.create_sheet('Validation');checks.append(['Rule','Status','Severity','Equipment','Finding'])
    for f in export_report(p)['validation']['diagnostics']:checks.append([f['rule_id'],f['status'],f['severity'],', '.join(f['equipment_ids']),f['message']])
    for sheet in wb:
        sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
        for cell in sheet[1]:cell.fill=PatternFill('solid',fgColor='285F49');cell.font=Font(color='FFFFFF',bold=True)
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                if isinstance(cell.value,str) and cell.value.startswith(('=','+','-','@')):cell.value="'"+cell.value
                if isinstance(cell.value,float):cell.number_format='0.0000'
        for col in sheet.columns:sheet.column_dimensions[col[0].column_letter].width=min(80,max(14,max(len(str(c.value or '')) for c in col)+2))
    output=io.BytesIO();wb.save(output);return output.getvalue()
