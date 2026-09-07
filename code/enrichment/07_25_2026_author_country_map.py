"""Proportional-symbol world map of author countries (matplotlib -> PNG, embedded in artifact).
Bubbles at country centroids, area ~ author-appearances, coloured by region; Saudi Arabia highlighted.
Also emits a light and a dark variant for the theme-aware artifact."""
import pandas as pd, numpy as np, base64, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

C = pd.read_csv('data/authors/07_25_2026_country_counts.csv')

# lon, lat centroids (approx) + region
GEO = {
 'Saudi Arabia':(45,24,'Gulf'),'United Arab Emirates':(54,24,'Gulf'),'Kuwait':(47.5,29.3,'Gulf'),
 'Qatar':(51.2,25.3,'Gulf'),'Oman':(56,21,'Gulf'),'Bahrain':(50.6,26,'Gulf'),
 'Egypt':(30,27,'Other Arab'),'Jordan':(36,31,'Other Arab'),'Lebanon':(35.8,33.8,'Other Arab'),
 'Iraq':(44,33,'Other Arab'),'Palestine':(35.2,31.9,'Other Arab'),'Yemen':(48,15.5,'Other Arab'),
 'Sudan':(30,15,'Other Arab'),'Syria':(38,35,'Other Arab'),'Tunisia':(9,34,'Other Arab'),
 'Morocco':(-7,32,'Other Arab'),'Algeria':(3,28,'Other Arab'),'Libya':(17,27,'Other Arab'),
 'Italy':(12.5,42,'Europe'),'United Kingdom':(-1.5,53,'Europe'),'Greece':(22,39,'Europe'),
 'France':(2.5,46.5,'Europe'),'Germany':(10.5,51,'Europe'),'Spain':(-3.7,40,'Europe'),
 'Austria':(14,47.5,'Europe'),'Poland':(19,52,'Europe'),'Sweden':(15,62,'Europe'),
 'Netherlands':(5.5,52,'Europe'),'Finland':(26,64,'Europe'),'Russia':(60,60,'Europe'),
 'Ireland':(-8,53,'Europe'),'Belgium':(4.5,50.8,'Europe'),'Ukraine':(32,49,'Europe'),
 'Romania':(25,46,'Europe'),'Denmark':(10,56,'Europe'),'Norway':(10,62,'Europe'),
 'Portugal':(-8,39.5,'Europe'),'Croatia':(15.5,45.1,'Europe'),'Switzerland':(8,46.8,'Europe'),
 'Slovenia':(14.8,46.1,'Europe'),'Albania':(20,41,'Europe'),'Bosnia and Herzegovina':(18,44,'Europe'),
 'Iceland':(-19,65,'Europe'),'Bulgaria':(25,43,'Europe'),'North Macedonia':(21.7,41.6,'Europe'),
 'Belarus':(28,53.7,'Europe'),'Czech Republic':(15.5,49.8,'Europe'),'Kosovo':(21,42.6,'Europe'),
 'Lithuania':(24,55.2,'Europe'),'Luxembourg':(6.1,49.8,'Europe'),'Hungary':(19.4,47.2,'Europe'),
 'Cyprus':(33.4,35.1,'Europe'),'Georgia':(43.5,42,'Europe'),'Armenia':(45,40,'Europe'),
 'India':(79,22,'Asia'),'Pakistan':(69,30,'Asia'),'China':(105,35,'Asia'),'Malaysia':(102,4,'Asia'),
 'Turkey':(35,39,'Asia'),'Iran':(53,32,'Asia'),'South Korea':(128,36,'Asia'),'Bangladesh':(90,24,'Asia'),
 'Japan':(138,36,'Asia'),'Vietnam':(106,16,'Asia'),'Israel':(35,31.5,'Asia'),'Philippines':(122,12,'Asia'),
 'Thailand':(101,15,'Asia'),'Indonesia':(120,-2,'Asia'),'Singapore':(103.8,1.35,'Asia'),
 'Hong Kong':(114.1,22.3,'Asia'),'Nepal':(84,28,'Asia'),'Sri Lanka':(81,7,'Asia'),'Myanmar':(96,21,'Asia'),
 'Afghanistan':(66,34,'Asia'),'Cambodia':(105,12.5,'Asia'),'Bhutan':(90.4,27.4,'Asia'),
 'Taiwan':(121,23.7,'Asia'),'Kazakhstan':(67,48,'Asia'),'Uzbekistan':(64,41.4,'Asia'),
 'Nigeria':(8,9,'Sub-Saharan Africa'),'Ghana':(-1,8,'Sub-Saharan Africa'),'Ethiopia':(40,9,'Sub-Saharan Africa'),
 'South Africa':(24,-29,'Sub-Saharan Africa'),'Somalia':(46,6,'Sub-Saharan Africa'),'Kenya':(38,0,'Sub-Saharan Africa'),
 'Benin':(2.3,9.3,'Sub-Saharan Africa'),'Botswana':(24,-22,'Sub-Saharan Africa'),'Uganda':(32.3,1.3,'Sub-Saharan Africa'),
 'Zimbabwe':(30,-19,'Sub-Saharan Africa'),'Tanzania':(35,-6,'Sub-Saharan Africa'),
 'United States':(-98,39,'Americas'),'Canada':(-106,56,'Americas'),'Brazil':(-51,-10,'Americas'),
 'Colombia':(-74,4,'Americas'),'Mexico':(-102,23,'Americas'),'Argentina':(-64,-34,'Americas'),
 'Chile':(-71,-35,'Americas'),'Paraguay':(-58,-23,'Americas'),'Peru':(-76,-10,'Americas'),
 'Cuba':(-79,21.5,'Americas'),'Uruguay':(-56,-33,'Americas'),'Bolivia':(-64,-17,'Americas'),
 'Australia':(134,-25,'Oceania'),'New Zealand':(172,-41,'Oceania'),'New Caledonia':(165.5,-21.3,'Oceania'),
}
REGION_COLOR = {
 'Gulf':'#16697a','Other Arab':'#489fb5','Europe':'#c77dff'.replace('#c77dff','#6a4c93'),
 'Asia':'#e07a5f','Sub-Saharan Africa':'#c9a227','Americas':'#2a9d8f','Oceania':'#9b5de5',
}
# recolor for clarity
REGION_COLOR = {'Gulf':'#0f5c6b','Other Arab':'#5aa9bd','Europe':'#6a4c93','Asia':'#e07a5f',
                'Sub-Saharan Africa':'#b8860b','Americas':'#2a9d8f','Oceania':'#c05299'}

import matplotlib.patheffects as pe

def draw(theme):
    dark = theme=='dark'
    fg = '#e8eef0' if dark else '#1b2b2f'
    ocean = '#0e1a1d' if dark else '#eef4f5'
    grid = '#26383d' if dark else '#dbe6e8'
    halo = '#0a1214' if dark else '#ffffff'
    K = 0.55   # radius scale (Saudi excluded from scaled bubbles -> max is ~199)
    fig, ax = plt.subplots(figsize=(15.5,8.0), dpi=150)
    fig.patch.set_facecolor('none'); ax.set_facecolor(ocean)
    ax.set_xlim(-168,187); ax.set_ylim(-56,86)
    for lon in range(-150,181,30): ax.axvline(lon,color=grid,lw=.6,zorder=1)
    for lat in range(-45,76,15): ax.axhline(lat,color=grid,lw=.6,zorder=1)
    ax.axhline(0,color=grid,lw=1.0,zorder=1)
    rows = C[C.country!='Saudi Arabia'].sort_values('author_appearances',ascending=False)
    # bubbles (biggest at back)
    for _,r in rows.iterrows():
        name=r['country']; v=r['author_appearances']
        if name not in GEO or v<=0: continue
        lon,lat,reg=GEO[name]; rad=K*np.sqrt(v)
        ax.add_patch(Circle((lon,lat),rad,facecolor=REGION_COLOR[reg],
                     edgecolor=halo,lw=.6,alpha=.85,zorder=5))
    # Saudi Arabia: home-base star (not scaled)
    slon,slat,_=GEO['Saudi Arabia']
    ax.scatter([slon],[slat],marker='*',s=520,facecolor='#e9b949',edgecolor='#7a5c00',
               lw=1.1,zorder=8)
    _sau=int(C.loc[C.country=='Saudi Arabia','author_appearances'].iloc[0])
    ax.annotate(f'Saudi Arabia\n{_sau} authors  (home)',(slon,slat-2.2),ha='center',va='top',
                fontsize=8.6,color=fg,fontweight='bold',zorder=9,linespacing=.95,
                path_effects=[pe.withStroke(linewidth=2.4,foreground=halo)])
    # labels for major hubs (>=30 authors), placed above the bubble
    for _,r in rows.iterrows():
        name=r['country']; v=r['author_appearances']
        if name not in GEO or v<30: continue
        lon,lat,reg=GEO[name]; rad=K*np.sqrt(v)
        short={'United States':'USA','United Kingdom':'UK'}.get(name,name)
        ax.annotate(f'{short} {v}',(lon,lat+rad+0.6),ha='center',va='bottom',
                    fontsize=7.0,color=fg,fontweight='bold',zorder=9,
                    path_effects=[pe.withStroke(linewidth=2.0,foreground=halo)])
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_color(grid)
    # region legend (upper-left ocean)
    from matplotlib.lines import Line2D
    handles=[Line2D([0],[0],marker='o',color='none',markerfacecolor=c,markersize=9,label=k)
             for k,c in REGION_COLOR.items()]
    handles.append(Line2D([0],[0],marker='*',color='none',markerfacecolor='#e9b949',
                   markeredgecolor='#7a5c00',markersize=13,label='Saudi Arabia (home)'))
    leg=ax.legend(handles=handles,loc='lower left',frameon=True,fontsize=8,
                  facecolor=ocean,edgecolor=grid,labelcolor=fg,ncol=2,title='World region  ·  bubble area ∝ author count')
    leg.get_title().set_color(fg); leg.get_title().set_fontweight('bold'); leg.set_zorder(20)
    # nested size legend (empty South Atlantic) - circles share a bottom baseline
    cx,base=-26,-54; rmax=K*np.sqrt(200)
    for val in (200,100,25):
        rad=K*np.sqrt(val)
        ax.add_patch(Circle((cx,base+rad),rad,facecolor='none',edgecolor=fg,lw=1,zorder=6))
        ax.plot([cx,cx+rmax+3],[base+2*rad,base+2*rad],color=fg,lw=.5,zorder=6)
        ax.text(cx+rmax+4,base+2*rad,f'{val}',ha='left',va='center',fontsize=7,color=fg)
    ax.text(cx,base+2*rmax+3,'authors',ha='center',va='bottom',fontsize=7.5,
            color=fg,style='italic',fontweight='bold')
    plt.tight_layout(pad=0.3)
    out=f'07_25_2026_author_country_map_{theme}.png'
    fig.savefig(out,dpi=150,bbox_inches='tight',facecolor='none',transparent=True)
    plt.close(fig)
    with open(out,'rb') as f:
        b64=base64.b64encode(f.read()).decode()
    return out,b64

if __name__=='__main__':
    b64={}
    for t in ('light','dark'):
        out,enc=draw(t); b64[t]=enc; print('wrote',out,f'({len(enc)//1024} KB b64)')
    json.dump(b64,open('data/authors/07_25_2026_map_b64.json','w'))
    print('saved base64 for both themes -> data/authors/07_25_2026_map_b64.json')
