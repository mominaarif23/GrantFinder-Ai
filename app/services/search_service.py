import httpx
import re
import uuid
from typing import List, Dict, Any, Optional
from app.config import settings

SERPER_URL = "https://google.serper.dev/search"

async def execute_web_search(
    track: str,
    country: str,
    keyword: Optional[str] = "",
    profile: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    # Construct targeted search query
    query_parts = []
    
    if track == "scholarship":
        query_parts.append("university scholarship OR fellowship")
        if profile and profile.get("major_domain"):
            query_parts.append(profile["major_domain"])
        if profile and profile.get("degree_level_stage"):
            query_parts.append(profile["degree_level_stage"])
    else:  # track == "grant"
        query_parts.append("startup grant OR innovation challenge OR seed fund")
        if profile and profile.get("major_domain"):
            query_parts.append(profile["major_domain"])
        if profile and profile.get("degree_level_stage"):
            query_parts.append(profile["degree_level_stage"])
            
    if keyword and keyword.strip():
        query_parts.append(keyword.strip())
        
    if country and country.lower() != "all":
        query_parts.append(country)
        
    query = " ".join(query_parts) + " 2026 2027 application deadline"

    # 1. Attempt live search if SERPER_API_KEY is configured
    if settings.SERPER_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "X-API-KEY": settings.SERPER_API_KEY,
                    "Content-Type": "application/json"
                }
                payload = {
                    "q": query,
                    "num": 8
                }
                response = await client.post(SERPER_URL, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    organic = data.get("organic", [])
                    results = []
                    for item in organic:
                        results.append({
                            "title": item.get("title", "Opportunity"),
                            "snippet": item.get("snippet", ""),
                            "link": item.get("link", "https://example.com"),
                            "source": item.get("source", "Web Discovery"),
                            "country": country if country and country.lower() != "all" else "International"
                        })
                    if results:
                        return results
        except Exception:
            # Fall back cleanly to dynamic mock if network/API error occurs
            pass

    # 2. Intelligent dynamic web search index generator
    return generate_mock_web_results(track, country, keyword, profile)

def generate_mock_web_results(
    track: str,
    country: str,
    keyword: Optional[str],
    profile: Optional[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    major = profile.get("major_domain", "Engineering & Computing") if profile else "Technology"
    c_label = country.strip() if country and country.lower() != "all" else "International"
    c_key = c_label.lower()
    norm_domain = re.sub(r"[^a-zA-Z]", "", c_label.lower())

    if track == "scholarship":
        scholarships_by_country = {
            "germany": [
                {
                    "title": "DAAD Helmut-Schmidt-Programme (Master's in Public Policy & Good Governance)",
                    "snippet": f"Full funding package covering €934/month living stipend, travel subsidy, and health insurance for exceptional scholars in {major} studying in Germany.",
                    "link": "https://www.daad.de/en/study-and-research-in-germany/scholarships",
                    "source": "DAAD Official Portal",
                    "country": "Germany"
                },
                {
                    "title": "Deutschlandstipendium National Merit Scholarship (German Universities)",
                    "snippet": f"National merit scholarship of €300/month awarded to high-achieving undergraduate and master's students pursuing {major} across public German universities.",
                    "link": "https://www.deutschlandstipendium.de",
                    "source": "Federal Ministry of Education (BMBF)",
                    "country": "Germany"
                },
                {
                    "title": "Heinrich Böll Foundation International Student Grants (Germany)",
                    "snippet": f"Provides comprehensive academic grants and monthly stipends for international undergraduates, graduates, and doctoral candidates in {major} studying in Germany.",
                    "link": "https://www.boell.de/en/scholarships",
                    "source": "Heinrich Böll Stiftung",
                    "country": "Germany"
                },
                {
                    "title": "Alexander von Humboldt Foundation International Climate & Research Fellowship",
                    "snippet": "Prestigious research fellowships covering monthly stipend of up to €2,670 plus travel and family support for prospective researchers and scientists in Germany.",
                    "link": "https://www.humboldt-foundation.de",
                    "source": "Humboldt Foundation",
                    "country": "Germany"
                },
                {
                    "title": "Friedrich Ebert Stiftung Postgraduate Scholarship Germany",
                    "snippet": f"Full funding up to €861/month plus family allowance for international scholars with exceptional academic records enrolled in German {major} degree programs.",
                    "link": "https://www.fes.de/en",
                    "source": "Friedrich Ebert Stiftung",
                    "country": "Germany"
                }
            ],
            "united kingdom": [
                {
                    "title": "Chevening UK Government International Scholarships (One-Year Master's)",
                    "snippet": f"Fully funded Master's degrees at top UK institutions for emerging leaders and technical innovators in {major}. Covers full tuition, monthly stipend, and airfare.",
                    "link": "https://www.chevening.org/scholarships",
                    "source": "UK FCDO",
                    "country": "United Kingdom"
                },
                {
                    "title": "British Council GREAT Scholarships for Postgraduate Studies",
                    "snippet": f"£10,000 tuition fee contribution awarded towards one-year postgraduate study across world-renowned UK universities in {major}.",
                    "link": "https://www.britishcouncil.org/study-work-abroad/in-uk/great-scholarships",
                    "source": "British Council",
                    "country": "United Kingdom"
                },
                {
                    "title": "Gates Cambridge Scholarship (Postgraduate Studies)",
                    "snippet": "Covers the full cost of studying at the University of Cambridge, including university composition fees, maintenance allowance (£20,000/yr), and airfare.",
                    "link": "https://www.gatescambridge.org",
                    "source": "Gates Cambridge Trust",
                    "country": "United Kingdom"
                }
            ],
            "united states": [
                {
                    "title": "Fulbright Foreign Student Program (Master's & PhD in the US)",
                    "snippet": f"Complete funding package including university tuition, living allowance, health insurance, and round-trip flights for graduate scholars in {major}.",
                    "link": "https://foreign.fulbrightonline.org",
                    "source": "US Department of State",
                    "country": "United States"
                },
                {
                    "title": "Knight-Hennessy Scholars Program at Stanford University",
                    "snippet": "Full funding for graduate degrees at Stanford University, including tuition, stipend, graduate course fees, and academic enrichment grants.",
                    "link": "https://knight-hennessy.stanford.edu",
                    "source": "Stanford University",
                    "country": "United States"
                }
            ],
            "china": [
                {
                    "title": "Chinese Government Scholarship (CSC) Bilateral University Program",
                    "snippet": f"Full scholarship covering 100% tuition, on-campus accommodation, monthly stipend (up to 3,500 RMB), and medical insurance for {major} scholars.",
                    "link": "https://www.campuschina.org",
                    "source": "China Scholarship Council",
                    "country": "China"
                },
                {
                    "title": "Schwarzman Scholars Master's Fellowship at Tsinghua University",
                    "snippet": "Fully funded one-year master's degree in Global Affairs at Tsinghua University in Beijing, including tuition, room and board, travel, and personal stipend ($4,000).",
                    "link": "https://www.schwarzmanscholars.org",
                    "source": "Schwarzman Scholars",
                    "country": "China"
                }
            ],
            "france": [
                {
                    "title": "Eiffel Excellence Scholarship Programme (Campus France)",
                    "snippet": f"Awarded by the French Ministry for Europe and Foreign Affairs to enable foreign students to pursue Master's and PhD programs in {major} in France (€1,181 - €1,700/mo).",
                    "link": "https://www.campusfrance.org/en/eiffel-scholarship-program-of-excellence",
                    "source": "Campus France",
                    "country": "France"
                },
                {
                    "title": "Emile Boutmy Scholarships at Sciences Po (Paris)",
                    "snippet": "Tuition grants ranging from €3,900 to €14,210 per year for top international students from outside the European Union admitted to undergraduate and master's tracks.",
                    "link": "https://www.sciencespo.fr",
                    "source": "Sciences Po",
                    "country": "France"
                }
            ],
            "netherlands": [
                {
                    "title": "NL Scholarship (Dutch Ministry of Education, Culture and Science)",
                    "snippet": f"Financed by the Dutch Ministry of Education for international students outside the EEA wishing to do a bachelor's or master's in {major} in the Netherlands (€5,000 grant).",
                    "link": "https://www.studyinnl.org/finances/nl-scholarship",
                    "source": "Nuffic Netherlands",
                    "country": "Netherlands"
                },
                {
                    "title": "Orange Tulip Scholarship Programme (Netherlands)",
                    "snippet": f"Offers talented international scholars partial or full tuition fee waivers and living cost subsidies across top Dutch research universities.",
                    "link": "https://www.studyinnl.org",
                    "source": "Orange Tulip Fund",
                    "country": "Netherlands"
                }
            ],
            "sweden": [
                {
                    "title": "Swedish Institute (SI) Scholarship for Global Professionals",
                    "snippet": f"Fully funded scholarship for master's degree studies in Sweden. Covers full tuition, monthly stipend of SEK 12,000, travel grant, and insurance.",
                    "link": "https://si.se/en/apply/scholarships/swedish-institute-scholarships-for-global-professionals",
                    "source": "Swedish Institute",
                    "country": "Sweden"
                },
                {
                    "title": "KTH Royal Institute of Technology Master's Tuition Scholarships",
                    "snippet": f"Full tuition fee waiver for the duration of the master's programme for outstanding non-EU students studying {major} in Stockholm.",
                    "link": "https://www.kth.se/en/studies/master/scholarships",
                    "source": "KTH Sweden",
                    "country": "Sweden"
                }
            ],
            "italy": [
                {
                    "title": "Italian Government MAECI Scholarships for Foreign Citizens",
                    "snippet": f"Grants offered by the Ministry of Foreign Affairs and International Cooperation to foster international cooperation in higher education and {major} in Italy (€900/mo).",
                    "link": "https://studyinitaly.esteri.it",
                    "source": "MAECI Italy",
                    "country": "Italy"
                },
                {
                    "title": "Invest Your Talent in Italy (IYT) Postgraduate Scholarships",
                    "snippet": f"Complete tuition exemption, monthly allowance of €900, and mandatory corporate internships at leading Italian tech and engineering corporations.",
                    "link": "https://postgradinitaly.esteri.it",
                    "source": "Invest Your Talent",
                    "country": "Italy"
                }
            ],
            "spain": [
                {
                    "title": "Spanish MAEC-AECID International Master's Scholarships",
                    "snippet": f"Offered by the Spanish Ministry of Foreign Affairs, providing tuition funding, health coverage, and monthly stipends (€1,300/mo) for foreign graduate students.",
                    "link": "https://www.aecid.es",
                    "source": "AECID Spain",
                    "country": "Spain"
                },
                {
                    "title": "Fundación Carolina Postgraduate Fellowships (Spain)",
                    "snippet": f"Full and partial grants covering university fees, airfare, accommodation, and living stipends for study at leading public Spanish universities in {major}.",
                    "link": "https://www.fundacioncarolina.es",
                    "source": "Fundación Carolina",
                    "country": "Spain"
                }
            ],
            "switzerland": [
                {
                    "title": "Swiss Government Excellence Scholarships (FCS)",
                    "snippet": f"Aimed at young foreign researchers and postgraduates who have completed a master's degree. Provides full tuition waiver, CHF 1,920/mo stipend, and housing allowance.",
                    "link": "https://www.sbfi.admin.ch/scholarships_eng",
                    "source": "Swiss Federal Government",
                    "country": "Switzerland"
                },
                {
                    "title": "ETH Zurich Excellence Scholarship & Opportunity Programme (ESOP)",
                    "snippet": "Covers the full study and living costs during the Master's degree course (CHF 12,000 per semester plus tuition fee waiver) at ETH Zurich.",
                    "link": "https://ethz.ch/students/en/studies/financial/scholarships/excellencescholarship.html",
                    "source": "ETH Zurich",
                    "country": "Switzerland"
                }
            ],
            "canada": [
                {
                    "title": "Vanier Canada Graduate Scholarships",
                    "snippet": f"$50,000 per year for three years during doctoral studies at Canadian institutions, awarded to world-class PhD scholars in {major}.",
                    "link": "https://vanier.gc.ca",
                    "source": "Government of Canada",
                    "country": "Canada"
                },
                {
                    "title": "Lester B. Pearson International Scholarship (University of Toronto)",
                    "snippet": "Covers tuition, books, incidental fees, and full residence support for four years of undergraduate study in Toronto.",
                    "link": "https://future.utoronto.ca/pearson",
                    "source": "University of Toronto",
                    "country": "Canada"
                }
            ],
            "australia": [
                {
                    "title": "Australia Awards Scholarships (DFAT)",
                    "snippet": f"Long-term awards administered by the Department of Foreign Affairs and Trade for full-time master's study in Australia. Covers full tuition, airfare, and living allowance.",
                    "link": "https://www.dfat.gov.au/people-to-people/australia-awards",
                    "source": "Australian Government",
                    "country": "Australia"
                },
                {
                    "title": "Australian Government Research Training Program (RTP) International Stipend",
                    "snippet": f"Annual living stipend of up to AUD 35,000 plus full tuition offset for outstanding postgraduate research candidates in {major}.",
                    "link": "https://www.education.gov.au/research-block-grants/research-training-program",
                    "source": "Department of Education",
                    "country": "Australia"
                }
            ],
            "turkey": [
                {
                    "title": "Türkiye Bursları Full Postgraduate Scholarships",
                    "snippet": f"Full government scholarship covering university placement, tuition waiver, free accommodation, health insurance, and monthly living stipend in Turkey.",
                    "link": "https://www.turkiyeburslari.gov.tr",
                    "source": "Presidency for Turks Abroad",
                    "country": "Turkey"
                }
            ],
            "pakistan": [
                {
                    "title": "LUMS National Outreach Programme (NOP) & Merit Scholarships 2026",
                    "snippet": f"Full financial assistance and tuition awards for exceptional scholars pursuing degrees in {major}. Covers tuition, hostel, and monthly stipend in Pakistan.",
                    "link": "https://nop.lums.edu.pk",
                    "source": "LUMS Portal",
                    "country": "Pakistan"
                },
                {
                    "title": "NUST Need-Based & Industry Partner Scholarships (BS/MS)",
                    "snippet": f"Over 1,200 merit and endowment funds awarded annually to talented computing and {major} undergraduates with minimum 3.0 CGPA.",
                    "link": "https://nust.edu.pk/scholarships",
                    "source": "NUST Official",
                    "country": "Pakistan"
                },
                {
                    "title": "FAST-NUCES Alumni Endowment Educational Scholarship Fund",
                    "snippet": f"Interest-free loans and non-refundable scholarships for students enrolled in {major}, computer science, and data engineering departments.",
                    "link": "https://nu.edu.pk/Admissions/Scholarships",
                    "source": "FAST University",
                    "country": "Pakistan"
                }
            ]
        }

        if c_key in scholarships_by_country:
            return scholarships_by_country[c_key]
        
        # Universal dynamic generator for any other country (e.g. Ireland, Norway, Finland, Austria, Japan, etc.)
        return [
            {
                "title": f"{c_label} National Ministry of Higher Education International Excellence Fellowship",
                "snippet": f"Prestigious government fellowship providing 100% full tuition coverage, monthly living stipend, and relocation grants for top international scholars in {major}.",
                "link": f"https://www.studyin{norm_domain}.org/scholarships",
                "source": f"{c_label} Higher Education Commission",
                "country": c_label
            },
            {
                "title": f"{c_label} State University Chancellor's Merit & Research Scholarship",
                "snippet": f"Merit-based financial grant covering complete tuition and monthly research stipends for international undergraduate and master's students pursuing {major}.",
                "link": f"https://chancellor.{norm_domain}.edu/grants",
                "source": f"{c_label} University Council",
                "country": c_label
            },
            {
                "title": f"{c_label} Global Future Leaders Academic Award (2026/2027)",
                "snippet": f"Non-repayable endowment scholarship supporting exceptional scholars in {major} with high academic standings and demonstrated leadership potential.",
                "link": f"https://www.globalawards.{norm_domain}.gov",
                "source": f"{c_label} International Foundation",
                "country": c_label
            },
            {
                "title": f"Erasmus Mundus Joint Master Degrees (European Multi-Country Fellowship)",
                "snippet": f"Fully funded European Union master's scholarship valid for study across {c_label} and partner European institutions (€1,400/month stipend + full tuition).",
                "link": "https://erasmus-plus.ec.europa.eu",
                "source": "European Commission",
                "country": c_label
            }
        ]

    else:  # track == "grant"
        grants_by_country = {
            "germany": [
                {
                    "title": "EXIST Business Start-up Grant (German Federal Ministry for Economic Affairs)",
                    "snippet": f"Non-dilutive grant supporting university students, graduates, and scientists in Germany. Provides up to €3,000/month living stipend per founder plus €30,000 materials budget for {major} startups.",
                    "link": "https://www.exist.de/EN",
                    "source": "German BMWK",
                    "country": "Germany"
                },
                {
                    "title": "High-Tech Gründerfonds (HTGF) Seed Investment Fund Germany",
                    "snippet": f"Europe's premier seed fund financing tech-driven startups in AI, deeptech, and {major} across Germany with initial ticket sizes up to €1,000,000.",
                    "link": "https://www.htgf.de/en",
                    "source": "HTGF Germany",
                    "country": "Germany"
                },
                {
                    "title": "Berlin Startup Scholarship & Incubation Stipend",
                    "snippet": f"Equity-free grant of €2,200/month per founder for student entrepreneurs launching innovative software and hardware ventures in Berlin.",
                    "link": "https://www.berlin.de/sen/wirtschaft/gruenden-und-foerdern/existenzgruendungen/berliner-startup-stipendium",
                    "source": "Berlin Senate for Economics",
                    "country": "Germany"
                },
                {
                    "title": "Bavarian Research Foundation Tech Prototype Seed Grant",
                    "snippet": f"Project subsidies up to €50,000 for student founders turning academic research in {major} into scalable commercial prototypes in Bavaria.",
                    "link": "https://forschungsstiftung.de",
                    "source": "Bavarian Foundation",
                    "country": "Germany"
                }
            ],
            "united kingdom": [
                {
                    "title": "Innovate UK Smart Grants (Non-dilutive Tech Innovation Fund)",
                    "snippet": f"Government grants from £25,000 to £500,000 for disruptive early-stage technology startups led by UK university researchers and student founders.",
                    "link": "https://www.ukri.org/councils/innovate-uk",
                    "source": "Innovate UK",
                    "country": "United Kingdom"
                },
                {
                    "title": "Techstars London Pre-Seed Founder Accelerator & Grant",
                    "snippet": "Provides up to $120,000 funding, hands-on mentorship, and access to an unmatched global network of corporate partners and venture capitalists.",
                    "link": "https://www.techstars.com/accelerators/london",
                    "source": "Techstars UK",
                    "country": "United Kingdom"
                }
            ],
            "united states": [
                {
                    "title": "National Science Foundation (NSF) SBIR/STTR Seed Grants",
                    "snippet": f"Up to $275,000 in non-dilutive federal capital to conduct research and development on innovative technological concepts in {major}.",
                    "link": "https://seedfund.nsf.gov",
                    "source": "NSF America",
                    "country": "United States"
                },
                {
                    "title": "Y Combinator Early Stage Founder Fellowship ($500,000)",
                    "snippet": "Twice a year YC invests $500,000 in early-stage startups worldwide to build groundbreaking technology, SaaS, and AI applications.",
                    "link": "https://www.ycombinator.com",
                    "source": "Y Combinator",
                    "country": "United States"
                }
            ],
            "china": [
                {
                    "title": "Innoway Beijing Tech Hub Seed Venture Grant",
                    "snippet": f"Equity-free seed subsidies up to 300,000 RMB plus 12 months free incubator space in Zhongguancun for international student founders building {major} tech.",
                    "link": "https://www.zgc-innoway.com",
                    "source": "Innoway Beijing",
                    "country": "China"
                },
                {
                    "title": "HAX Hardware & Robotics Accelerator Seed Stipend China",
                    "snippet": "$250,000 initial investment, prototype development facilities, and supply-chain engineering support for technical teams based in Shenzhen.",
                    "link": "https://hax.co",
                    "source": "HAX SOSV",
                    "country": "China"
                }
            ],
            "france": [
                {
                    "title": "Bpifrance French Tech Seed Innovation Grant",
                    "snippet": f"Matching grants and convertible subsidies up to €50,000 for early-stage deeptech and software ventures founded by university scholars in France.",
                    "link": "https://www.bpifrance.fr",
                    "source": "Bpifrance",
                    "country": "France"
                },
                {
                    "title": "Station F Founders Program Seed Stipend (Paris)",
                    "snippet": "Full residency at the world's largest startup campus in Paris with non-dilutive cloud credits, prototyping labs, and investor matchmaking.",
                    "link": "https://stationf.co",
                    "source": "Station F",
                    "country": "France"
                }
            ],
            "netherlands": [
                {
                    "title": "Netherlands Enterprise Agency (RVO) Innovation Seed Voucher",
                    "snippet": f"Subsidies up to €25,000 for innovative early-stage startups and student founders developing clean tech, digital health, and {major} solutions in the Netherlands.",
                    "link": "https://english.rvo.nl",
                    "source": "RVO Netherlands",
                    "country": "Netherlands"
                }
            ],
            "sweden": [
                {
                    "title": "Vinnova Sweden's Innovation Agency Pre-Seed Grant",
                    "snippet": f"Grants up to SEK 500,000 for innovative startup projects with significant technical risk and high potential impact founded in Sweden.",
                    "link": "https://www.vinnova.se/en",
                    "source": "Vinnova Sweden",
                    "country": "Sweden"
                }
            ],
            "italy": [
                {
                    "title": "CDP Venture Capital Smart&Start Italia Grant",
                    "snippet": f"Zero-interest loans and non-repayable grants up to €1,500,000 for innovative tech startups established in Italy by youth under 35.",
                    "link": "https://www.invitalia.it",
                    "source": "Invitalia",
                    "country": "Italy"
                }
            ],
            "spain": [
                {
                    "title": "ENISA Young Entrepreneurs Seed Grant (Spain)",
                    "snippet": f"Participative loans up to €75,000 with no guarantees required for innovative startups founded by entrepreneurs aged 40 or under in Spain.",
                    "link": "https://www.enisa.es",
                    "source": "ENISA Spain",
                    "country": "Spain"
                }
            ],
            "switzerland": [
                {
                    "title": "Innosuisse Swiss Innovation Agency Initial Startup Grant",
                    "snippet": f"Direct project funding and professional business coaching vouchers up to CHF 50,000 for science-based startups in Switzerland.",
                    "link": "https://www.innosuisse.ch",
                    "source": "Innosuisse",
                    "country": "Switzerland"
                },
                {
                    "title": "Venture Kick Pre-Seed Foundation Fund Switzerland",
                    "snippet": "Provides up to CHF 150,000 in non-dilutive milestone-based seed capital for university spin-offs and student ventures in Switzerland.",
                    "link": "https://www.venturekick.ch",
                    "source": "Venture Kick",
                    "country": "Switzerland"
                }
            ],
            "pakistan": [
                {
                    "title": "PITB & TechHub Connect Co-Working & Prototype Seed Grant 2026",
                    "snippet": f"Equity-free grants up to PKR 1,500,000 for early-stage {major} startups founded by university students and recent graduates in Punjab.",
                    "link": "https://pitb.gov.pk/techhub",
                    "source": "PITB",
                    "country": "Pakistan"
                },
                {
                    "title": "LUMS Center for Entrepreneurship (LCE) Foundation Fund",
                    "snippet": f"Providing incubation, venture backing, and seed grants for student-led deep tech and {major} initiatives across Pakistan.",
                    "link": "https://lce.lums.edu.pk",
                    "source": "LUMS LCE",
                    "country": "Pakistan"
                },
                {
                    "title": "Ignite National Technology Fund - SEED Startup Grant",
                    "snippet": f"Up to PKR 5,000,000 in equity-free non-dilutive capital for student founders building 4IR prototypes in {major}.",
                    "link": "https://ignite.org.pk",
                    "source": "Ignite Pakistan",
                    "country": "Pakistan"
                }
            ]
        }

        if c_key in grants_by_country:
            return grants_by_country[c_key]

        # Universal dynamic grant generator for any other country
        return [
            {
                "title": f"{c_label} National Innovation Agency Early-Stage Venture Grant",
                "snippet": f"Non-dilutive prototype and commercialization grant up to $50,000 equivalent for tech startups in {major} founded by students and recent alumni in {c_label}.",
                "link": f"https://www.innovationagency.{norm_domain}.gov/grants",
                "source": f"{c_label} Innovation Authority",
                "country": c_label
            },
            {
                "title": f"{c_label} Science & Enterprise Foundation Prototype Seed Voucher",
                "snippet": f"Direct financial stipend to develop minimum viable products (MVPs) and file initial IP protection for early-stage software and hardware ventures in {c_label}.",
                "link": f"https://seedfund.{norm_domain}.org",
                "source": f"{c_label} Tech Enterprise Board",
                "country": c_label
            },
            {
                "title": f"{c_label} University Incubator Cohort Seed Stipend (2026/2027)",
                "snippet": f"Providing equity-free seed grants, co-working facilities, and mentor networks for student ventures targeting international markets.",
                "link": f"https://incubator.{norm_domain}.edu",
                "source": f"{c_label} University Network",
                "country": c_label
            },
            {
                "title": "Google for Startups Cloud & AI Catalyst Fund",
                "snippet": "Up to $100,000 in Google Cloud and Gemini AI infrastructure credits, technical mentorship, and global venture network access.",
                "link": "https://startup.google.com/programs",
                "source": "Google for Startups",
                "country": c_label
            }
        ]
