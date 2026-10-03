#!/usr/bin/env python3
"""Generate and clean SEO-friendly static job detail pages from jobs/jobs.json."""
from pathlib import Path
from datetime import datetime, timezone
import os
import json, re, html, shutil

ROOT = Path(__file__).resolve().parents[1]
JOBS_FILE = ROOT / "jobs.json"
OUT = ROOT
MARKER = "<!-- GENERATED JOB PAGE -->"
SITE_URL = os.environ.get("SITE_URL", "https://jobs.laxmannepal.com.np").rstrip("/")

def slugify(value):
    value = re.sub(r"[^\w\s-]", "", str(value).lower().strip(), flags=re.UNICODE)
    value = re.sub(r"-+", "-", re.sub(r"\s+", "-", value))
    return value[:70].strip("-") or "job"

def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)

def fmt_date(value):
    if not value:
        return "Not specified"
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        return str(value)

def page(job, slug):
    title = esc(job.get("title", "Nepal Job"))
    org = esc(job.get("organization", "Employer"))
    category = esc(job.get("category", "Other"))
    location = esc(job.get("location", "Nepal"))
    qualification = esc(job.get("qualification", "Not specified"))
    experience = esc(job.get("experience", "Not specified"))
    salary = esc(job.get("salary", "Not disclosed"))
    deadline = esc(job.get("deadline", ""))
    description = esc(job.get("description", "Check the source for the complete vacancy details."))
    source = esc(job.get("source", "Employer"))
    apply = esc(job.get("applyUrl", "#"))
    canonical = f"{SITE_URL}/{slug}/"
    reqs = job.get("requirements") or []
    skills = job.get("skills") or []
    req_html = "".join(f"<li>{esc(x)}</li>" for x in reqs) or "<li>See the official vacancy notice.</li>"
    skill_html = "".join(f"<span>{esc(x)}</span>" for x in skills) or "<span>Not specified</span>"
    verified = "✓ Verified source" if job.get("verified") else "Source listed"
    valid = f'{deadline}T23:59:59+05:45' if deadline else ""
    jsonld = {
        "@context":"https://schema.org","@type":"JobPosting","title":job.get("title","Nepal Job"),
        "description":job.get("description","Check the source for the complete vacancy details."),
        "datePosted":job.get("posted") or None,"validThrough":valid or None,
        "employmentType":job.get("type") if job.get("type") and job.get("type") != "Not specified" else None,
        "hiringOrganization":{"@type":"Organization","name":job.get("organization","Employer")},
        "jobLocation":{"@type":"Place","address":{"@type":"PostalAddress","addressLocality":job.get("location","Nepal"),"addressCountry":"NP"}},
        "url":canonical
    }
    if job.get("salaryMax"):
        jsonld["baseSalary"]={"@type":"MonetaryAmount","currency":"NPR","value":{"@type":"QuantitativeValue","maxValue":job["salaryMax"],"unitText":"MONTH"}}
    jsonld = json.dumps({k:v for k,v in jsonld.items() if v is not None}, ensure_ascii=False)
    return f'''<!doctype html>
<html lang="en">
<head>
{MARKER}
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{title} at {org}. Qualification, experience, location, salary, deadline and application source.">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{title} — {org}">
<meta property="og:description" content="Nepal job vacancy: {title} at {org}. Deadline: {fmt_date(job.get("deadline"))}.">
<meta property="og:type" content="website"><meta property="og:url" content="{canonical}">
<title>{title} — {org} | Nepal Jobs</title>
<link rel="stylesheet" href="/jobs.css">
<link rel="stylesheet" href="/jobs.css">
<style>
.job-detail-wrap{{width:min(900px,calc(100% - 28px));margin:0 auto;padding:48px 0 70px}}
.job-detail-card{{border:1px solid var(--jb-line);border-radius:26px;background:rgba(255,255,255,.86);backdrop-filter:blur(18px);box-shadow:0 18px 55px rgba(16,24,40,.08);overflow:hidden}}
.job-detail-head{{padding:30px;border-bottom:1px solid var(--jb-line)}}
.job-detail-head h1{{font-size:clamp(30px,5vw,50px);line-height:1.05;letter-spacing:-.045em;margin:10px 0}}
.job-detail-org{{color:#667085;font-size:14px;font-weight:700}}
.job-detail-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding:18px 30px;background:#f8fafc}}
.job-detail-stat{{padding:12px;border:1px solid var(--jb-line);border-radius:13px;background:#fff}}
.job-detail-stat span{{display:block;color:#98a2b3;font-size:9px;font-weight:800;text-transform:uppercase}}
.job-detail-stat strong{{display:block;margin-top:3px;font-size:12px}}
.job-detail-body{{padding:30px}}
.job-detail-body section{{margin-bottom:28px}}
.job-detail-body h2{{font-size:15px;margin:0 0 9px}}
.job-detail-body p,.job-detail-body li{{color:#475467;font-size:14px;line-height:1.75}}
.job-detail-body ul{{padding-left:20px}}
.job-skills{{display:flex;gap:7px;flex-wrap:wrap}}
.job-skills span{{padding:7px 10px;border-radius:999px;background:#f2f4f7;color:#475467;font-size:11px;font-weight:750}}
.job-detail-actions{{display:flex;gap:9px;flex-wrap:wrap;margin-top:24px}}
.job-detail-actions a{{display:inline-block;text-decoration:none;padding:12px 16px;border-radius:12px;font-size:12px;font-weight:850}}
.job-apply{{background:#111827;color:#fff}}
.job-back{{border:1px solid var(--jb-line);background:#fff;color:#344054}}
.job-source{{padding:14px;border-radius:13px;background:#f8fafc;color:#667085;font-size:11px;line-height:1.6}}
@media(max-width:700px){{.job-detail-grid{{grid-template-columns:1fr 1fr;padding:14px}}.job-detail-head,.job-detail-body{{padding:22px}}}}
</style>
<script type="application/ld+json">{jsonld}</script>
</head>
<body>
<header class="jobs-header">
<a class="jobs-brand" href="/" aria-label="Nepal Jobs home"><span class="jobs-logo">LN</span><span><strong>Nepal Jobs</strong><small>Verified Nepal vacancy portal</small></span></a>
<nav aria-label="Main navigation"><a href="/">Home</a><a href="/youtube-tools/">YouTube Tools</a><a class="active" href="/">Jobs</a></nav>
<a class="jobs-header-btn" href="/jobs/">Browse Jobs</a>
</header>
<main class="job-detail-wrap">
<article class="job-detail-card">
<header class="job-detail-head">
<div class="eyebrow">{category} · {verified}</div>
<h1>{title}</h1>
<div class="job-detail-org">{org} · {location}</div>
<div class="job-detail-actions"><a class="job-apply" href="{apply}" target="_blank" rel="noopener noreferrer">Apply / View official notice ↗</a><a class="job-back" href="/jobs/">← Back to all jobs</a></div>
</header>
<div class="job-detail-grid">
<div class="job-detail-stat"><span>Qualification</span><strong>{qualification}</strong></div>
<div class="job-detail-stat"><span>Experience</span><strong>{experience}</strong></div>
<div class="job-detail-stat"><span>Salary</span><strong>{salary}</strong></div>
<div class="job-detail-stat"><span>Deadline</span><strong>{fmt_date(job.get("deadline"))}</strong></div>
</div>
<div class="job-detail-body">
<section><h2>Job overview</h2><p>{description}</p></section>
<section><h2>Requirements</h2><ul>{req_html}</ul></section>
<section><h2>Skills</h2><div class="job-skills">{skill_html}</div></section>
<section><h2>Application & source</h2><div class="job-source"><strong>Source:</strong> {source}<br>Verify the exact qualification, eligibility, fee, deadline and application instructions on the source before applying.</div></section>
</div>
</article>
</main>
</body>
</html>
'''

def main():
    jobs = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
    active = set()
    for job in jobs:
        slug = slugify(f'{job.get("title","job")}-{job.get("organization","")}')
        active.add(slug)
        folder = OUT / slug
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(page(job, slug), encoding="utf-8")

    for d in OUT.iterdir():
        if not d.is_dir() or d.name in active:
            continue
        p = d / "index.html"
        if p.exists():
            try:
                if MARKER in p.read_text(encoding="utf-8"):
                    shutil.rmtree(d)
            except OSError:
                pass

    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap.append(f"  <url><loc>{SITE_URL}/</loc></url>")
    for slug in sorted(active):
        sitemap.append(f"  <url><loc>{SITE_URL}/{slug}/</loc></url>")
    sitemap.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
    print(f"Generated {len(jobs)} job pages and sitemap entries.")

if __name__ == "__main__":
    main()
