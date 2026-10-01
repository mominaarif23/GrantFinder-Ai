# GrantFinder AI

An AI-powered discovery platform that connects university students with high-value academic scholarships and student founders with non-dilutive startup and innovation grants.

Instead of manually checking scattered university portals, government ministries, and private foundation directories, users build a profile once. The system finds, ranks, and matches opportunities through a **Hybrid Data Model** combining a verified, curated database of institutional funding programs with real-time AI-driven web search.

---

## 1. Core Architecture & Features

### 1.1 Hybrid Data Model
* **Curated Institutional Repository:** High-value, stable government and foundation sources (e.g. HEC Indigenous, PEEF, Fulbright, Chevening, Ignite SEED, Karandaaz Innovation Challenge, National Incubation Centers, PSEB) are audited and pre-seeded in the database.
* **Live AI-Driven Web Discovery:** University-specific grants, private endowments, and niche startup competitions are discovered dynamically via live search indexing (Serper.dev API) at search time.
* **Gemini AI Extraction & Semantic Scoring:** Raw search snippets are structured into verified cards with 0-100% semantic match scores and personalized rationales based on user profiles.

### 1.2 Dual Opportunity Tracks
* **Track 1: University Scholarships:** Matched against academic discipline, degree level (Undergraduate, Master's, Doctoral), semester standing, GPA, and regional preferences.
* **Track 2: Startup & Innovation Grants:** Matched against venture domain, maturity stage (Idea, Working Prototype, Launched Product, Growth), and required non-dilutive capital.

### 1.3 Role-Based Portals
* **Student Dashboard:** Academic profile builder, scholarship search, match explanations, opportunity saving, and an AI Statement of Purpose / Essay Drafter.
* **Founder Dashboard:** Startup profile builder, innovation grant discovery, bookmarking, and an AI Grant Pitch Proposal Drafter.
* **Administrator Portal:** Curated repository management (add/edit/delete verified programs), search telemetry analytics, and user account management.

### 1.4 Freemium Monetization Model (Demonstrated)
* **Free Tier:** Complete profile builder, top 3 visible matches per search, basic match percentage, in-app notifications, and email notifications.
* **Premium Tier ($9 One-Time Demo):** Unlimited matches (removes 3-result cutoff), detailed scoring breakdowns, AI Essay & Pitch Drafters, and instant Twilio WhatsApp alerts.

### 1.5 Multi-Channel Notifications
* **In-App Alerts:** Built-in notification bell dropdown for all users.
* **Email Notifications:** Dispatched via Gmail SMTP.
* **WhatsApp Instant Alerts:** Dispatched via Twilio WhatsApp sandbox for Premium tier users.

---

## 2. Technology Stack

* **Backend:** Python 3.10+ / FastAPI
* **Frontend:** Semantic HTML5, Tailwind CSS, Minimal Vanilla JavaScript (Jinja2 Server-Side Rendering)
* **Database:** SQLite (Local Development) / PostgreSQL / Supabase with clean abstraction layer
* **AI & Embeddings:** Google Gemini API (`gemini-1.5-flash`)
* **Search Engine:** Serper.dev Web Search API (with resilient heuristic fallback)
* **Messaging & Alerts:** Twilio WhatsApp Sandbox & SMTP Email
* **Testing:** Pytest & FastAPI TestClient

---

## 3. Directory Structure

```text
Brain/Projects/GrantFinder-AI/
├── app/
│   ├── auth.py                  # Cryptographic hashing (PBKDF2) & JWT tokens
│   ├── config.py                # Pydantic environment configuration
│   ├── db.py                    # SQLite schema, CRUD operations & pre-seeding
│   ├── main.py                  # FastAPI application entrypoint & static mount
│   ├── models.py                # Pydantic schemas & data entities
│   ├── routers/
│   │   ├── assistant_routes.py  # AI essay & pitch generation (freemium gated)
│   │   ├── auth_routes.py       # Register, login, logout, profile update
│   │   ├── dashboard_routes.py  # HTML views (student, founder, admin)
│   │   └── opportunity_routes.py# Live search, saving, and plan upgrade
│   ├── services/
│   │   ├── ai_service.py        # Gemini AI parsing & drafting
│   │   ├── curated_service.py   # Curated database queries & scoring
│   │   ├── notification_service.py # In-app, SMTP, and WhatsApp alerts
│   │   └── search_service.py    # Serper.dev API & fallback web index
│   ├── static/
│   │   ├── css/custom.css       # Refined scrollbars & glassmorphism accents
│   │   └── js/app.js            # Client-side async hooks & modal controls
│   └── templates/
│       ├── admin_dashboard.html # Superadmin analytics & curated manager
│       ├── base.html            # Master layout with navbar & upgrade modal
│       ├── founder_dashboard.html # Founder portal & pitch drafter
│       ├── index.html           # High-conversion dual-track landing page
│       ├── login.html           # Sign in view with demo prefill
│       ├── register.html        # Registration with role selector
│       └── student_dashboard.html # Student portal & essay drafter
├── data/
│   └── curated_opportunities.json # 26+ verified Pakistani & international programs
├── tests/
│   ├── test_api.py              # End-to-end API integration tests
│   ├── test_auth.py             # Auth & token unit tests
│   └── test_services.py         # Service & matching logic tests
├── .env.example                 # Environment configuration template
├── README.md                    # Project documentation
└── requirements.txt             # Python package dependencies
```

---

## 4. Getting Started

### 4.1 Prerequisites
* Python 3.10 or higher
* `pip` package manager

### 4.2 Installation
```bash
# Navigate to the project root
cd Brain/Projects/GrantFinder-AI

# Install dependencies
pip install -r requirements.txt
```

### 4.3 Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Optional)* Add your `GEMINI_API_KEY`, `SERPER_API_KEY`, or `TWILIO_ACCOUNT_SID`. If left blank, the application automatically uses its built-in resilient heuristic engines so all features function seamlessly offline or in local testing.

### 4.4 Running the Application
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Access the application at `http://127.0.0.1:8000`.

### 4.5 Default Administrator Credentials
* **Email:** `admin@grantfinder.ai`
* **Password:** `AdminPass123!`

---

## 5. Automated Verification

Run the test suite using `pytest`:
```bash
pytest tests/ -v
```

All tests validate:
1. User registration, password hashing, and role-based permissions.
2. Academic and venture profile matching against curated databases.
3. Live web search and structured AI parsing.
4. Freemium tier enforcement (top 3 visible on free; 402 block on AI drafters until upgraded).
5. Bookmark persistence and admin telemetry operations.

---

## 6. Zero-Cost Deployment Guidelines

* **Backend / API:** Deploy to **Render Free Tier** or **Railway Free Tier** with a Web Service pointing to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
* **Database:** Local SQLite for demo or **Supabase Free Tier (PostgreSQL)** by setting `DATABASE_URL=postgresql+asyncpg://...` in environment variables.
* **Frontend:** Served natively from FastAPI via Jinja2, or static assets deployed to **Vercel**.
