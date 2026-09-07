# -*- coding: utf-8 -*-
# Rule-based first-pass classifier for the 310 ADJUDICATED (descriptive+causal) outcomes ->
# 12 categories in 4 domains, plus a residual OTHER. The 75 predictive outcomes do NOT pass
# through here; they are categorised by the model that determines them (see aggregate script).
# Decision order (first match wins) per docs/methods/08_08_2026_outcome_categorization_codebook.md.
import csv, re, sys, io

CATLAB={
 "1.1":"Mortality & survival","1.2":"Disease occurrence / diagnosis",
 "1.3":"Severity, progression, complications & safety","1.4":"Physiological, lab & imaging measures",
 "1.5":"Treatment / procedure response & success","2.1":"Clinical, functional & symptom scales (incl. QoL)",
 "2.2":"Mental health & psychological status","2.3":"Satisfaction & care experience",
 "3.1":"Knowledge & awareness","3.2":"Attitudes, perceptions & willingness",
 "3.3":"Health behaviors, practices & adherence","4.1":"Utilization, cost, process & workforce","OTHER":"OTHER (manual)"}
DOMAIN={"1.1":"1 Clinical/biomedical","1.2":"1 Clinical/biomedical","1.3":"1 Clinical/biomedical","1.4":"1 Clinical/biomedical","1.5":"1 Clinical/biomedical",
 "2.1":"2 Patient-reported/functional","2.2":"2 Patient-reported/functional","2.3":"2 Patient-reported/functional",
 "3.1":"3 Knowledge/attitudes/behaviors","3.2":"3 Knowledge/attitudes/behaviors","3.3":"3 Knowledge/attitudes/behaviors",
 "4.1":"4 Health-system/process","OTHER":"OTHER"}

# Manual overrides (reviewed judgment) applied BEFORE the rules. Keyed on the outcome text.
# EXACT = full (normalized, lowercased) match; SUB = normalized-substring match. Exact wins.
EXACT_OVR={
 "weight":"1.4","fever":"1.2","stroke":"1.2","tumor":"1.2","covid-19":"1.2","anemia":"1.2",
 "dental trauma":"1.2","microalbuminuria":"1.2","hyponatremia":"1.2",
 "body mass index (bmi)":"1.4","bmi status":"1.4","categorical bmi":"1.4","weight loss":"1.3",
}
SUB_OVR={
 # -> from OTHER
 "sharing incidents":"3.3","pattern reversal visual":"1.4","composite scores on ssi-4":"2.1",
 "hematopoietic cell transplantation":"1.5","maximum isometric muscle strength":"1.4",
 "conduction defects requiring permanent pacemaker":"1.3","overall performance (skills)":"2.1",
 "unconjugated estrone":"1.4","c-reactive protein":"1.4","complete clearance or residual fragments":"1.5",
 "urninary excretion of total flavanone":"1.4","externalizing behavior":"2.2",
 "receipt of coronary revascularization":"4.1","risk of hypertensive events":"1.2","viral dysbiosis":"1.4",
 "ohrqol using ohip-14":"2.1","body weight change":"1.4","screen time":"3.3","emotional over eating":"3.3",
 "health care seeking behavior":"3.3","muscle protein synthesis":"1.4","cd4+cd25":"1.4","interleukin-6":"1.4",
 "skipping breakfast":"3.3","structural empowerment":"4.1","cutaneous manifestations post-vaccination":"1.3",
 "skeletal classification sna":"1.4","on-scene time":"4.1","distance from upper posterior teeth":"1.4",
 "difficulty obtaining an accurate patient history":"4.1","organizational citizenship behavior":"4.1",
 "polyethylene liner size":"1.4","videogame disorder":"2.2","physical component summaries":"2.1",
 "tower of hanoi":"2.1","seizure frequency":"1.3","hsv-1 quantification":"1.4","dynamic limit of stability":"2.1",
 "social life domain of the beutyqol":"2.1","skin prick testing":"1.4","spheno-occipital synchondrosis":"1.4",
 "adjacent teeth root resorption":"1.3","baby-friendly designation":"4.1","non-strabismic binocular vision":"1.2",
 "synchronous vs":"1.2","cervical joint position sense":"2.1","obese vs. normal weight":"1.2",
 "intercanine within in mixed dentition":"1.4","hip flexors muscle strength":"1.4",
 "academic achievement using gpa":"2.1","white matter hyperintensities":"1.4","traumatic brain injury":"1.2",
 "common online tool":"3.3","lymph node metastasis":"1.3",
 # -> fix rule errors among matched rows
 "surveyed urban environments reduces the risk":"3.2","affect your choice of specialty":"3.2",
 "my child is doing physical activities":"3.3","covid-19 related fear":"2.2",
 "development of primary open-angle glaucoma":"1.2","psychiatric ed visits":"4.1",
 "out-of-pocket health expenditure":"4.1","body mass index-for-age z-score":"1.4",
 "covid-19 status (testing positive":"1.2","postoperative cognitive dysfunction":"1.2",
 "persistent dysplasia defined by an acetabular":"1.2","ohrqol using child perception questionnaire":"2.1",
 "perceived exertion rating":"2.1","prevalence of ophthalmic symptoms":"1.2",
 "prevalence of metformin use":"3.3","dietary-quality score":"3.3","hepatocellular":"1.2",
}

DISEASE=r"(stroke|tuberculosis|\btb\b|covid|sars-cov|malaria|mrsa|candidias|candida|epilepsy|dyslipidemia|dyslipidaemia|preterm|low birth weight|thrombosis|nocardiosis|carcinoma|cancer|tumou?r|carie|caries|[NAME-REDACTED]|hypertension|diabet|obesit|anaemia|anemia|microalbumin|nocardios|helicobacter|pylori|cirrhosis|metabolic syndrome|copd|asthma|melanoma|[NAME-REDACTED]|leukaemia|sepsis|pneumonia|hepatitis)"

def _norm(t):
    return re.sub(r'\s+',' ',(t or '').strip().lower())

def classify(t):
    s=t.lower()
    n=_norm(t)
    if n in EXACT_OVR: return EXACT_OVR[n]
    for k,v in SUB_OVR.items():
        if k in n: return v
    def has(p): return re.search(p,s) is not None
    # 1 mortality/survival
    if has(r"mortalit|death|died|fatal|survival|stillbirth|perinatal death|case[- ]fatal|overall survival|\bos\b|recurrence[- ]free surviv|\brfs\b"):
        return "1.1"
    # 2 knowledge
    if has(r"knowledge|awareness|\baware\b|heard about|heard of|knowing|know what|reasons for tooth"):
        return "3.1"
    # 3 mental health
    if has(r"depress|anxiet|anxious|\bstress\b|well[- ]?being|wellbeing|burnout|psycholog|mental health|sleep quality|eating disorder|distress"):
        return "2.2"
    # 4 satisfaction
    if has(r"satisf"):
        return "2.3"
    # 5 attitudes/perceptions/willingness
    if has(r"attitude|percept|perceived|perspective|willing|willingness|belief|intention|prefer|loyalty|would i advise|advise others|barrier"):
        return "3.2"
    # 6 behaviors/practices/adherence
    if has(r"adheren|complian|non[- ]?adheren|\bpractice|consumption|\buse of|\busers?\b|uptake|screening|exercise|physical activity|smok|tobacco|condom|not vaccinated|unvaccinated|vaccinat.*(status|coverage)|selling|donat"):
        return "3.3"
    # 7 treatment/procedure response & success
    if has(r"response\b|responder|success|failure|healing|\bcure\b|closure|reintervention|coverage percentage|relieve|relief|infusion|graft|extrusion"):
        return "1.5"
    # 8 severity/progression/complications/safety
    if has(r"severity|complication|recurren|relapse|progression|rebound|adverse|side[- ]?effect|\bgrade|worsening|loss\b|flare|exacerbation"):
        return "1.3"
    # 9 functional/symptom/QoL scales
    if has(r"quality of life|\bqol\b|symptom|\bpain\b|function|disability|\bindex\b|questionnaire|\bscale\b|\bscore\b|osdi|snot|dash|fugl|competence"):
        # competence -> workforce handled later; but 'nurses competence' should be 4.1; catch competence before
        if has(r"competence"): return "4.1"
        return "2.1"
    # 10 disease occurrence / diagnosis
    if has(r"prevalence|incidence|\bpositive for|positivity|diagnos|presence of|"+DISEASE):
        return "1.2"
    # 11 physiological / lab / imaging
    if has(r"\blevel|concentration|pressure|\bcount\b|ratio|angle|\bdose\b|z[- ]?score|hemoglob|haemoglob|glucose|creatinine|bilirubin|\bbmd\b|bone mineral|\bbmi\b|serum|\bblood\b|antibod|\bigg\b|\bigm\b|gene|mutation|phenotype|echogenic|cross[- ]sectional area|\bcsa\b|heart rate|\bhr\b|diameter|width|height|thickness|\brate\b|number of|percentage|proportion|mean |values?\b|measurement"):
        return "1.4"
    # 12 health-system/process
    if has(r"length of (hospital )?stay|hospital stay|\bcost|expenditure|out[- ]of[- ]pocket|time to |waiting|wait time|utiliz|workload|non[- ]complian|turnaround"):
        return "4.1"
    return "OTHER"

def main():
    src=sys.argv[1] if len(sys.argv)>1 else "data/outcomes/08_08_2026_adjudicated_outcomes_desc_causal.csv"
    rows=list(csv.DictReader(open(src,encoding="utf-8-sig")))
    for r in rows:
        r["cat"]=classify(r["adjudicated_outcome"])
        r["cat_label"]=CATLAB[r["cat"]]; r["domain"]=DOMAIN[r["cat"]]
    out="data/outcomes/08_08_2026_outcomes_classified.csv"
    with open(out,"w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    # ASCII-safe summary
    from collections import Counter
    print("classified:",len(rows),"->",out)
    c=Counter(r["cat"] for r in rows)
    for k in ["1.1","1.2","1.3","1.4","1.5","2.1","2.2","2.3","3.1","3.2","3.3","4.1","OTHER"]:
        print("  %-6s %3d  %s"%(k,c.get(k,0),CATLAB[k]))
    # write OTHER + a sample per cat to a file for review (utf-8)
    with open("data/screening/08_08_2026_classify_review.txt","w",encoding="utf-8") as f:
        for k in ["OTHER","1.1","1.2","1.3","1.4","1.5","2.1","2.2","2.3","3.1","3.2","3.3","4.1"]:
            f.write("\n=== %s  %s ===\n"%(k,CATLAB[k]))
            for r in rows:
                if r["cat"]==k: f.write("  [%s] %s\n"%(r["Study_Type"][:4],r["adjudicated_outcome"]))
    print("wrote data/screening/08_08_2026_classify_review.txt")

main()
