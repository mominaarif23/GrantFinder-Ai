# UI & UX Design Specification & Visual System

Project: **GrantFinder AI**
Document Version: 1.0.0
Design Reference: EEDU Point Global Education & Nuova Academic Layout Systems

---

## 1. Design Direction & Visual Identity

Based on the reference design standards, GrantFinder AI adopts a **High-Trust Academic & Venture Architecture**. The visual tone transitions from developer-centric dark themes to a publication-grade, institutional interface utilizing crisp off-white canvas backgrounds, deep Oxford Navy contrast headers, refined Cobalt and Emerald track accents, asymmetric stat callouts, and structured opportunity cards.

---

## 2. Color System & Design Tokens

### 2.1 Core Palette

```text
[ Oxford Navy ]   #0A192F / #0F172A   Primary text, navigation headers, dark accents
[ Cobalt Blue ]   #1D4ED8 / #2563EB   Primary brand color, Student track CTA, active tabs
[ Sky Tint ]      #E0F2FE / #F0F9FF   Badge backgrounds, icon containers, card accents
[ Emerald Green ] #059669 / #10B981   Founder track accents, grant funding badges, success stats
[ Light Slate ]   #F8FAFC / #F1F5F9   Main application canvas, card background fills
[ Border Muted ]  #E2E8F0 / #CBD5E1   Divider rules, card strokes, subtle input borders
[ Dark Charcoal ] #1E293B / #334155   Body prose, secondary descriptions, metadata
```

### 2.2 Semantic Color Mapping
* **Student Track (Scholarships):** Cobalt Blue (`#1D4ED8`) with Sky Tint accents (`#E0F2FE`).
* **Founder Track (Startup Grants):** Emerald Green (`#059669`) with Mint Tint accents (`#ECFDF5`).
* **Freemium Upgrade & Admin:** Amber Gold (`#D97706`) with Warm Cream accents (`#FEF3C7`).
* **Match Score Meter:** Gradient transitions from Amber (60-74%) to Sky Blue (75-84%) to Emerald (85-100%).

---

## 3. Typography & Hierarchy

### 3.1 Typeface Families
* **Primary Sans-Serif:** `Plus Jakarta Sans`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `sans-serif`.
  * Used for: Navigation, body text, buttons, form inputs, metadata chips, data tables.
* **Editorial Serif (Accent):** `Playfair Display` or `Newsreader`, `serif`.
  * Used for: Hero section emphasis phrases (e.g., *"Turn Ambition into Achievement"*), section sub-headings, pull-quotes.
* **Code / Numerical Monospace:** `JetBrains Mono`, `Consolas`, `monospace`.
  * Used for: Deadlines, funding currency values, match percentages, API keys.

### 3.2 Type Scale
* **Display / Hero H1:** 48px - 56px, Bold (700) / Extrabold (800), line-height 1.15.
* **Section Header H2:** 30px - 36px, Bold (700), line-height 1.25.
* **Card Title H3 / H4:** 18px - 20px, Semi-Bold (600), line-height 1.35.
* **Body Text:** 14px - 15px, Regular (400), line-height 1.6.
* **Metadata & Captions:** 11px - 12px, Medium (500), uppercase tracking +0.05em.

---

## 4. UI Component Architecture (Sample-Aligned)

### 4.1 Master Navigation Bar
* Sticky header with blur backdrop (`backdrop-blur-md`).
* Clean brand emblem with dual-tone logo ("GrantFinder **AI**").
* Track switcher links (`Scholarships`, `Startup Grants`, `Browse by Country`).
* User status cluster: Plan badge (`Free Tier` / `Premium Tier`), notification bell with unread indicator dot, user avatar/name chip, and clean sign-out action.

### 4.2 Hero Section (EEDU Point & Academic Synthesis)
* **Pill Category Badge:** Top rounded badge with blue tint (e.g. `[Hybrid AI Funding Discovery]`).
* **Dual-Style Headline:** Combination of bold sans-serif with italicized editorial serif (e.g., *"Your Bridge to Global Higher Education & Startup Capital"*).
* **Dual Action Cluster:** Primary button with arrow indicator (`Explore Opportunities ->`) paired with secondary white card button (`Build Your Profile`).
* **Social Proof & Impact Metrics:** Floating stats bar below hero:
  * `10,000+` Matching Opportunities Discovered
  * `PKR 75M+` Verified Non-Dilutive Grant Capital
  * `26+` Verified Government Portals
  * `98%` Semantic Matching Accuracy

### 4.3 Country & Regional Destination Grid
* Horizontal card scroll / responsive grid showcasing primary destinations:
  * **Pakistan:** HEC Indigenous, Ignite SEED, NIC Cohorts, Karandaaz, PEEF.
  * **United Kingdom:** Chevening, Commonwealth, Rhodes Oxford.
  * **United States:** Fulbright Program, Global UGRAD, Y Combinator.
  * **Germany:** DAAD EPOS, Research Internships in Science & Engineering.
  * **European Union:** Erasmus Mundus Joint Master Degrees.
* Each card includes the country flag, iconic landmark photo, active funding counter, and directional arrow link.

### 4.4 Four-Pillar Value Grid
* Clean white cards with light borders (`border-slate-200`) and soft hovering elevation.
* Color-tinted icon containers (Sky, Emerald, Amber, Indigo).
  1. **Curated Repositories:** Pre-seeded institutional data with zero stale records.
  2. **Live AI Web Crawling:** Serper-powered dynamic crawling for current deadlines.
  3. **Gemini Semantic Scoring:** Profile relevance explanation with transparent reasoning.
  4. **AI Application Assistant:** One-click Statement of Purpose and Pitch Proposal generation.

### 4.5 Dual-Track Dashboard View (Student & Founder)
* **Top Profile Summary Card:** Modern white card with subtle grey divider lines, editable inline fields (Discipline, Degree, GPA / Startup Domain, Stage, Capital ask).
* **Live Search Filter Bar:** Integrated search input with Country selector and Run Discovery button.
* **Opportunity Result Cards:**
  * Clean white card body with top badge row (Curated vs Live Web discovery, Country, Match Percentage pill).
  * Two-line truncated title with hover color transition.
  * Two-column metadata block: Funding amount in emerald green, deadline in slate monospace.
  * Bulleted match explanation items with green check bullets.
  * Card action footer: "Official Portal ->" outbound link, "Save Opportunity" button, and primary "Draft AI Essay / Pitch" button.
* **Locked Freemium Cards (Index 4+ on Free Tier):**
  * Translucent blurred overlay with subtle lock icon, masked funding and criteria, and high-conversion upgrade button ($9 Demo).

### 4.6 Accordion FAQ & Testimonial Section
* Interactive accordion questions addressing eligibility, accuracy, data freshness, and premium features.
* Student and Founder testimonial cards with verified avatar photos, quotes, program names, and five-star rating indicators.

---

## 5. API Ingestion & Account Configuration

To transition the backend from local heuristic simulation mode to live enterprise production, the following credentials can be supplied into the `.env` file under `Brain/Projects/GrantFinder-AI/.env`:

```bash
# 1. Live Web Search Engine (Serper.dev)
SERPER_API_KEY=your_serper_api_key_here

# 2. Google Gemini Generative AI (Google AI Studio)
GEMINI_API_KEY=your_gemini_api_key_here

# 3. Database Layer (Supabase PostgreSQL / MongoDB Atlas)
# Supabase connection URI example:
DATABASE_URL=postgresql://postgres.xxx:password@aws-0-region.pooler.supabase.com:6543/postgres

# 4. Instant WhatsApp Messaging (Twilio Sandbox)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# 5. Transactional Email Notifications (Gmail SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_specific_password
```
