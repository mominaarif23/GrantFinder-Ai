import os
import json
import re
from typing import List, Dict, Any, Optional
from app.db import list_curated_opportunities

_CURATED_META: Dict[str, Dict[str, Any]] = {}
try:
    _data_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "curated_opportunities.json")
    if os.path.exists(_data_path):
        with open(_data_path, "r", encoding="utf-8") as f:
            for _it in json.load(f):
                _CURATED_META[_it.get("name", "")] = {
                    "domains": _it.get("domains", []),
                    "category": _it.get("category", "General"),
                    "stages": _it.get("stages", [])
                }
except Exception:
    pass

def get_curated_matches(track: str, country: str, profile: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    opportunities = list_curated_opportunities(track=track, country=country)
    
    scored_results = []
    for opp in opportunities:
        meta = _CURATED_META.get(opp.get("name", ""), {})
        opp_domains = opp.get("domains") or meta.get("domains", [])
        opp_category = opp.get("category") or meta.get("category", "General")
        opp["domains"] = opp_domains
        opp["category"] = opp_category

        score = calculate_base_match_score(opp, profile)
        reasons = generate_match_reasons(opp, profile, score)
        
        scored_results.append({
            "id": opp["id"],
            "name": opp["name"],
            "type": opp["type"],
            "category": opp.get("category", "General"),
            "country": opp.get("country", "Pakistan"),
            "amount": opp.get("amount", "Funded"),
            "deadline": opp.get("deadline", "Open"),
            "eligibility": opp.get("eligibility", "General"),
            "source_link": opp.get("source_link", "https://example.com"),
            "domains": opp.get("domains", []),
            "match_score": score,
            "match_reasons": reasons,
            "is_curated": True,
            "is_locked": False
        })
    
    # Sort by match score descending
    scored_results.sort(key=lambda x: x["match_score"], reverse=True)
    return scored_results

def calculate_base_match_score(opp: Dict[str, Any], profile: Optional[Dict[str, Any]]) -> int:
    base_score = 70
    if not profile:
        return base_score
    
    major_or_domain = profile.get("major_domain", "").strip().lower()
    stage_or_level = profile.get("degree_level_stage", "").strip().lower()
    pref_country = profile.get("country_preference", "").strip().lower()
    gpa_or_funding = profile.get("gpa_funding", "").strip().lower()
    
    opp_country = opp.get("country", "").lower()
    opp_name = opp.get("name", "").lower()
    opp_eligibility = opp.get("eligibility", "").lower()
    opp_category = opp.get("category", "").lower()
    opp_domains = [d.lower() for d in opp.get("domains", [])]
    
    # 1. Geographic Alignment
    if pref_country and pref_country != "all":
        country_aliases = {
            "germany": ["germany", "german", "daad"],
            "united kingdom": ["united kingdom", "uk", "britain", "chevening", "rhodes", "oxford"],
            "united states": ["united states", "usa", "us", "fulbright"],
            "pakistan": ["pakistan", "hec", "peef", "ehsaas", "ignite", "karandaaz", "nic"],
            "turkey": ["turkey", "turkiye", "burslari"],
            "china": ["china", "chinese", "csc"],
            "australia": ["australia", "australian"]
        }
        aliases = country_aliases.get(pref_country, [pref_country])
        is_direct_country = pref_country in opp_country or opp_country in pref_country
        is_opp_target = any(a in opp_name or a in opp_eligibility for a in aliases)
        
        if is_direct_country:
            base_score += 20
        elif is_opp_target:
            base_score += 18
        elif opp_country == "international" or "global" in opp_country:
            base_score += 4
        else:
            # Geographic mismatch (e.g. user wants UK, but opp is domestic Pakistan only)
            base_score -= 15
    else:
        base_score += 5
        
    # 2. Domain / Discipline Relevance
    if major_or_domain:
        # Check synonyms and subfields
        domain_tokens = set(re.findall(r"\w+", major_or_domain))
        domain_hit = False
        
        for d in opp_domains:
            opp_tokens = set(re.findall(r"\w+", d))
            if domain_tokens & opp_tokens or major_or_domain in d or d in major_or_domain:
                base_score += 14
                domain_hit = True
                break
                
        if not domain_hit:
            if any(token in opp_name or token in opp_eligibility for token in domain_tokens if len(token) > 2):
                base_score += 8
            elif "all disciplines" in opp_category or "general" in opp_category:
                base_score += 4
            else:
                base_score -= 6
                
    # 3. Degree Level / Startup Stage Fit
    if stage_or_level:
        if "undergrad" in stage_or_level or "bs" in stage_or_level or "bachelor" in stage_or_level:
            if any(k in opp_name or k in opp_eligibility or k in opp_category for k in ["undergrad", "bs", "bachelor", "all degree", "student"]):
                base_score += 8
            elif "phd" in opp_name and "master" not in opp_name and "undergrad" not in opp_eligibility:
                base_score -= 8
        elif "master" in stage_or_level or "ms" in stage_or_level:
            if any(k in opp_name or k in opp_eligibility or k in opp_category for k in ["master", "ms", "postgrad", "graduate"]):
                base_score += 10
        elif "phd" in stage_or_level or "doctor" in stage_or_level:
            if any(k in opp_name or k in opp_eligibility for k in ["phd", "doctor", "fellowship", "postdoc"]):
                base_score += 12
        elif "prototype" in stage_or_level or "mvp" in stage_or_level:
            if any(k in opp_name or k in opp_eligibility for k in ["seed", "prototype", "incubat", "early", "ignite"]):
                base_score += 10
        elif "idea" in stage_or_level or "concept" in stage_or_level:
            if any(k in opp_name or k in opp_eligibility for k in ["challenge", "idea", "hackathon", "foundational", "incub"]):
                base_score += 10
        elif "revenue" in stage_or_level or "scale" in stage_or_level:
            if any(k in opp_name or k in opp_eligibility for k in ["growth", "accelerat", "commercial", "scale", "venture"]):
                base_score += 10
                
    # 4. Academic Standing / GPA Merit Alignment
    if gpa_or_funding:
        gpa_match = re.search(r"(\d\.\d+)", gpa_or_funding)
        if gpa_match:
            gpa_val = float(gpa_match.group(1))
            if gpa_val >= 3.5 and ("merit" in opp_category or "fellowship" in opp_category):
                base_score += 5
                
    # Normalize bounds
    return min(98, max(50, base_score))

def generate_match_reasons(opp: Dict[str, Any], profile: Optional[Dict[str, Any]], score: int) -> List[str]:
    reasons = [
        f"Verified institutional opportunity: {opp.get('category', 'Government & Foundation')}",
        f"Funding benefit: {opp.get('amount')}"
    ]
    if not profile:
        return reasons
        
    major_or_domain = profile.get("major_domain", "").strip()
    stage_or_level = profile.get("degree_level_stage", "").strip()
    pref_country = profile.get("country_preference", "").strip()
    
    opp_country = opp.get("country", "")
    opp_domains = opp.get("domains", [])
    
    if major_or_domain:
        matched_domain = next((d for d in opp_domains if major_or_domain.lower() in d.lower() or d.lower() in major_or_domain.lower()), None)
        if matched_domain:
            reasons.append(f"Direct discipline alignment with {matched_domain}")
        elif "all disciplines" in opp.get("category", "").lower():
            reasons.append(f"Open across all fields including {major_or_domain}")
            
    if stage_or_level:
        reasons.append(f"Eligibility tailored for {stage_or_level} applicants")
        
    if pref_country and pref_country.lower() != "all":
        if pref_country.lower() in opp_country.lower():
            reasons.append(f"Direct destination match for {pref_country}")
        elif opp_country.lower() == "international":
            reasons.append("Global international award with cross-border tenure")
            
    return reasons

