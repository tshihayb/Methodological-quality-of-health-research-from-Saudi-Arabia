# -*- coding: utf-8 -*-
"""Classify a Saudi affiliation block into an institution TYPE + specific institution.

Strategy: identify the top-level *employing* institution, not the nested department/college.
Three tiers, tried in order; within a tier the RIGHTMOST alias (closest to the city, i.e. the
top-level org) wins:
  Tier 1  specific named institutions (universities, named hospitals/medical cities, military
          facilities, agencies, councils, research centres, companies, private colleges)
  Tier 2  umbrella ministries / health systems (MoH, MNGHA, other ministries, health clusters)
  Tier 3  keyword fallback

Documented rulings (flagged for the user, easy to change here):
  * KFSHRC -> Hospital / medical city (a specialist hospital that also runs research).
  * University teaching hospitals / university medical cities -> University.
  * National-Guard health facilities by function: King Abdulaziz Medical City -> Hospital,
    KAIMRC -> Research centre, KSAU-HS -> University; only the bare 'Ministry of National Guard
    Health Affairs' umbrella -> Military & security-forces.
  * [NAME-REDACTED] / Interior / National Guard -> Military & security-forces (not 'other gov').
"""
import re, unicodedata

# Canonical type labels
UNIV='University'; HOSP='Hospital / medical city'; HOSPRES='Hospital & research centre'
MIL='Military & security-forces medical'
MOH='Ministry of Health'; GOV='Other government / ministry'; AUTH='Government authority / agency'
COUN='Council / commission'; RES='Research centre / institute'; CO='Company / industry'
SOC='Society / association / NGO'; OTH='Other / unspecified'

def _compact(s):
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', s.lower())

def _norm(s):
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', s.lower())

# ---------------- Tier 1: specific named institutions ----------------
# (type, canonical, [compact aliases])
TIER1 = [
 # --- public universities (aliases chosen so teaching hospitals/medical cities fold in) ---
 (UNIV,'King Saud University',['kingsauduniversity','kingsaudmedicaluniversity','kingkhaliduniversityhospital','kingsaudiuniversity']),
 (UNIV,'King Abdulaziz University',['kingabdulazizuniversity','kingabdelazizuniversity']),
 (UNIV,'Imam Abdulrahman Bin Faisal University',['imamabdulrahmanbinfaisaluniversity','imamabdulrahman','universityofdammam','imamabdurrahmanbinfaisal','imamabdulrahmanbinfaisal','kingfahdhospitaloftheuniversity','kingfahadhospitaloftheuniversity','imamabdulraman']),
 (UNIV,'Umm Al-Qura University',['ummalquurauniversity','ummalqurauniversity','ummalqura']),
 (UNIV,'King Khalid University',['kingkhaliduniversity']),
 (UNIV,'Qassim University',['qassimuniversity','alqassimuniversity']),
 (UNIV,'Prince Sattam Bin Abdulaziz University',['princesattam','princesattambinabdulaziz','princesattambinabddulaziz','princesattambinabdullaziz','pricesattam']),
 (UNIV,'Jazan University',['jazanuniversity','jizanuniversity']),
 (UNIV,'Jouf University',['joufuniversity','aljoufuniversity']),
 (UNIV,'King Saud bin Abdulaziz University for Health Sciences',['kingsaudbinabdulaziz','ksauhs','kingsaudbinabdelaziz']),
 (UNIV,'Taibah University',['taibahuniversity','taibauniversity']),
 (UNIV,'Majmaah University',['majmaahuniversity','almajmaahuniversity']),
 (UNIV,'King Faisal University',['kingfaisaluniversity']),
 # KAAUH is PNU's teaching hospital -> University, per the teaching-hospital ruling above
 (UNIV,'Princess Nourah Bint Abdulrahman University',['princessnourah','princessnora','princessnoura','kingabdullahbinabdulazizuniversityhospital','kaauh']),
 (UNIV,'Taif University',['taifuniversity']),
 (UNIV,'University of Hail',['universityofhail','hailuniversity','universityofhail','universityofhal']),
 (UNIV,'Northern Border University',['northernborderuniversity']),
 (UNIV,'University of Tabuk',['universityoftabuk','tabukuniversity']),
 (UNIV,'[NAME-REDACTED]',['najranuniversity']),
 (UNIV,'[NAME-REDACTED]',['shaqrauniversity','shaqrauniversity']),
 (UNIV,'[NAME-REDACTED]',['universityofjeddah']),
 (UNIV,'[NAME-REDACTED]',['albahauniversity','universityofalbaha','albahuniversity']),
 (UNIV,'[NAME-REDACTED]',['universityofbusinessandtechnology']),
 (UNIV,'[NAME-REDACTED]',['onaizahcolleges','unaizahcolleges']),
 (UNIV,'University of Bisha',['universityofbisha','bishauniversity']),
 (UNIV,'[NAME-REDACTED]',['universityofhafralbatin','hafralbatinuniversity']),
 (UNIV,'[NAME-REDACTED]',['kingfahduniversityofpetroleum','kingfahduniversityofpetroleumandminerals','kfupm']),
 (UNIV,'[NAME-REDACTED]',['saudielectronicuniversity']),
 (UNIV,'[NAME-REDACTED]',['naifarabuniversity','naifarabuniversityforsecurity']),
 (UNIV,'Imam Mohammad Ibn Saud Islamic University',['imammohammadibnsaud','imammuhammadibnsaud','alimammuhammadibnsaud','alimammohammadibnsaud','imsiu','imammohammedibnsaud']),
 (UNIV,'Prince Mohammad Bin Fahd University',['princemohammadbinfahduniversity','princemohammedbinfahduniversity']),
 (UNIV,'[NAME-REDACTED]',['shaqra']),
 # --- private universities / colleges ---
 (UNIV,'Alfaisal University',['alfaisaluniversity']),
 (UNIV,'Almaarefa University',['almaarefauniversity','almaarefa','almarefauniversity']),
 (UNIV,'[NAME-REDACTED]',['daraluloomuniversity','daraluloom']),
 (UNIV,'[NAME-REDACTED]',['riyadhelmuniversity','riyadhelm','riyadhcollegesofdentistry']),
 (UNIV,'[NAME-REDACTED]',['sulaimanalrajhi','alrajhiuniversity','sulaimanalrajhicolleges']),
 (UNIV,'[NAME-REDACTED]',['effatuniversity']),
 (UNIV,'[NAME-REDACTED]',['fakeehcollege','fakeehcollegeforhealthsciences']),
 (UNIV,'[NAME-REDACTED]',['almanacollege','mohammedalmana','almanacollegeformedical']),
 (UNIV,'[NAME-REDACTED]',['batterjee']),
 (UNIV,'[NAME-REDACTED]',['visionmedicalcollege']),
 (UNIV,'[NAME-REDACTED]',['ibnsinanationalcollege','ibnsinacollege']),
 (UNIV,'[NAME-REDACTED]',['buraydahprivatecolleges','buraydahcolleges']),
 (UNIV,'[NAME-REDACTED]',['alrayancolleges','alrayan']),
 (UNIV,'[NAME-REDACTED]',['arabeastcolleges']),
 (UNIV,'[NAME-REDACTED]',['inayamedical','inayamedicalcollege','inayamedicalcollage']),
 (UNIV,'[NAME-REDACTED]',['princesultanuniversity']),
 (UNIV,'[NAME-REDACTED]',['almustaqbaluniversity','almustaqbalcollege']),
 # --- named standalone hospitals / medical cities ---
 (HOSP,'King Fahad Medical City',['kingfahdmedicalcity','kingfahadmedicalcity']),
 (HOSPRES,'King Faisal Specialist Hospital & Research Centre',['kingfaisalspecialisthospital','kfshrc','kingfaisaspecialisthospital']),
 (HOSP,'King Abdulaziz Medical City',['kingabdulazizmedicalcity','kingabdelazizmedicalcity','kingabdulazizmedicalcity','kamc']),
 (HOSP,'[NAME-REDACTED]',['kingsaudmedicalcity']),
 (HOSP,'King Abdullah Medical City',['kingabdullahmedicalcity']),
 (HOSP,'[NAME-REDACTED]',['kingkhaledeyespecialist','kkesh','kingkhalideyespecialist']),
 (HOSP,'[NAME-REDACTED]',['princesultancardiac']),
 (HOSP,'[NAME-REDACTED]',['princekhaledbinsultancardiac']),
 (HOSP,'[NAME-REDACTED]',['saudigermanhospital']),
 (HOSP,'[NAME-REDACTED]',['sulaimanalhabib','alhabibmedicalgroup','drsulaimanalhabib']),
 (HOSP,'[NAME-REDACTED]',['almoosa']),
 (HOSP,'[NAME-REDACTED]',['alansarispecialist','alansarihospital']),
 (HOSP,'[NAME-REDACTED]',['fakeehcare','solimanfakeeh','fakeehhospital']),
 (HOSP,'Dallah Hospital',['dallahhospital']),
 (HOSP,'Kingdom Hospital',['kingdomhospital']),
 (HOSP,'[NAME-REDACTED]',['eradacomplex','eradahcomplex','eradamental','eradahmental','eradaandmentalhealth']),
 (HOSP,'[NAME-REDACTED]',['dammammedicalcomplex']),
 (HOSP,'[NAME-REDACTED]',['autismcenterofexcellence','autismcentreofexcellence']),
 # --- added 2026-08-23: named hospitals that were falling to the tier-3 keyword
 #     fallback and printing as "(hospital/clinic, unnamed)" in Supplementary Fig. S2.
 #     They were never unnamed -- they were simply absent from this list.
 # NOTE: no city in these canonical names. The same hospital name recurs in several
 # cities ([NAME-REDACTED] exists in Hail AND Al-Kharj), and the block's city is
 # already captured in its own column -- so naming a city here would assert something
 # the classifier cannot know.
 (HOSP,'King Fahad Specialist Hospital',['kingfahadspecialisthospital','kingfahdspecialisthospital','kingfahdspecialtyhospital','kingfahadspecialtyhospital']),
 (HOSP,'[NAME-REDACTED]',['kingfahdcentralhospital','kingfahadcentralhospital']),
 (HOSP,'[NAME-REDACTED]',['kingfahadgeneralhospital','kingfahdgeneralhospital']),
 (HOSP,'[NAME-REDACTED]',['kingfahdhospital','kingfahadhospital']),
 (HOSP,'[NAME-REDACTED]',['kingabdulazizspecialisthospital','kingabdelazizspecialisthospital']),
 (HOSP,'[NAME-REDACTED]',['kingabdulazizgeneralhospital']),
 (HOSP,'[NAME-REDACTED]',['kingabdullahmedicalcomplex']),
 (HOSP,'[NAME-REDACTED]',['kingfaisalhospital']),
 (HOSP,'[NAME-REDACTED]',['kingkhalidhospital','kingkhaledhospital']),
 (HOSP,'[NAME-REDACTED]',['kingsalmanhospital']),
 (HOSP,'[NAME-REDACTED]',['princemohammedbinabdulazizhospital','princemohammadbinabdulazizhospital']),
 (HOSP,'[NAME-REDACTED]',['princemohammedbinnasser','princemohammadbinnasser']),
 (HOSP,'[NAME-REDACTED]',['alahsahospital']),
 (HOSP,'[NAME-REDACTED]',['ohudhospital','uhudhospital']),
 (HOSP,'[NAME-REDACTED]',['alahmadyhospital']),
 (HOSP,'[NAME-REDACTED]',['alqunfudahgeneralhospital','alqunfudhahgeneralhospital']),
 (HOSP,'[NAME-REDACTED]',['rafhacentralhospital']),
 (HOSP,'Jeddah National Hospital',['jeddahnationalhospital']),
 (HOSP,'[NAME-REDACTED]',['hailgeneralhospital','hailgeneralhospital']),
 (HOSP,'[NAME-REDACTED]',['astersanadhospital','sanadhospital']),
 (HOSP,'[NAME-REDACTED]',['almofarrehpolyclinic','almofarreh']),
 (HOSP,"Medina Maternity & Children's Hospital",['medinamaternityandchildrenshospital','madinahmaternityandchildrenshospital']),
 (HOSP,'Maternity & Children Hospital (MoH)',['maternityandchildrenhospital','maternityandchildrenshospital']),
 (HOSP,'[NAME-REDACTED]',['adultandchildtherapycenter','adultandchildtherapycentre']),
 # --- added 2026-08-24 after the S2 sweep (screens D and D2). These five were named on the
 #     page but matched no Tier-1 alias, so each fell through to the Tier-2 MoH badge in its
 #     own block and printed as the bare "Ministry of Health" -- losing the NAME and, because
 #     the sector follows the institution, mis-typing the SECTOR as well. Same class as the
 #     2026-08-23 "(hospital/clinic, unnamed)" fix, one tier up.
 # ⚠ [NAME-REDACTED] (Hail) is a different facility from [NAME-REDACTED]
 #   (Riyadh) above; neither alias is a substring of the other, so both resolve correctly.
 (HOSP,'[NAME-REDACTED]',['kingsalmanspecialisthospital','kingsalmanspecialityhospital']),
 (HOSP,'[NAME-REDACTED]',['ajyademergencyhospital','ajyadhospital']),
 (HOSP,'[NAME-REDACTED]',['hotatbanitamimgeneralhospital','hotatbanitamimhospital']),
 (HOSP,'[NAME-REDACTED]',['albashaierhospital','albashaerhospital','bashaierhospital']),
 (HOSP,"[NAME-REDACTED]",['haildentalcenter','haildentalcentre']),
 # --- military & security-forces named facilities ---
 (MIL,'Prince Sultan Military Medical City',['princesultanmilitary','psmmc']),
 (MIL,'[NAME-REDACTED]',['kingfahdmilitary','kingfahadmilitary','kingfahdmilitarymedicalcomplex']),
 (MIL,'[NAME-REDACTED]',['princesultanmilitarycollege']),
 (MIL,'Security Forces Hospital',['securityforceshospital','securityforcehospital','securityforceshospitalprogram']),
 (MIL,'[NAME-REDACTED]',['princemansourmilitary']),
 (MIL,'King Salman Armed Forces Hospital',['kingsalmanarmedforces']),
 (MIL,'[NAME-REDACTED]',['kingfahdarmedforces','kingfahadarmedforces','kingfahdarmoredforces','kingfahadarmoredforces']),
 (MIL,'Armed Forces Hospital',['armedforceshospital','armedforcesmedicalservices','armedforceshospitals','northernareaarmedforces']),
 (MIL,'[NAME-REDACTED]',['jafh']),
 (MIL,'[NAME-REDACTED]',['royalsaudilandforces','royalsaudiairforce','royalsaudiairforces']),
 (MIL,'[NAME-REDACTED]',['airbasehospital']),
 (MIL,'[NAME-REDACTED]',['specialsecurityforces']),
 # --- research centres / institutes (standalone) ---
 (RES,'King Abdullah International Medical Research Center',['kingabdullahinternationalmedicalresearch','kaimrc']),
 (RES,'Center for Outcomes Research in Liver Disease',['outcomesresearchinliver']),
 (RES,'[NAME-REDACTED]',['autismresearchandtreatment']),
 # --- government authorities / agencies ---
 (AUTH,'Saudi Food & Drug Authority',['saudifoodanddrug','foodanddrugauthority','sfda']),
 (AUTH,'[NAME-REDACTED]',['saudicenterfordisease','saudicentrefordisease','centerfordiseasepreventionandcontrol','weqaya','publichealthauthority','saudicenterfordiseasecontrol']),
 (AUTH,'General Authority for Statistics',['generalauthorityforstatistics','gastat']),
 (AUTH,'Saudi Data & AI Authority',['saudidataandai','sdaia']),
 (AUTH,'[NAME-REDACTED]',['cbahi','centralboardforaccreditation']),
 # --- councils / commissions ---
 (COUN,'Saudi Health Council',['saudihealthcouncil']),
 (COUN,'Saudi Commission for Health Specialties',['saudicommissionforhealth','scfhs']),
 (COUN,'[NAME-REDACTED]',['saudiboardof','saudiboard']),
 # --- companies / industry ---
 (CO,'Johns Hopkins Aramco Healthcare / Saudi Aramco',['aramco','jhah','johnshopkinsaramco']),
 (CO,'SABIC',['sabic']),
 (CO,'[NAME-REDACTED]',['nupco','nationalunifiedprocurement']),
 (CO,'MED-EL',['medel']),
 # --- other named employers (not health facilities, but named) ---
 (SOC,'[NAME-REDACTED]',['alhilalfootballclub','alhilalsaudifootballclub']),
]

# ---------------- Tier 2: umbrella ministries / health systems ----------------
TIER2 = [
 # 'moh' REMOVED from the compact aliases 2026-08-23: compact matching strips all
 # punctuation, so a bare 'moh' matched inside "Mohammed" / "Almohandes" and typed two
 # Prince-Mohammed hospitals as Ministry of Health. The abbreviation is now matched as
 # a whole word on the spaced text instead -- see _moh_badge().
 (MOH,'Ministry of Health',['ministryofhealth','saudiministryofhealth','ministryofhealthofsaudiarabia','ministryofhealthclinics']),
 (MOH,'[NAME-REDACTED]',['healthcluster']),
 (MOH,'Primary health care (MoH)',['primaryhealthcare','primaryhealthcarecenter','primaryhealthcarecentre']),
 (MIL,'[NAME-REDACTED]',['ministryofnationalguard','nationalguardhealth','nationalguardhealthaffairs','ministryofthenationalguard','nationalguardshealthaffairs','mngha']),
 (MIL,'[NAME-REDACTED]',['ministryofdefence','ministryofdefense']),
 (MIL,'Ministry of Interior',['ministryofinterior']),
 (GOV,'[NAME-REDACTED]',['ministryofeducation']),
 (GOV,'[NAME-REDACTED]',['healthsectortransformation']),
 (GOV,'General government / ministry',['ministryof']),
]

# ---------------- Tier 3: keyword fallback (on normalized spaced text) ----------------
def _tier3(n):
    # order matters: military hospitals before generic hospital; hospital/university before company;
    # company requires a strong industry token (NOT bare 'pharmaceutical', which flags clinical
    # 'pharmaceutical care' departments inside hospitals).
    if re.search(r'\bmilitar|armed forces|armored forces|security forces|national guard|air ?base', n): return MIL,'(military, unnamed)'
    if re.search(r'ministry of health', n): return MOH,'(MoH, unnamed)'
    if re.search(r'\bauthority\b', n): return AUTH,'(authority, unnamed)'
    if re.search(r'\bcouncil\b|\bcommission\b', n): return COUN,'(council, unnamed)'
    if re.search(r'\buniversit|\bcollege(s)?\b|\bfaculty\b', n): return UNIV,'(university/college, unnamed)'
    if re.search(r'medical city|\bhospital\b|medical complex|medical group|medical center|medical centre|\bpolyclinic|\bclinic\b|health cluster|health centre|health center|maternity|therapy cent|rehabilitation cent', n): return HOSP,'(hospital/clinic, unnamed)'
    if re.search(r'primary health', n): return MOH,'(PHC, unnamed)'
    if re.search(r'research (cent(er|re)|institut)|\binstitute\b', n): return RES,'(research centre, unnamed)'
    if re.search(r'\bsociety\b|\bassociation\b|\bcharit|\bfoundation\b', n): return SOC,'(society/NGO, unnamed)'
    if re.search(r'\bgmbh\b|\bl\.?l\.?c\b|\binc\b|\bltd\b|\bcorp\b|\bcompany\b|\bcompanies\b|\bpharmaceuticals\b|\bindustries\b|\bfactory\b', n): return CO,'(company, unnamed)'
    if re.search(r'\bministry\b|\bgeneral directorate\b|\bdirectorate of health\b', n): return GOV,'(government, unnamed)'
    # Not a missing name: these authors state that they have no institution. Say so,
    # rather than printing "(unspecified)" as though the affiliation were incomplete.
    if re.search(r'private practice|independent researcher|independent scholar|freelance', n):
        return OTH,'[NAME-REDACTED]'
    return OTH,'(unspecified)'

def _rightmost(compact, tier):
    best=None; best_pos=-1; best_len=0
    for typ,canon,aliases in tier:
        for al in aliases:
            i=compact.rfind(al)
            if i>=0 and (i>best_pos or (i==best_pos and len(al)>best_len)):
                best_pos=i; best_len=len(al); best=(typ,canon)
    return best

_MOH_BADGE = re.compile(r'ministry of health|\bmoh\b')


def _moh_badge(n):
    """True if the block carries an explicit MoH badge -- the spelled-out ministry, a
    parenthesised (MOH), or an @moh.gov.sa address. Whole-word only, so 'Mohammed'
    does not count."""
    return bool(_MOH_BADGE.search(n))


def classify(block):
    """Return (type, institution, tier) for one Saudi affiliation block."""
    compact=_compact(block); n=_norm(block)
    m=_rightmost(compact, TIER1)
    # RULING (adjustable): the named institution wins and the SECTOR follows it, even
    # when the block also carries a Ministry-of-Health badge -- "[NAME-REDACTED],
    # Ministry of Health, Riyadh" is a hospital that MoH runs, and it has always been
    # typed Hospital here. MoH ownership is a governance fact, not the sector.
    # Making the badge override the sector was tried on 2026-08-23 and rejected: it
    # silently retyped hospitals that were already correct.
    if m: return m[0], m[1], 1
    m=_rightmost(compact, TIER2)
    if m: return m[0], m[1], 2
    if _moh_badge(n): return MOH,'Ministry of Health',2
    typ,canon=_tier3(n)
    return typ, canon, 3

TYPE_ORDER=[UNIV,HOSP,HOSPRES,MIL,MOH,GOV,AUTH,COUN,RES,CO,SOC,OTH]
