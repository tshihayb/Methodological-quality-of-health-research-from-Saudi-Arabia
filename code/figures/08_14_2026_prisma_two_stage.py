# -*- coding: utf-8 -*-
# PRISMA — Saudi 2022 health-research quality study. TWO-STAGE single figure:
# Stage 1 study selection (main 1,000 + supplementary 20) -> Stage 2 quality-review conduct -> 385 analysed.
import html
AC="#16697a"; INK="#232830"; MUT="#5c6570"; PAPER="#f6f5f1"; BOX="#ffffff"; BD="#c7ccc3"
EXF="#faf7f2"; EXB="#d3c4b0"; AMF="#f9efdd"; AMB="#d7a24a"; AMT="#8a5511"; ARR="#98a0a4"
SUF="#eef4f4"; SUB="#a9ccd0"
serif='Iowan Old Style, "Palatino Linotype", Palatino, Georgia, serif'
sans='system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'
W=1200
MX=64;  MW=392                      # main spine
RX=486; RW=316                      # side (exclusion) column
SX=832; SW=336                      # supplementary column
CX=MX+MW/2; SUX=SX+SW/2
els=[]
def esc(s): return html.escape(str(s), quote=True)
def rect(x,y,w,h,fill,stroke,rx=9,sw=1.4):
    els.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def line(x1,y1,x2,y2,w=1.7,dash=""):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    els.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{ARR}" stroke-width="{w}"{d} marker-end="url(#a)"/>')
def elbow(x1,y1,x2,y2,w=1.7):        # horizontal then vertical elbow with arrow at end
    els.append(f'<path d="M {x1:.0f} {y1:.0f} H {x2:.0f} V {y2:.0f}" fill="none" stroke="{ARR}" stroke-width="{w}" marker-end="url(#a)"/>')
def txt(x,y,s,size=13.5,fill=INK,anchor="start",weight="400",ff=sans):
    els.append(f'<text x="{x:.0f}" y="{y:.1f}" font-family="{ff}" font-size="{size}" fill="{fill}" '
               f'text-anchor="{anchor}" font-weight="{weight}" style="font-variant-numeric:tabular-nums">{esc(s)}</text>')
def box(x,y,w,rows,fill=BOX,stroke=BD,pad=12,lh=18,rx=9):
    h=pad*2+lh*len(rows); rect(x,y,w,h,fill,stroke,rx); ty=y+pad+13
    for (t,sz,fc,wt) in rows: txt(x+15,ty,t,size=sz,fill=fc,weight=wt); ty+=lh
    return h

# ============================== IDENTIFICATION ==============================
y=70
hid=box(MX,y,MW,[("Records identified — PubMed 2022, Saudi-affiliated",13.5,INK,"600"),
                 ("via a reproducible R query",12,MUT,"400"),("n = 5,558",14.5,AC,"700")])
idb=y+hid
# two draws
sy=idb+34
h_main=box(MX,sy,MW,[("Main random sample",13,INK,"600"),
                     ("simple random sample, without replacement",12,MUT,"400"),("n = 1,000",14,INK,"700")])
h_sup=box(SX,sy,SW,[("Supplementary random sample",13,INK,"600"),
                    ("simple random sample, same query",12,MUT,"400"),("n = 20",14,INK,"700")],fill=SUF,stroke=SUB)
line(CX,idb,CX,sy)                                   # identify -> main
elbow(CX,idb+16,SUX,sy)                              # identify -> supplementary
mainb=sy+h_main

# ============================== SCREENING (main) ==============================
# not screened branches from the Main 1,000 row (side)
h_ns=box(RX,sy,RW,[("Not screened — sample-size target met",12.5,MUT,"700"),
                   ("target of N = 385 reached;",11.5,MUT,"400"),
                   ("Seq 622–1000 never assessed:  379",11.5,MUT,"400")],fill=PAPER,stroke=BD)
line(MX+MW,sy+h_main/2,RX,sy+h_ns/2)
# screened
ny=mainb+30
h_scr=box(MX,ny,MW,[("Records screened, in random order",13,INK,"600"),
                    ("(title / abstract + full text)",12,MUT,"400"),("n = 621",14.5,AC,"700")])
line(CX,mainb,CX,ny)
scrb=ny+h_scr
# passed screening
py=scrb+30
h_pass=box(MX,py,MW,[("Passed screening",13,INK,"600"),("n = 385",14.5,AC,"700")])
line(CX,scrb,CX,py)
# excluded-at-screening reason box (single column), aligned to the screened row, branches from it
exPad=12; exLH=17.5
reasons=[("Non-human / laboratory","174"),("Non-health topic","22"),("Review (narrative / systematic)","14"),
         ("Qualitative research","11"),("Non-empirical (protocol / simulation)","9"),("Case report / series","6")]
exH=exPad*2+18+16+len(reasons)*exLH
rect(RX,ny,RW,exH,EXF,EXB,9)
ey=ny+exPad+13
txt(RX+15,ey,"Excluded at screening — n = 236",12.5,INK,weight="700"); ey+=18
txt(RX+15,ey,"eligibility reasons:",11.5,MUT,weight="600"); ey+=16
for lab,cnt in reasons:
    txt(RX+22,ey,"•  "+lab,11.5,MUT); txt(RX+RW-16,ey,cnt,11.5,INK,anchor="end",weight="700"); ey+=exLH
line(MX+MW,ny+h_scr/2,RX,ny+h_scr/2)
passb=py+h_pass

# ============================== SUPPLEMENTARY branch ==============================
supy=sy+h_sup+30
h_add=box(SX,supy,SW,[("Added to the analysis — n = 3",12.5,INK,"700"),
                      ("2 Causal · 1 Predictive",11,MUT,"400")],fill=SUF,stroke=SUB)
line(SUX,sy+h_sup,SUX,supy)
h_na=box(SX,supy+h_add+22,SW,[("Not added — n = 17",12.5,MUT,"700"),
                      ("eligible but surplus (target met):  5",11.5,MUT,"400"),
                      ("excluded with reasons:  12",11.5,MUT,"400")],fill=PAPER,stroke=BD)
line(SUX,supy+h_add,SUX,supy+h_add+22)
addb=supy+h_add

# ============================== STAGE 2 — REVIEW CONDUCT ==============================
ay=passb+40
h_asg=box(MX,ay,MW,[("Assigned for dual quality review",13,INK,"600"),
                    ("13 reviewers · 2 per paper · 770 reviews",12,MUT,"400"),
                    ("5 recusals (conflict of interest) re-assigned",11.5,MUT,"400")])
line(CX,passb,CX,ay,dash="1 0")
# recusal-reasons box (side, aligned with the Assigned box)
h_rec=box(RX,ay,RW,[("Recusal reasons — conflict of interest (n = 5)",11.8,MUT,"700"),
                    ("•  the co-PI is a co-author",11,MUT,"400"),
                    ("•  an author is a relative",11,MUT,"400"),
                    ("•  collaborator with the first author",11,MUT,"400"),
                    ("•  an author heads the reviewer’s department",11,MUT,"400"),
                    ("•  not stated (re-covered by a 3rd reviewer)",11,MUT,"400")],
          fill=PAPER,stroke=BD,pad=11,lh=15.5)
line(MX+MW,ay+h_asg/2,RX,ay+h_rec/2)
asgb=ay+h_asg
# excluded post-review (side)
ry=max(asgb,ay+h_rec)+30
h_ret=box(MX,ry,MW,[("Retained after post-hoc exclusions",13,INK,"600"),("n = 382",14.5,AC,"700")])
line(CX,asgb,CX,ry)
h_pr=box(RX,ry,RW,[("Excluded after review — n = 3",12.5,AMT,"700"),
                   ("•  Co-authored by a study reviewer (COI):  1",11.5,AMT,"400"),
                   ("•  No Saudi affiliation:  2",11.5,AMT,"400")],fill=AMF,stroke=AMB)
line(MX+MW,ry+h_ret/2,RX,ry+h_ret/2)
retb=ry+h_ret

# ============================== FINAL ==============================
fy=retb+40
h_fin=box(MX,fy,MW,[("Studies in the final analysis",14,"#ffffff","700"),("n = 385",17,"#ffffff","800"),
                    ("382 main sample  +  3 supplementary  ·  770 reviews",11.5,"#dceef1","400")],
          fill=AC,stroke=AC,pad=14,lh=22)
line(CX,retb,CX,fy)
# supplementary 3 -> final: exit Added box LEFT, drop through the gap between the two right columns, into final
gapx=(RX+RW+SX)/2
els.append(f'<path d="M {SX:.0f} {supy+h_add/2:.0f} H {gapx:.0f} V {fy+h_fin/2:.0f} H {MX+MW:.0f}" fill="none" stroke="{AC}" stroke-width="1.8" stroke-dasharray="5 4" marker-end="url(#a)"/>')

# ---- footer panel: HOW each 'excluded at screening' reason was established (n = 236) ----
pv_y=fy+h_fin+30; pvW=(SX+SW)-MX; pvH=12+20+3*17+16
rect(MX,pv_y,pvW,pvH,SUF,SUB,9)
txt(MX+16,pv_y+19,"How each “excluded at screening” reason (n = 236) was established",12.5,INK,weight="700")
items=[("169","both reviewers agreed on the reason"),
       ("18","reviewers disagreed — they adjudicated it"),
       ("7","disagreed, not adjudicated — LLM adjudicated"),
       ("38","one reviewer gave a reason — LLM as 2nd reviewer"),
       ("4","no reviewer reason — LLM determined it")]
c1x=MX+24; c2x=MX+pvW/2+18; cy0=pv_y+19+22
for i,(n,lab) in enumerate(items):
    cxx=c1x if i<3 else c2x; row=i if i<3 else i-3; yy=cy0+row*17
    txt(cxx,yy,n,12,AC,anchor="end",weight="700"); txt(cxx+8,yy,"· "+lab,11.5,MUT)
txt(c2x-24,cy0+2*17,"LLM inputs used the 169 agreed reasons as few-shot examples",11,MUT)
H=pv_y+pvH+30

# ---- band rail ----
def band(y0,y1,label):
    els.insert(0,f'<rect x="26" y="{y0:.0f}" width="6" height="{y1-y0:.0f}" rx="3" fill="{AC}" opacity="0.85"/>')
    cy=(y0+y1)/2
    els.append(f'<text x="20" y="{cy:.0f}" font-family="{serif}" font-size="11.5" fill="{AC}" text-anchor="middle" '
               f'font-weight="600" letter-spacing="1.4" transform="rotate(-90 20 {cy:.0f})" style="text-transform:uppercase">{label}</text>')
band(66, idb+6, "Identification")
band(sy-4, passb+4, "Screening")
band(ay-6, retb+4, "Review conduct")
band(fy-6, fy+h_fin+2, "Analysed")

defs=(f'<defs><marker id="a" markerWidth="9" markerHeight="9" refX="7.2" refY="4" orient="auto">'
      f'<path d="M0,0 L8,4 L0,8 z" fill="{ARR}"/></marker></defs>')
title=f'<text x="{MX}" y="44" font-family="{serif}" font-size="19" fill="{INK}" font-weight="700">Study selection &amp; review conduct &#8212; PRISMA flow</text>'
svg=(f'<svg xmlns="[ARTICLE-URL-REDACTED]" viewBox="0 0 {W} {H:.0f}" width="{W}" height="{H:.0f}" '
     f'font-family="{sans}"><rect width="{W}" height="{H:.0f}" fill="{PAPER}"/>{defs}{title}'+''.join(els)+'</svg>')
open('outputs/figures/08_14_2026_prisma_two_stage.svg','w',encoding='utf-8').write(svg)
print('wrote SVG %dx%.0f'%(W,H))

svg_resp=svg.replace(f'width="{W}" height="{H:.0f}" font-family','width="100%" height="auto" font-family',1)
page=f'''<title>PRISMA flow</title>
<style>
:root{{--pg:#eef0ec;--card:#fff;--ink:#232830;--mut:#5c6570;--ac:#16697a;--hair:#dfe2db;}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--pg:#0f1216;--card:#151a1f;--ink:#e9edf1;--mut:#9aa4b1;--ac:#5bb5c6;--hair:#262c33;}}}}
:root[data-theme="dark"]{{--pg:#0f1216;--card:#151a1f;--ink:#e9edf1;--mut:#9aa4b1;--ac:#5bb5c6;--hair:#262c33;}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--pg);color:var(--ink);font-family:{sans};padding:clamp(16px,4vw,40px)}}
.wrap{{max-width:1240px;margin:0 auto}}
.eyebrow{{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--ac);font-weight:700;margin:0 0 8px}}
h1{{font-family:{serif};font-weight:700;font-size:clamp(21px,3vw,29px);margin:0 0 8px;text-wrap:balance}}
p.lede{{color:var(--mut);max-width:78ch;margin:0 0 22px;line-height:1.55}}
.fig{{background:var(--card);border:1px solid var(--hair);border-radius:14px;padding:clamp(8px,2vw,16px);overflow-x:auto}}
.fig svg{{display:block;width:100%;min-width:760px;height:auto}}
.note{{color:var(--mut);font-size:12.5px;line-height:1.65;max-width:96ch;margin:16px 2px 0}} .note b{{color:var(--ink)}}
</style>
<div class="wrap">
<p class="eyebrow">Assessment of Healthcare Research Quality · Saudi Arabia</p>
<h1>Study selection &amp; review conduct — PRISMA flow</h1>
<p class="lede">A reproducible PubMed 2022 Saudi-affiliated query, sampled in two independent simple random draws, screened in random order to the sample-size target, then dual-reviewed by 13 epidemiologists — yielding the 385-study analysis set.</p>
<div class="fig">{svg_resp}</div>
<p class="note"><b>Reconciliation.</b> Of the main sample of 1,000, 379 were never assessed (target reached) and 621 were screened → 236 excluded and <b>385 passed screening</b>. These 385 were assigned for dual quality review (13 reviewers, 770 reviews; 5 recusals re-assigned). During review, 3 were excluded (1 co-authored by a study reviewer, 2 without a Saudi affiliation), leaving 382; the supplementary sample of 20 contributed 3 added studies, for <b>385 studies analysed</b> (770 reviews). The screening reason counts are the reviewer-locked tally (before the LLM-validation refinements).</p>
</div>'''
open('outputs/reports/08_14_2026_prisma_two_stage.html','w',encoding='utf-8').write(page)
print('wrote HTML')
