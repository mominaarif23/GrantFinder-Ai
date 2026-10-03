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

EUROPEAN_COUNTRIES = {
    "germany", "united kingdom", "uk", "france", "netherlands", "sweden", "italy",
    "spain", "switzerland", "ireland", "norway", "finland", "denmark", "austria",
    "belgium", "poland", "hungary", "czech republic", "portugal", "greece", "turkey"
}

COUNTRY_ALIASES = {
    "germany": ["germany", "german", "daad", "berlin", "munich", "deutschland", "tum", "lmu"],
    "united kingdom": ["united kingdom", "uk", "britain", "british", "chevening", "rhodes", "oxford", "cambridge", "commonwealth"],
    "united states": ["united states", "usa", "us", "american", "fulbright", "stanford", "harvard", "mit"],
    "china": ["china", "chinese", "csc", "tsinghua", "peking", "beijing", "shanghai"],
    "france": ["france", "french", "eiffel", "campus france", "paris", "sorbonne", "sciences po"],
    "netherlands": ["netherlands", "dutch", "holland", "orange tulip", "amsterdam", "delft", "groningen"],
    "sweden": ["sweden", "swedish", "kth", "stockholm", "uppsala", "lund"],
    "italy": ["italy", "italian", "maeci", "bocconi", "bologna", "politecnico"],
    "spain": ["spain", "spanish", "carolina", "maec", "madrid", "barcelona"],
    "switzerland": ["switzerland", "swiss", "eth", "epfl", "zurich", "lausanne"],
    "ireland": ["ireland", "irish", "trinity", "ucd"],
    "norway": ["norway", "norwegian", "oslo"],
    "finland": ["finland", "finnish", "helsinki", "aalto"],
    "denmark": ["denmark", "danish", "copenhagen", "dtu"],
    "austria": ["austria", "austrian", "vienna"],
    "belgium": ["belgium", "belgian", "brussels", "leuven", "ghent"],
    "poland": ["poland", "polish", "warsaw", "nawa"],
    "hungary": ["hungary", "hungarian", "hungaricum", "budapest"],
    "czech republic": ["czech", "czech republic", "prague"],
    "portugal": ["portugal", "portuguese", "lisbon", "porto"],
    "greece": ["greece", "greek", "athens"],
    "turkey": ["turkey", "turkiye", "burslari", "istanbul", "ankara", "tubitak"],
    "canada": ["canada", "canadian", "vanier", "toronto", "mcgill", "ubc", "waterloo"],
    "australia": ["australia", "australian", "sydney", "melbourne", "anu", "queensland"],
    "japan": ["japan", "japanese", "mext", "tokyo", "kyoto"],
    "south korea": ["south korea", "korea", "korean", "gks", "seoul", "kaist"],
    "singapore": ["singapore", "singa", "nus", "ntu"],
    "malaysia": ["malaysia", "malaysian", "mis"],
    "saudi arabia": ["saudi arabia", "saudi", "kaust", "kfupm"],
    "united arab emirates": ["united arab emirates", "uae", "dubai", "abu dhabi", "mbzuai"],
    "pakistan": ["pakistan", "hec", "peef", "ehsaas", "ignite", "karandaaz", "nic", "lums", "nust", "fast", "giki", "pitb"]
}

def get_curated_matches(track: str, country: str, profile: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    opportunities = list_curated_opportunities(track=track, country=country)
    
    scored_results = []
    norm_search_country = (country or "").strip().lower()

    for opp in opportunities:
        meta = _CURATED_META.get(opp.get("name", ""), {})
        opp_domains = opp.get("domains") or meta.get("domains", [])
        opp_category = opp.get("category") or meta.get("category", "General")
        opp["domains"] = opp_domains
        opp["category"] = opp_category

        opp_country = (opp.get("country") or "").strip().lower()
        opp_name_lower = opp.get("name", "").lower()
        opp_elig_lower = opp.get("eligibility", "").lower()

        # Strict Relevance Filter: When user explicitly searches for a country (e.g. Germany),
        # eliminate opportunities belonging exclusively to another nation (e.g. Pakistan, USA, etc.)
        if norm_search_country and norm_search_country not in ("all", "international"):
            # Exclude opportunities with a different specific domestic country
            if opp_country and opp_country not in ("international", "global", "", norm_search_country):
                continue
            
            # If the opportunity has country="International", check if its name or scope is explicitly tied to another country
            if norm_search_country != "pakistan":
                if any(k in opp_name_lower or k in opp_elig_lower for k in ["hec indigenous", "peef", "ehsaas", "lums national outreach", "ignite national"]):
                    continue
                if "pakistan" in opp_name_lower and not any(k in opp_name_lower for k in [norm_search_country, "erasmus", "daad"]):
                    continue
            if norm_search_country not in ("united states", "usa", "us") and "fulbright pakistan" in opp_name_lower:
                continue
            if norm_search_country != "australia" and "australia awards" in opp_name_lower:
                continue

        score = calculate_base_match_score(opp, profile, target_country=country)
        reasons = generate_match_reasons(opp, profile, score, target_country=country)
        
        # Determine displayed country
        display_country = opp.get("country")
        if not display_country or display_country == "International":
            if norm_search_country and norm_search_country != "all":
                display_country = country
            else:
                display_country = "International"

        scored_results.append({
            "id": opp["id"],
            "name": opp["name"],
            "type": opp["type"],
            "category": opp.get("category", "General"),
            "country": display_country,
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

def calculate_base_match_score(
    opp: Dict[str, Any],
    profile: Optional[Dict[str, Any]],
    target_country: Optional[str] = None
) -> int:
    base_score = 70

    # User's searched country takes highest priority; fall back to profile preference
    effective_country = ""
    if target_country and target_country.lower() != "all":
        effective_country = target_country.strip().lower()
    elif profile and profile.get("country_preference") and profile.get("country_preference").lower() != "all":
        effective_country = profile.get("country_preference").strip().lower()

    opp_country = (opp.get("country") or "").lower().strip()
    opp_name = opp.get("name", "").lower()
    opp_eligibility = opp.get("eligibility", "").lower()
    opp_category = opp.get("category", "").lower()
    opp_domains = [d.lower() for d in opp.get("domains", [])]
    
    # 1. Geographic Alignment (Heavily weighted)
    if effective_country and effective_country != "all":
        aliases = COUNTRY_ALIASES.get(effective_country, [effective_country])
        is_direct_country = effective_country in opp_country or opp_country in effective_country
        is_opp_target = any(a in opp_name or a in opp_eligibility for a in aliases)
        is_european_program = (effective_country in EUROPEAN_COUNTRIES) and any(k in opp_name for k in ["erasmus", "europe", "hungaricum", "daad", "epos"])

        if is_direct_country or is_opp_target:
            base_score += 26
        elif is_european_program:
            base_score += 18
        elif opp_country in ("international", "global"):
            base_score += 6
        else:
            base_score -= 35
    else:
        base_score += 5
        
    # 2. Domain / Discipline Relevance
    major_or_domain = profile.get("major_domain", "").strip().lower() if profile else ""
    if major_or_domain:
        domain_tokens = set(re.findall(r"\w+", major_or_domain))
        domain_hit = False
        
        for d in opp_domains:
            opp_tokens = set(re.findall(r"\w+", d))
            if domain_tokens & opp_tokens or major_or_domain in d or d in major_or_domain:
                base_score += 12
                domain_hit = True
                break
                
        if not domain_hit:
            if any(token in opp_name or token in opp_eligibility for token in domain_tokens if len(token) > 2):
                base_score += 7
            elif "all disciplines" in opp_category or "general" in opp_category:
                base_score += 4
            else:
                base_score -= 4
                
    # 3. Degree Level / Startup Stage Fit
    stage_or_level = profile.get("degree_level_stage", "").strip().lower() if profile else ""
    if stage_or_level:
        if any(k in stage_or_level for k in ["undergrad", "bs", "bachelor"]):
            if any(k in opp_name or k in opp_eligibility or k in opp_category for k in ["undergrad", "bs", "bachelor", "all degree", "student"]):
                base_score += 8
            elif "phd" in opp_name and "master" not in opp_name and "undergrad" not in opp_eligibility:
                base_score -= 8
        elif any(k in stage_or_level for k in ["master", "ms", "postgrad"]):
            if any(k in opp_name or k in opp_eligibility or k in opp_category for k in ["master", "ms", "postgrad", "graduate"]):
                base_score += 10
        elif any(k in stage_or_level for k in ["phd", "doctor"]):
            if any(k in opp_name or k in opp_eligibility for k in ["phd", "doctor", "fellowship", "postdoc"]):
                base_score += 12
        elif any(k in stage_or_level for k in ["prototype", "mvp"]):
            if any(k in opp_name or k in opp_eligibility for k in ["seed", "prototype", "incubat", "early", "ignite"]):
                base_score += 10
        elif any(k in stage_or_level for k in ["idea", "concept"]):
            if any(k in opp_name or k in opp_eligibility for k in ["challenge", "idea", "hackathon", "foundational", "incub"]):
                base_score += 10
        elif any(k in stage_or_level for k in ["revenue", "scale"]):
            if any(k in opp_name or k in opp_eligibility for k in ["growth", "accelerat", "commercial", "scale", "venture"]):
                base_score += 10
                
    # 4. Academic Standing / GPA Merit Alignment
    gpa_or_funding = profile.get("gpa_funding", "").strip().lower() if profile else ""
    if gpa_or_funding:
        gpa_match = re.search(r"(\d\.\d+)", gpa_or_funding)
        if gpa_match:
            gpa_val = float(gpa_match.group(1))
            if gpa_val >= 3.5 and ("merit" in opp_category or "fellowship" in opp_category or "daad" in opp_name):
                base_score += 4
                
    # Normalize bounds
    return min(98, max(50, base_score))

def generate_match_reasons(
    opp: Dict[str, Any],
    profile: Optional[Dict[str, Any]],
    score: int,
    target_country: Optional[str] = None
) -> List[str]:
    reasons = [
        f"Verified institutional opportunity: {opp.get('category', 'Government & Foundation')}",
        f"Funding benefit: {opp.get('amount')}"
    ]
    
    effective_country = target_country if target_country and target_country.lower() != "all" else (profile.get("country_preference") if profile else None)
    if effective_country:
        reasons.append(f"Aligned with destination preference: {effective_country}")

    if not profile:
        return reasons
        
    major_or_domain = profile.get("major_domain", "").strip()
    stage_or_level = profile.get("degree_level_stage", "").strip()
    opp_domains = opp.get("domains", [])
    
    if major_or_domain:
        matched_domain = next((d for d in opp_domains if major_or_domain.lower() in d.lower() or d.lower() in major_or_domain.lower()), None)
        if matched_domain:
            reasons.append(f"Direct discipline alignment with {matched_domain}")
        elif "all disciplines" in opp.get("category", "").lower():
            reasons.append(f"Open across all fields including {major_or_domain}")
            
    if stage_or_level:
        reasons.append(f"Eligibility tailored for {stage_or_level} applicants")
            
    return reasons
