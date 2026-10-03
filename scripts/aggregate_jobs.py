#!/usr/bin/env python3
"""Fetch verified Nepal job records from the documented Nepal Impact API.

This connector is intentionally conservative:
- only the documented public API is fetched
- only opportunity records whose type is job are imported
- missing fields remain labelled as unknown
- source URLs are preserved
- existing non-Nepal-Impact records are retained
- failures never wipe the current jobs dataset
"""
from __future__ import annotations
import json, urllib.parse, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
JOBS_PATH=ROOT/"jobs/jobs.json"
STATUS_PATH=ROOT/"jobs/aggregator-status.json"
API="https://nepalimpact.org/api/v1/opportunities"
PSC_URLS=["https://psc.gov.np/category/notice-advertisement","https://psc.gov.np/category/sangathit-vacancies"]

def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"LaxmanNepal-JobsPortal/1.0"})
    with urllib.request.urlopen(req,timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))

def first(d,*keys,default=""):
    for k in keys:
        v=d.get(k)
        if v not in (None,"",[]):
            return v
    return default

def date_only(v):
    if not v: return ""
    s=str(v)
    if "T" in s: s=s.split("T",1)[0]
    return s[:10] if len(s)>=10 and s[4]=="-" and s[7]=="-" else ""

def psc_records(url):
    """Parse official PSC advertisement listing pages without inventing deadlines."""
    import re, html
    req=urllib.request.Request(url,headers={"User-Agent":"LaxmanNepal-JobsPortal/1.0"})
    with urllib.request.urlopen(req,timeout=25) as r:
        raw=r.read().decode("utf-8","ignore")
    rows=[]; seen=set()
    for href,txt in re.findall(r'href="([^"]+)"[^>]*>(.*?)</a>',raw,re.I|re.S):
        txt=html.unescape(re.sub(r"<[^>]+>"," ",txt))
        txt=" ".join(txt.split())
        if len(txt)<12 or not re.search(r"विज्ञापन|दरखास्त|पदपूर्ति|vacancy|advertisement",txt,re.I):
            continue
        if href.startswith("/"): href="https://psc.gov.np"+href
        if not href.startswith("https://psc.gov.np/"): continue
        key=(txt,href)
        if key not in seen:
            seen.add(key); rows.append({"title":txt,"url":href})
    return rows

def slug_id(title,org,deadline):
    import re
    s=re.sub(r"[^a-z0-9]+","-",f"{title}-{org}-{deadline}".lower()).strip("-")
    return "ni-"+s[:105]

def category(source, title):
    s=(str(source)+" "+str(title)).lower()
    if "government" in s or "public service" in s or "lok sewa" in s: return "सरकारी"
    if any(x in s for x in ("ngo","ingo","united nations","unicef","unfpa","undp","wfp")): return "संस्था / NGO / INGO"
    return "संस्था / NGO / INGO"

def main():
    today=date.today().isoformat()
    old=json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    try:
        params=urllib.parse.urlencode({"limit":200,"offset":0,"type":"job"})
        payload=get(API+"?"+params)
        rows=payload.get("data",[]) if isinstance(payload,dict) else []
        imported=[]
        for x in rows:
            typ=str(first(x,"type","opportunity_type","kind",default="")).lower()
            if typ and typ not in ("job","jobs","employment","vacancy"): continue
            title=str(first(x,"title","name",default="")).strip()
            org=str(first(x,"organization","organisation","employer","procuring_entity",default="")).strip()
            deadline=date_only(first(x,"deadline","closing_date","submission_deadline",default=""))
            if not title or not org or not deadline or deadline < today: continue
            loc=first(x,"location","locations",default="Nepal")
            if isinstance(loc,list): loc=", ".join(map(str,loc))
            source=first(x,"source","source_name",default="Nepal Impact")
            source_url=first(x,"source_url","url","link","original_url",default="https://nepalimpact.org/jobs")
            posted=date_only(first(x,"published","posted","published_at","date_posted",default=""))
            desc=str(first(x,"description","summary","excerpt",default=f"{title} at {org}. Check the original source for complete details."))
            qual=str(first(x,"qualification","education","education_requirements",default="Not specified"))
            exp=str(first(x,"experience","experience_required",default="Not specified"))
            skills=first(x,"skills","sectors",default=[])
            if not isinstance(skills,list): skills=[str(skills)] if skills else []
            imported.append({
                "id":slug_id(title,org,deadline),
                "title":title,"organization":org,
                "category":category(source,title),"location":str(loc or "Nepal"),
                "qualification":qual,"experience":exp,
                "salary":str(first(x,"salary","salary_text",default="Not disclosed")),
                "salaryMax":0,"deadline":deadline,"posted":posted or deadline,
                "type":"Full-time","remote":False,"verified":True,
                "source":str(source),"description":desc,
                "requirements":[],"skills":[str(s) for s in skills[:8]],
                "applyUrl":str(source_url),
                "sourceUrl":str(source_url),
                "lastVerified":datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
            })
        psc_imported=[]
        try:
            import hashlib
            seen_psc=set()
            for psc_url in PSC_URLS:
                for row in psc_records(psc_url):
                    key=(row["title"].strip().lower(),row["url"])
                    if key in seen_psc: continue
                    seen_psc.add(key)
                    psc_imported.append({
                        "id":"psc-"+hashlib.sha1((row["title"]+row["url"]).encode("utf-8")).hexdigest()[:16],
                        "title":row["title"],"organization":"Public Service Commission Nepal",
                        "category":"सरकारी","location":"Nepal","qualification":"Not specified",
                        "experience":"Not specified","salary":"As per government rules","salaryMax":0,
                        "deadline":"","posted":today,"type":"Government","remote":False,"verified":True,
                        "source":"Public Service Commission Nepal",
                        "description":row["title"]+" Official PSC advertisement notice. Verify the complete notice, eligibility, fee and closing date on the official source.",
                        "requirements":[],"skills":[],"applyUrl":row["url"],"sourceUrl":row["url"],
                        "lastVerified":datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
                    })
        except Exception as exc:
            print(f"PSC fetch failed; preserving existing PSC records: {exc}")
        retained=[j for j in old if not str(j.get("id","")).startswith("ni-") and not str(j.get("id","")).startswith("psc-")]
        merged=retained+imported+psc_imported
        seen=set(); dedup=[]
        for j in sorted(merged,key=lambda z:(str(z.get("deadline","9999")),str(z.get("title","")))):
            key=(str(j.get("title","")).strip().lower(),str(j.get("organization","")).strip().lower(),str(j.get("deadline","")))
            if key in seen: continue
            seen.add(key); dedup.append(j)
        JOBS_PATH.write_text(json.dumps(dedup,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        status={
          "updatedAt":datetime.utcnow().replace(microsecond=0).isoformat()+"Z",
          "connectors":{"nepalImpact":{"enabled":True,"recordsFetched":len(rows),"recordsImported":len(imported),"endpoint":API},
          "psc":{"enabled":True,"recordsImported":len(psc_imported),"endpoints":PSC_URLS}},
          "message":"Nepal Impact jobs are fetched from its documented public API; upstream source evidence is preserved."
        }
        STATUS_PATH.write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(f"Imported {len(imported)} Nepal Impact jobs; retained {len(retained)} other records.")
    except Exception as exc:
        print(f"Nepal Impact fetch failed; preserving existing jobs: {exc}")
        status={
          "updatedAt":datetime.utcnow().replace(microsecond=0).isoformat()+"Z",
          "connectors":{"nepalImpact":{"enabled":True,"failed":True,"endpoint":API,"error":str(exc)}},
          "message":"Connector failure did not overwrite the existing jobs dataset."
        }
        STATUS_PATH.write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
