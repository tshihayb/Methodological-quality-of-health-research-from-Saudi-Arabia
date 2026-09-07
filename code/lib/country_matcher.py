# NOTE (public repository): 11 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
"""Comprehensive affiliation -> country classifier. Rightmost-match strategy."""
import re, unicodedata

def _norm(s):
    # strip accents, lowercase, collapse whitespace
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.lower()

# ---- Country patterns: canonical -> list of regex-safe variant strings ----
# Order matters only within a country; across countries we pick the RIGHTMOST match.
COUNTRY_VARIANTS = {
    'Saudi Arabia': ['saudi arabia', 'kingdom of saudi arabia', 'ksa', r'k\.s\.a', 'saudia arabia',
                     'saudi araba', 'saudi arbia'],
    'United States': ['united states of america', 'united states', r'u\.s\.a', 'usa', r'u\.s\b'],
    'United Kingdom': ['united kingdom', r'u\.k\b', 'uk', 'england', 'scotland', 'wales', 'northern ireland',
                       'great britain'],
    'United Arab Emirates': ['united arab emirates', 'uae', r'u\.a\.e', 'abu dhabi', 'dubai', 'sharjah', 'ajman'],
    'Egypt': ['egypt'],
    'Italy': ['italy', 'italia'],
    'India': ['india'],
    'Pakistan': ['pakistan'],
    'Nigeria': ['nigeria'],
    'Australia': ['australia'],
    'Turkey': ['turkey', 'turkiye', 'turkey.'],
    'Malaysia': ['malaysia'],
    'China': ['china', "people's republic of china", 'pr china', 'p.r. china'],
    'France': ['france'],
    'Tunisia': ['tunisia', 'tunisie'],
    'Canada': ['canada'],
    'Greece': ['greece', 'hellas'],
    'Iran': ['iran', 'islamic republic of iran'],
    'Germany': ['germany', 'deutschland'],
    'Jordan': ['jordan'],
    'Poland': ['poland', 'polska'],
    'Bangladesh': ['bangladesh'],
    'Spain': ['spain', 'espana'],
    'Finland': ['finland'],
    'Sweden': ['sweden'],
    'Brazil': ['brazil', 'brasil'],
    'Netherlands': ['the netherlands', 'netherlands'],
    'Lebanon': ['lebanon'],
    'Kuwait': ['kuwait'],
    'Ireland': ['ireland'],
    'Qatar': ['qatar'],
    'Japan': ['japan'],
    'Sudan': ['sudan'],
    'Austria': ['austria'],
    'Russia': ['russia', 'russian federation'],
    'Ghana': ['ghana'],
    'Vietnam': ['vietnam', 'viet nam'],
    'Iraq': ['iraq'],
    'Israel': ['israel'],
    'Philippines': ['philippines'],
    'Ethiopia': ['ethiopia'],
    'Oman': ['oman', 'sultanate of oman'],
    'New Zealand': ['new zealand'],
    'South Korea': ['south korea', 'republic of korea', r'korea, republic', 'korea'],
    'Palestine': ['palestine', 'palestinian'],
    'Yemen': ['yemen', 'republic of yemen'],
    'Morocco': ['morocco', 'maroc'],
    'Romania': ['romania'],
    'South Africa': ['south africa'],
    'Thailand': ['thailand'],
    'Denmark': ['denmark'],
    'Belgium': ['belgium', 'belgiumand'],
    'Mexico': ['mexico'],
    'Ukraine': ['ukraine'],
    'Portugal': ['portugal'],
    'Colombia': ['colombia'],
    'Bahrain': ['bahrain'],
    'Singapore': ['singapore'],
    'Croatia': ['croatia'],
    'Norway': ['norway'],
    'Indonesia': ['indonesia'],
    'Chile': ['chile'],
    'Slovenia': ['slovenia'],
    'Switzerland': ['switzerland'],
    'Nepal': ['nepal'],
    'Luxembourg': ['luxembourg'],
    'Somalia': ['somalia'],
    'Peru': ['peru'],
    'Syria': ['syria', 'syrian arab republic'],
    'Iceland': ['iceland'],
    'Kenya': ['kenya'],
    'Paraguay': ['paraguay'],
    'Hong Kong': ['hong kong'],
    'North Macedonia': ['north macedonia', 'macedonia'],
    'Albania': ['albania'],
    'Botswana': ['botswana'],
    'Algeria': ['algeria', 'algerie'],
    'Uganda': ['uganda'],
    'Georgia': [r'\bgeorgia\b'],  # country; disambiguated below vs US state
    'Czech Republic': ['czech republic', 'czechia'],
    'Hungary': ['hungary'],
    'Serbia': ['serbia'],
    'Bulgaria': ['bulgaria'],
    'Slovakia': ['slovakia', 'slovak republic'],
    'Cyprus': ['cyprus'],
    'Estonia': ['estonia'],
    'Latvia': ['latvia'],
    'Lithuania': ['lithuania'],
    'Taiwan': ['taiwan'],
    'Sri Lanka': ['sri lanka'],
    'Libya': ['libya'],
    'Cameroon': ['cameroon', 'cameroun'],
    'Tanzania': ['tanzania'],
    'Zimbabwe': ['zimbabwe'],
    'Zambia': ['zambia'],
    'Rwanda': ['rwanda'],
    'Senegal': ['senegal'],
    'Ivory Coast': ["cote d'ivoire", 'ivory coast'],
    'Mali': ['mali'],
    'Malawi': ['malawi'],
    'Mozambique': ['mozambique'],
    'Argentina': ['argentina'],
    'Venezuela': ['venezuela'],
    'Ecuador': ['ecuador'],
    'Bolivia': ['bolivia'],
    'Uruguay': ['uruguay'],
    'Cuba': ['cuba'],
    'Costa Rica': ['costa rica'],
    'Panama': ['panama'],
    'Guatemala': ['guatemala'],
    'Afghanistan': ['afghanistan'],
    'Kazakhstan': ['kazakhstan'],
    'Uzbekistan': ['uzbekistan'],
    'Azerbaijan': ['azerbaijan'],
    'Armenia': ['armenia'],
    'Mongolia': ['mongolia'],
    'Myanmar': ['myanmar', 'burma'],
    'Cambodia': ['cambodia'],
    'Laos': ['laos'],
    'Brunei': ['brunei'],
    'Maldives': ['maldives'],
    'Bhutan': ['bhutan'],
    'Mauritius': ['mauritius'],
    'Madagascar': ['madagascar'],
    'Angola': ['angola'],
    'Namibia': ['namibia'],
    'Gabon': ['gabon'],
    'Benin': ['benin'],
    'Burkina Faso': ['burkina faso'],
    'Niger': [r'\bniger\b'],
    'Togo': ['togo'],
    'Congo': ['democratic republic of the congo', 'dr congo', r'\bcongo\b'],
    'Malta': ['malta'],
    'Montenegro': ['montenegro'],
    'Bosnia and Herzegovina': ['bosnia and herzegovina', 'bosnia'],
    'Kosovo': ['kosovo'],
    'Moldova': ['moldova'],
    'Belarus': ['belarus'],
    'Kyrgyzstan': ['kyrgyzstan'],
    'Tajikistan': ['tajikistan'],
    'Turkmenistan': ['turkmenistan'],
    'Fiji': ['fiji'],
    'Papua New Guinea': ['papua new guinea'],
    'Jamaica': ['jamaica'],
    'Trinidad and Tobago': ['trinidad'],
    'Dominican Republic': ['dominican republic'],
    'Haiti': ['haiti'],
    'Honduras': ['honduras'],
    'Nicaragua': ['nicaragua'],
    'El Salvador': ['el salvador'],
    'Puerto Rico': ['puerto rico'],
    'New Caledonia': ['new caledonia'],
}

# ---- Fallback dictionaries (used only when no explicit country matched) ----
# Saudi cities + unambiguous Saudi institution keywords (for segments naming only a city/uni).
SAUDI_CITIES = ['riyadh','jeddah','jiddah','makkah','mecca','madinah','medina','dammam','khobar',
    'al khobar','dhahran','taif','tabuk','abha','jazan','jizan','hail',"ha'il",'buraidah','buraydah',
    'hofuf','al-ahsa','alahsa','al-hasa','al ahsa','najran','jubail','yanbu','qassim','al-qassim',
    'skaka','sakaka','aljouf','al-jouf','arar','khamis mushait','bisha','unaizah','onaizah','alharj',
    'al-kharj','kharj','wadi al-dawasir','rabigh','al-baha','baha']
SAUDI_INSTITUTIONS = ['king saud','king abdulaziz','king abdul aziz','king abdullah','king faisal',
    'king khalid','king fahd','imam abdulrahman','imam muhammad ibn saud','imam mohammad ibn saud',
    'al-imam muhammad','prince sattam','prince sultan','princess nourah','princess nora','umm al-qura',
    'umm al qura','taibah univ','qassim univ','najran univ','jazan univ','jouf univ','university of hail',
    'university of tabuk','university of bisha','kfshrc','king faisal specialist','kaust',
    'saudi food and drug','ministry of health, riyadh','ngha','national guard health']
# Curated city -> country for city-only segments that appear in the corpus.
CITY_COUNTRY = {
    'minneapolis':'United States','cambridge':'United States','boston':'United States',
    'cairo':'Egypt','buenos aires':'Argentina','sao paulo':'Brazil','montevideo':'Uruguay',
    'medellin':'Colombia','basel':'Switzerland','vienna':'Austria','graz':'Austria',
    'parkville':'Australia','sydney':'Australia','leuven':'Belgium',
}
# Email country-code TLD -> country (last resort; only 2-letter ccTLDs that are unambiguous).
CCTLD_COUNTRY = {
    'sa':'Saudi Arabia','au':'Australia','at':'Austria','ch':'Switzerland','co':'Colombia',
    'uy':'Uruguay','br':'Brazil','eg':'Egypt','uk':'United Kingdom','ca':'Canada','de':'Germany',
    'fr':'France','it':'Italy','es':'Spain','nl':'Netherlands','se':'Sweden','fi':'Finland',
    'no':'Norway','dk':'Denmark','pl':'Poland','gr':'Greece','tr':'Turkey','ir':'Iran','in':'India',
    'pk':'Pakistan','ng':'Nigeria','my':'Malaysia','cn':'China','jp':'Japan','kr':'South Korea',
    'jo':'Jordan','kw':'Kuwait','qa':'Qatar','ae':'United Arab Emirates','om':'Oman','bh':'Bahrain',
    'lb':'Lebanon','ye':'Yemen','iq':'Iraq','ps':'Palestine','sd':'Sudan','ma':'Morocco','tn':'Tunisia',
    'dz':'Algeria','ie':'Ireland','pt':'Portugal','ru':'Russia','ua':'Ukraine','za':'South Africa',
    'gh':'Ghana','et':'Ethiopia','ke':'Kenya','ug':'Uganda','bd':'Bangladesh','lk':'Sri Lanka',
    'np':'Nepal','id':'Indonesia','th':'Thailand','vn':'Vietnam','ph':'Philippines','tw':'Taiwan',
    'hk':'Hong Kong','sg':'Singapore','nz':'New Zealand','mx':'Mexico','cl':'Chile','pe':'Peru',
    'ro':'Romania','hu':'Hungary','cz':'Czech Republic','be':'Belgium','hr':'Croatia','si':'Slovenia',
    'rs':'Serbia','bg':'Bulgaria','sk':'Slovakia','ee':'Estonia','lv':'Latvia','lt':'Lithuania',
    'is':'Iceland','cy':'Cyprus','mt':'Malta','il':'Israel','ly':'Libya','sy':'Syria',
}

# US states (full + 2-letter) -> map to United States. Applied only if no explicit country found.
US_STATES_FULL = ['alabama','alaska','arizona','arkansas','california','colorado','connecticut',
    'delaware','florida','georgia','hawaii','idaho','illinois','indiana','iowa','kansas','kentucky',
    'louisiana','maine','maryland','massachusetts','michigan','minnesota','mississippi','missouri',
    'montana','nebraska','nevada','new hampshire','new jersey','new mexico','new york','north carolina',
    'north dakota','ohio','oklahoma','oregon','pennsylvania','rhode island','south carolina',
    'south dakota','tennessee','texas','utah','vermont','virginia','washington','west virginia',
    'wisconsin','wyoming','district of columbia']
US_STATE_ABBR = {'al','ak','az','ar','ca','co','ct','de','fl','ga','hi','id','il','in','ia','ks','ky',
    'la','me','md','ma','mi','mn','ms','mo','mt','ne','nv','nh','nj','nm','ny','nc','nd','oh','ok','or',
    'pa','ri','sc','sd','tn','tx','ut','vt','va','wa','wv','wi','wy','dc'}
# common informal US abbreviations sometimes used
US_STATE_ABBR_EXTRA = {'mass','calif','conn','fla','tex','wis','minn','okla'}

# Build compiled rightmost-search patterns.
_compiled = []
for canon, variants in COUNTRY_VARIANTS.items():
    for v in variants:
        # if variant already contains \b it's a raw regex; else wrap with boundaries
        if r'\b' in v:
            pat = v
        else:
            pat = r'\b' + re.escape(v).replace(r'\ ', ' ') + r'\b'
        _compiled.append((canon, re.compile(pat)))

def _strip_email(seg):
    # remove 'Electronic address: ...' and bare emails
    seg = re.sub(r'electronic address\s*:.*$', '', seg, flags=re.I)
    seg = re.sub(r'\S+@\S+', '', seg)
    return seg

def _cctld_from_email(raw):
    m = re.findall(r'\S+@\S+', raw)
    if not m: return None
    dom = m[-1].rstrip('.').split('@')[-1].lower()
    tld = dom.rsplit('.', 1)[-1] if '.' in dom else ''
    return CCTLD_COUNTRY.get(tld)

def detect_country_segment(seg):
    """Return (canonical_country, method) for ONE affiliation segment, or (None,'none')."""
    raw = seg
    seg = _strip_email(seg)
    n = _norm(seg)
    # 1) rightmost explicit-country match
    best = None; best_pos = -1
    for canon, rx in _compiled:
        for m in rx.finditer(n):
            if m.start() > best_pos:
                best_pos = m.start(); best = canon
    # Disambiguate Georgia: if 'georgia' matched but a US signal is present, treat as US
    if best == 'Georgia':
        if re.search(r'\b(ga|usa|u\.s\.a|united states)\b', n) or re.search(r'atlanta|emory|augusta', n):
            best = 'United States'
    if best is not None:
        return best, 'explicit'
    # 2) US full-state-name fallback
    for name in US_STATES_FULL:
        if re.search(r'\b'+re.escape(name)+r'\b', n):
            return 'United States', 'us-state-full'
    # 3) US 2-letter / informal abbrev near tail (strip surrounding punctuation from tokens)
    toks = [re.sub(r'[^a-z]', '', t) for t in re.split(r'[,\s;]+', n)]
    toks = [t for t in toks if t]
    for t in reversed(toks[-5:]):
        if t in US_STATE_ABBR or t in US_STATE_ABBR_EXTRA:
            return 'United States', 'us-state-abbr'
    # 4) Saudi institution / city fallback
    if any(k in n for k in SAUDI_INSTITUTIONS) or any(re.search(r'\b'+re.escape(c)+r'\b', n) for c in SAUDI_CITIES):
        return 'Saudi Arabia', 'saudi-inst-city'
    # 5) curated city -> country
    for city, ctry in CITY_COUNTRY.items():
        if re.search(r'\b'+re.escape(city)+r'\b', n):
            return ctry, 'city'
    # 6) email ccTLD last resort
    c = _cctld_from_email(raw)
    if c:
        return c, 'email-cctld'
    return None, 'none'

# Manual overrides for authors whose ONLY affiliation is a truncated fragment,
# resolved from within-paper institutional context (co-authors' affiliations).
MANUAL_AUTHOR_COUNTRY = {
    ('STUDY-0731', 'Baek'): 'South Korea',     # Seoul National Univ orthodontics (co-authors Kim/Ha/Choi, SNU)
    ('STUDY-0531', 'Abusrair'): 'Saudi Arabia',# KFSHRC Riyadh Dept of [NAME-REDACTED] (co-author AlHamoud)
    ('STUDY-0531', 'Bohlega'): 'Saudi Arabia', # KFSHRC Riyadh Dept of [NAME-REDACTED]
    # --- added 2026-08-23, from validating S1/S2 against the full texts ---
    # PubMed gives no country ("University of Benin Teaching Hospital, PMB 1111"), so the
    # matcher matched the country name INSIDE the university name. The paper's affiliation
    # 6 reads "University of Benin Teaching Hospital, Benin, Nigeria" -- Benin City is in
    # Nigeria, a different country from Benin.
    ('STUDY-0393', 'Bazuaye'): 'Nigeria',
    # PubMed says "Orthopedic Surgery Department, Jeddah National Hospital, Jeddah, Saudi
    # Arabia"; the published paper (JPMA 72:2223, DOI [DOI-REDACTED]) gives affiliation
    # 4 as "Department of Orthopedic, Liaquat College of Medicine and Dentistry, Karachi,
    # Pakistan". TSA ruled 2026-08-23 that the PAPER wins over PubMed.
    ('STUDY-0928', 'Azfar'): 'Pakistan',

    # --- added 2026-08-24, from the 385-paper hand-read of the author->affiliation
    # linkage (docs/provenance/08_23_2026_handread_linkage.md). Values may now be a LIST
    # for dual-country authors; the first entry is the primary affiliation.
    #
    # STUDY-0821 -- PubMed's affiliation for the Center for Outcomes Research in Liver
    # Disease is CORRUPT: "Center for Outcomes Research in Liver Disease, Washington
    # District of Columbia, Riyadh, Saudi Arabia". CORLD is a Washington DC entity; the
    # "Riyadh, Saudi Arabia" is spliced in from elsewhere. Because detect_country_segment
    # takes the RIGHTMOST country, four DC-based authors were labelled Saudi. The paper
    # prints no Saudi address for any of them. ⚠ This is the ONLY known case of S1
    # OVER-counting Saudi -- every other error runs the other way.
    # The paper keeps 2 genuinely Saudi authors (Alswat/King Saud U, Alqahtani/KFSHRC),
    # so its inclusion is unaffected.
    ('STUDY-0821', 'Ziayee'): 'United States',
    ('STUDY-0821', 'Henry'): 'United States',
    ('STUDY-0821', 'Stepanova'): 'United States',
    ('STUDY-0821', 'Ong'): ['Philippines', 'United States'],

    # STUDY-0715 -- PubMed joined two affiliations with ". " instead of "; ", so
    # detect_country (which splits only on '|' and ';') saw one block ending in
    # "Baltimore, MD, USA" and the rightmost rule swallowed the Saudi one. The paper
    # prints "Johns Hopkins Aramco Healthcare, Dhahran, Saudi Arabia" as affiliation 1.
    # Corpus-wide this mechanism affects exactly 1 of 3,457 authors.
    ('STUDY-0715', 'Al-Tawfiq'): ['Saudi Arabia', 'United States'],

    # STUDY-0094 -- PubMed jams two institutions into one string: "Department of Preventive
    # Dental Sciences, Saudi Arabia Department of Health Promotion, ... Jazan University,
    # Maastricht University, Maastricht, Netherlands". Rightmost rule kept Netherlands and
    # lost Saudi Arabia. The paper gives affiliation 13 as Jazan University, Saudi Arabia.
    # TSA ruled 2026-08-24 to record all three.
    ('STUDY-0094', 'Jafer'): ['Nigeria', 'Saudi Arabia', 'Netherlands'],

    # STUDY-0393 -- 'de' is the US state abbreviation for DELAWARE and the commonest
    # preposition in Spanish institution names, so "Instituto de Prevision Social,
    # Asuncion" resolved to United States. The paper gives both authors the LABMT
    # secretariat in Bern plus their home institution. TSA ruled 2026-08-24 to record both.
    ('STUDY-0393', 'Frutos'): ['Switzerland', 'Paraguay'],
    ('STUDY-0393', 'Karduss'): ['Switzerland', 'Colombia'],

    # ⚠⚠ STUDY-0468 Fanikos -- THE ONE CASE WHERE THE PAPER **AND** PUBMED ARE BOTH WRONG.
    # The published byline prints affiliation marker "1" (Qassim University) against Ting,
    # Fanikos AND Buckley. PubMed corrects Ting and Buckley to Brigham and Women's Hospital
    # but inherits the error for Fanikos, listing him at "Department of Pharmacy Practice,
    # College of Pharmacy, Qassim University, Qassim, Saudi Arabia".
    # John Fanikos is Executive Director of Pharmacy at Brigham and Women's Hospital,
    # Boston, where he has worked for ~40 years (brighamandwomens.org; thrombosis.org).
    #
    # The hand-read did NOT flag this: the reader recorded what the page prints, PubMed
    # says the same, so the two "agreed" -- but they are not independent, because PubMed's
    # record descends from that same byline. Agreement between two sources sharing a common
    # ancestor is not corroboration.
    #
    # PRECEDENCE RULING (TSA, 2026-08-24): verified external institutional evidence beats
    # BOTH the paper and PubMed when the two share the byline as their common source. This
    # sits one tier above the standing "the paper beats PubMed" rule (STUDY-0928).
    # Effect: Saudi appearances 1,520 -> 1,519; STUDY-0468 goes 4/8 -> 3/8, so its
    # pct_saudi_ge50 flips '>=50%' -> '<50%'. The paper keeps 3 Saudi authors (Alahmed,
    # Aldemerdash, Fatani), so its inclusion is unaffected.
    ('STUDY-0468', 'Fanikos'): 'United States',

    # STUDY-0519 Abdelwahid -- ONE block naming TWO institutions in two countries:
    # "[NAME-REDACTED] (JAFH), Suez Canal University, Ismailia, Egypt."
    # The rightmost-country rule takes Egypt and drops the Saudi half. The SAME PAPER
    # states three times that JAFH is Saudi: authors 2, 3 and 4 all read "JAFH, Jazan,
    # Saudi Arabia". Under the any-affiliation convention he holds both; JAFH is printed
    # first, so Saudi Arabia is primary.
    # Same failure family as STUDY-0715 Al-Tawfiq and STUDY-0094 Jafer.
    # ⚠ The hand-read did NOT flag this: the reader transcribed the string as printed and
    # the classifier gave Egypt for both sides, so reader and S1 "agreed". It surfaced only
    # through the wide-vs-S1 stratifier screen, which said first_author_saudi should be 1.
    ('STUDY-0519', 'Abdelwahid'): ['Saudi Arabia', 'Egypt'],

    # --- added 2026-08-24 from the S2 sweep (screens E/E2), TSA ruled to apply ---
    # Two more of the same family: ONE segment naming a foreign and a Saudi institution,
    # joined by the word "and" rather than by '|' or ';', so the rightmost-country rule
    # keeps one and silently drops the other. Here it drops the FOREIGN half, so neither
    # author's Saudi status changes and no stratifier moves -- but under the settled
    # any-affiliation convention each holds two countries, and Suppl. Fig. S1 was
    # under-counting the United States and Egypt by one appearance each.
    # ⚠ Both are mid-byline authors (idx 3 of 5, idx 8 of 10), so making the foreign
    # affiliation PRIMARY -- as the print order requires -- touches nothing: the only
    # consumers of primary_country are the first/last-author summaries.
    #
    # STUDY-0945: "Rayyan Bukhari, MSOT, is PhD Student, Department of Occupational Therapy,
    # Colorado State University, Fort Collins, AND Lecturer, Department of Occupational
    # Therapy, King Saud bin Abdulaziz University for Health Sciences, Jeddah, Saudi Arabia."
    ('STUDY-0945', 'Bukhari'): ['United States', 'Saudi Arabia'],
    # STUDY-0793: "Medical Surgical Nursing, College of Nursing Tanta University, Egypt AND
    # College of Nursing, Mahalah Branch for Girls King Khalid University, Asir, Saudi Arabia"
    ('STUDY-0793', 'Ahmed'): ['Egypt', 'Saudi Arabia'],
}

def detect_country(aff):
    """For a full affiliation string, return (primary_country, [all_countries_in_order]).

    Affiliation blocks are split on BOTH '|' (PubMed's join of separate <Affiliation>
    elements) and ';' (multiple institutions inside one element). Within each block the
    RIGHTMOST country wins (a block is one institution whose country sits at the end,
    e.g. 'China Medical University, Taichung, Taiwan' -> Taiwan, not China). The PRIMARY
    country is that of the FIRST block that resolves (the first-listed affiliation)."""
    if not aff or not aff.strip():
        return None, []
    blocks = re.split(r'\s*[|;]\s*', aff)
    countries = []
    for b in blocks:
        if not b.strip():
            continue
        c, _ = detect_country_segment(b)
        if c:
            countries.append(c)
    primary = countries[0] if countries else None
    # ordered unique
    seen = set(); allc = []
    for c in countries:
        if c not in seen:
            seen.add(c); allc.append(c)
    return primary, allc
