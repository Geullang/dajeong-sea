"""Individual original *interpretive* watercolor-and-ink travel sketches; no photographs.
Each image is seeded by the full place name and category and independently rendered.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import hashlib, random, math, io
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
SERIF='/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'

def file_for(name):
 return hashlib.sha256(name.encode('utf-8')).hexdigest()[:17]+'.jpg'

def render(name, category, width=720, height=440):
 seed=int(hashlib.sha256((name+'/'+category).encode()).hexdigest()[:14],16)
 rng=random.Random(seed)
 W,H=width,height
 # Painted paper; high-frequency rice-paper wash and pigmented color blooms
 np_rng=np.random.default_rng(seed)
 y=np.linspace(0,1,H)[:,None,None];x=np.linspace(0,1,W)[None,:,None]
 paper=np.array([253,248,235],float).reshape(1,1,3)
 grain=np_rng.normal(0,2.4,(H,W,1))
 vignette=5*np.sqrt(((x-.5)/.8)**2+((y-.5)/.8)**2)
 a=np.uint8(np.clip(paper+grain-vignette,0,255)).repeat(1,0)
 img=Image.fromarray(a,'RGB').convert('RGBA')
 wash=Image.new('RGBA',(W,H));wa=ImageDraw.Draw(wash,'RGBA')
 palettes=[[(150,190,196),(105,158,176),(220,188,149)],[(135,181,195),(180,203,191),(229,170,153)],[(151,176,192),(215,196,167),(181,190,149)],[(168,194,194),(120,169,183),(229,198,166)],[(155,183,198),(210,178,144),(173,191,157)]]
 colors=palettes[seed%len(palettes)]
 for _ in range(115):
  cx=rng.randint(-40,W+40);cy=rng.randint(-35,H+30);rx=rng.randint(25,150);ry=rng.randint(15,95)
  rr,gg,bb=colors[rng.randrange(3)]
  wa.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),fill=(rr,gg,bb,rng.randint(18,49)))
 wash=wash.filter(ImageFilter.GaussianBlur(19));img=Image.alpha_composite(img,wash)
 d=ImageDraw.Draw(img,'RGBA');ink=(65,78,83,195);thin=(87,98,95,120)
 horizon=rng.randint(int(H*.56),int(H*.68))
 # mountain and sea: background unique per composition
 is_coast=category=='자연·풍경' or any(s in name for s in ['해변','바다','청사포','영도','해운대','미포','수변','광안','등대','요트','다릿돌','노을','동백','태종','송정'])
 if is_coast:
  poly=[(0,horizon-23)];lx=0
  for k in range(8):
   lx=int(W*k/7);poly.append((lx,horizon-rng.randint(15,85)))
  poly.extend([(W,horizon),(0,horizon)])
  d.polygon(poly,fill=(129,157,174,35))
  for u in range(4):
   yy=horizon+15+u*23
   d.line([(0,yy+rng.randint(1,5)),(W,yy+rng.randint(-3,3))],fill=(79,142,167,44),width=2)
  for k in range(35):
   xx=rng.randrange(W);yy=rng.randint(horizon,H-70)
   d.arc((xx,yy,xx+rng.randint(8,44),yy+4),180,340,fill=(45,119,153,rng.randint(20,65)),width=1)
 else:
  for i in range(12):
   bx=i*68+rng.randint(-22,15);bh=rng.randint(75,180)
   d.rectangle((bx,horizon-bh,bx+rng.randint(25,65),horizon),fill=(135,167,166,12),outline=(87,109,105,27),width=1)
  d.polygon([(0,horizon),(W,horizon),(W,H),(0,H)],fill=(206,177,146,20))
  for k in range(5):
   yy=horizon+15+k*37
   d.line((0,yy,W,yy),fill=(151,148,130,25),width=2)
 # composition: independent details based on category, place full-name and seeded architecture
 scene=Image.new('RGBA',(W,H));p=ImageDraw.Draw(scene,'RGBA')
 variant=(seed//19)%13
 cx=int(W*(.32+rng.random()*.35));cy=horizon-15
 def line(points,width=3,color=ink):p.line(points,fill=color,width=width,joint='curve')
 def box(x0,y0,x1,y1,fill,outline=ink,width=2):p.rounded_rectangle((x0,y0,x1,y1),radius=3,fill=fill,outline=outline,width=width)
 def ellipse(bb,fill,outline=thin,width=2):p.ellipse(bb,fill=fill,outline=outline,width=width)
 def leafy(px,py,k=5):
  line([(px,py),(px+rng.randint(-10,10),py-80)],2,(77,98,79,125))
  for j in range(k):
   xx=px+rng.randint(-33,33); yy=py-rng.randint(28,100)
   ellipse((xx-13,yy-6,xx+13,yy+6),(101+rng.randrange(40),147+rng.randrange(45),110,63),(73,98,81,78),1)
 if category in ('독립서점','소품샵') or any(s in name for s in ['서점','책방','책장','서원','도서관','마켓','시장']):
  # Bookshelves / stationery / traditional brick bookstores
  bw=270+rng.randrange(90); bh=185+rng.randrange(55)
  x0=cx-bw//2;y0=cy-bh
  p.polygon([(x0-12,y0),(x0+bw+12,y0),(x0+bw,cy),(x0,cy)],fill=(221,180,150,105),outline=ink)
  box(x0+12,y0+30,x0+bw-12,cy-15,(246,228,193,163))
  for k in range(2+(variant%3)):
   sy=y0+65+k*39
   line([(x0+22,sy+22),(x0+bw-25,sy+22)],2,(70,78,74,125))
   for m in range(10):
    xx=x0+26+m*((bw-56)//10)
    ww=rng.randint(18,49)
    box(xx,sy-rng.randint(3,12),xx+ww,sy+19,(rng.randint(115,226),rng.randint(125,211),rng.randint(121,193),150),width=1)
  if category=='소품샵':
   for i in range(5):
    x=x0+44+i*45; y=cy-22
    ellipse((x-9,y-23,x+9,y),(199,152,109,130))
  leafy(x0-40,cy+18,5)
 elif category=='카페·디저트' or any(s in name for s in ['베이커리','커피','로스터리','카페']):
  bw=260+rng.randrange(120); bh=190+rng.randrange(50)
  x0=cx-bw//2;y0=cy-bh
  box(x0,y0,x0+bw,cy,(227,200,174,150))
  p.polygon([(x0-15,y0+36),(x0+bw+15,y0+36),(x0+bw,y0+73),(x0,y0+73)],fill=(98+rng.randrange(40),147,163,125),outline=ink)
  for k in range(4):
   xx=x0+(k+1)*bw/5
   line([(xx,y0+38),(xx,y0+73)],2,(239,232,211,170))
  box(x0+25,y0+95,x0+bw-25,cy-16,(198,221,219,155))
  for k in range(3):
   xx=x0+48+k*((bw-96)/3)
   ellipse((xx,cy-38,xx+28,cy-10),(236,199-rng.randrange(40),145,160))
  # coffee cup and pastry display vary
  p.arc((cx-15,y0+110,cx+40,y0+157),0,180,fill=ink,width=3)
  p.line((cx-30,y0+149,cx+45,y0+149),fill=ink,width=2)
  leafy(x0-30,cy+15,4)
 elif category=='식사':
  bw=260+rng.randrange(110);bh=175+rng.randrange(65);x0=cx-bw//2;y0=cy-bh
  p.polygon([(x0-14,y0+42),(x0+bw+14,y0+42),(x0+bw-6,y0+18),(x0+6,y0+18)],fill=(131,162,163,132),outline=ink)
  box(x0,y0+40,x0+bw,cy,(223,189,158,140))
  box(x0+36,y0+89,x0+bw-32,cy-18,(252,232,198,180))
  for i in range(4):
   x=x0+64+i*45; yy=y0+143
   ellipse((x-21,yy-9,x+21,yy+15),(224,218,188,175),ink,2)
   ellipse((x-12,yy-6,x+12,yy+4),(118+rng.randrange(60),147,102,117),None)
  p.line((x0-22,cy,x0+bw+25,cy),fill=ink,width=3)
  leafy(x0-36,cy+5,6)
 else:
  # Art/culture/landscape structures – bridges, galleries, lighthouses, trains, gardens, theatres
  if any(t in name for t in ['열차','정거장','역']) or (category=='문화·공간' and variant in (7,11)):
   x0=cx-188;y0=cy-140
   box(x0,y0,x0+380,cy,(230,197,156,135))
   p.polygon([(x0,y0+30),(x0+380,y0+30),(x0+380,y0),(x0,y0)],fill=(115,158,180,139))
   for j in range(5): box(x0+35+j*69,y0+58,x0+82+j*69,cy-35,(156,193,201,130))
   for j in range(6): ellipse((x0+35+j*60,cy-8,x0+45+j*60,cy+4),(80,91,91,142),ink,1)
  elif any(t in name for t in ['요트','등대','항','터널','다리','수변','전망대','해수욕','바다','해변','동백']):
   if '등대' in name:
    x0=cx-20;box(x0,cy-220,x0+54,cy,(230,214,193,182));p.polygon([(x0-15,cy-219),(x0+70,cy-219),(x0+50,cy-253),(x0+4,cy-253)],fill=(199,112,94,152),outline=ink)
    ellipse((cx-2,cy-180,cx+36,cy-146),(223,231,197,190),ink)
   elif any(t in name for t in ['요트','항']):
    for j in range(2+variant%3):
     x=cx-125+j*85
     p.polygon([(x,cy-7),(x+66,cy-7),(x+46,cy+20),(x+15,cy+20)],fill=(161,174,183,170),outline=ink)
     line([(x+28,cy-7),(x+28,cy-180-rng.randrange(30))],2)
     p.polygon([(x+30,cy-166),(x+30,cy-25),(x+87,cy-25)],fill=(240,225,185,170),outline=thin)
   else:
    for j in range(2+(variant%3)):
     xx=int(W*(.15+j*.20));yy=horizon-22-rng.randrange(35)
     p.polygon([(xx-48,yy+15),(xx,yy-30),(xx+60,yy+15)],fill=(112,154,168,75),outline=thin)
    if '다리' in name or '광안' in name:
     line([(0,horizon-30),(W,horizon-30)],3)
     for j in range(11):line([(j*70,horizon-30),(j*70,horizon)],1)
   leafy(120,cy+10,7)
  else:
   bw=270+rng.randrange(155);bh=190+rng.randrange(52);x0=cx-bw//2;y0=cy-bh
   p.polygon([(x0-20,y0+32),(x0+bw+20,y0+32),(x0+bw-12,y0),(x0+12,y0)],fill=(179,190,173,132),outline=ink)
   box(x0,y0+31,x0+bw,cy,(208,209,187,155))
   for j in range(3+variant%2):
    xx=x0+35+j*(bw-75)//4
    box(xx,y0+66,xx+44,cy-35,(168,196,202,128))
   for j in range(3):leafy(x0-15+j*(bw//2),cy+18,4)
 scene=scene.filter(ImageFilter.GaussianBlur(.4))
 img=Image.alpha_composite(img,scene)
 q=ImageDraw.Draw(img,'RGBA')
 # Invented artistic marks and tiny ink strokes add the sketchbook texture
 for i in range(130):
  xx=rng.randrange(W);yy=rng.randint(40,H-38)
  if rng.random()<.42:
   q.line((xx,yy,xx+rng.randrange(5,28),yy+rng.randrange(-2,3)),fill=(61,89,100,rng.randrange(10,32)),width=1)
 # Editorial label is on a cream strip; it explicitly distinguishes sketch from photograph.
 q.rounded_rectangle((22,H-80,W-22,H-18),radius=12,fill=(252,249,237,223))
 try:font=ImageFont.truetype(FONT,27 if len(name)<17 else 22)
 except OSError:font=ImageFont.load_default()
 try:small=ImageFont.truetype(SERIF,13)
 except OSError:small=ImageFont.load_default()
 try:q.text((38,H-74),name,font=font,fill=(49,72,86,246))
 except (UnicodeEncodeError,ValueError):q.text((38,H-74),'BUSAN · PERSONAL SKETCH',font=font,fill=(49,72,86,246))
 q.text((W-133,H-43),'WATERCOLOUR',font=small,fill=(99,118,123,155))
 return img.convert('RGB')

def art_bytes(name,category):
 b=io.BytesIO();render(name,category).save(b,format='JPEG',quality=83,optimize=True);return b.getvalue()

if __name__=='__main__':
 import csv
 path=ROOT/'assets'/'places';path.mkdir(parents=True,exist_ok=True)
 with (ROOT/'data'/'places.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
 seen=set()
 for i,row in enumerate(rows):
  if row['name'] in seen:continue
  seen.add(row['name']);out=path/file_for(row['name']);out.write_bytes(art_bytes(row['name'],row['category']))
 print('CREATED',len(seen),'unique JPEG illustrations',sum(p.stat().st_size for p in path.glob('*.jpg'))//1024,'KiB')
