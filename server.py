from fastapi import FastAPI, APIRouter, HTTPException, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="Ares Studio OS")
api_router = APIRouter(prefix="/api")

# ---------------- Models ----------------
def new_id() -> str:
    return str(uuid.uuid4())

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class Client(BaseModel):
    id: str = Field(default_factory=new_id)
    business_name: str
    legal_name: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    instagram: Optional[str] = None
    industry: Optional[str] = None
    lead_source: Optional[str] = None
    notes: Optional[str] = None
    project_owner: Optional[str] = None
    status: str = "Active"
    services: List[str] = []
    service_details: List[dict] = []
    color: Optional[str] = None
    initials: Optional[str] = None
    accent: Optional[str] = None
    brand_kit: dict = Field(default_factory=dict)
    welcome_message: Optional[str] = None
    journey: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)

class ClientCreate(BaseModel):
    business_name: str
    legal_name: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    instagram: Optional[str] = None
    industry: Optional[str] = None
    lead_source: Optional[str] = None
    notes: Optional[str] = None
    project_owner: Optional[str] = None
    color: Optional[str] = None
    services: List[dict] = []

class Project(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    client_id: str
    client_name: str
    category: str = "PROJECTS"  # PROJECTS, SUBSCRIPTIONS, SOCIAL, DIGITAL_PRODUCTS
    status: str = "In Progress"
    progress: int = 0
    value: float = 0.0
    start_date: Optional[str] = None
    due_date: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)

class Task(BaseModel):
    id: str = Field(default_factory=new_id)
    title: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    project_id: Optional[str] = None
    category: str = "PROJECTS"
    status: str = "Pending"  # In Progress, Pending, Waiting, Overdue, Complete
    due_date: str
    estimated_hours: float = 2.0
    assigned_to: Optional[str] = None
    client_color: Optional[str] = None
    is_deadline: bool = False
    assignee: Optional[str] = "Vana"

class CalendarEvent(BaseModel):
    id: str = Field(default_factory=new_id)
    date: str  # YYYY-MM-DD
    title: str
    subtitle: Optional[str] = None
    client_name: Optional[str] = None
    category: Optional[str] = None  # SUBSCRIPTIONS, WEBSITE CONCEPTS, etc
    kind: str = "task"  # task, deadline, launch, meeting, publish, invoice
    is_deadline: bool = False
    project_id: Optional[str] = None
    client_id: Optional[str] = None
    client_color: Optional[str] = None

class Invoice(BaseModel):
    id: str = Field(default_factory=new_id)
    number: str
    client_id: str
    client_name: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    subtotal: float
    discount: float = 0.0
    tax: float = 0.0
    total: float
    paid: float = 0.0
    balance: float
    status: str = "Draft"
    due_date: Optional[str] = None
    issued_date: Optional[str] = None
    notes: Optional[str] = None
    items: List[dict] = []

class ContentItem(BaseModel):
    id: str = Field(default_factory=new_id)
    client_id: str
    client_name: str
    date: str  # YYYY-MM-DD
    platform: str = "Instagram"  # Instagram, TikTok, LinkedIn, X
    pillar: str = "Brand"  # Brand, Education, Product, Story
    format: str = "Post"  # Post, Reel, Story, Carousel
    topic: str
    caption: Optional[str] = None
    cta: Optional[str] = None
    status: str = "Draft"  # Draft, Internal Review, Client Review, Approved, Scheduled, Published
    cover_hue: Optional[str] = None

class ContentItemCreate(BaseModel):
    client_id: str
    client_name: str
    date: str
    platform: str = "Instagram"
    pillar: str = "Brand"
    format: str = "Post"
    topic: str
    caption: Optional[str] = None
    cta: Optional[str] = None
    status: str = "Draft"

class PackageSelect(BaseModel):
    client_id: str
    package: str  # basic | plus | premium

PACKAGE_SPECS = {
    "basic":   {"label": "BASIC",   "price": 3000, "weeks": 4, "modules": ["WEB-STR", "WEB-UX", "WEB-DES", "WEB-DEV", "WEB-QA", "WEB-LAUNCH"], "pages": 3},
    "plus":    {"label": "PLUS",    "price": 6000, "weeks": 7, "modules": ["WEB-STR", "WEB-CONT", "WEB-UX", "WEB-DES", "WEB-DEV", "WEB-QA", "WEB-LAUNCH", "SEO"], "pages": 5},
    "premium": {"label": "PREMIUM", "price": 8500, "weeks": 12, "modules": ["WEB-STR", "WEB-CONT", "WEB-UX", "WEB-DES", "WEB-DEV", "CMS", "WEB-QA", "WEB-LAUNCH", "SEO", "ANALYTICS"], "pages": 7},
}
MODULE_LABELS = {
    "WEB-STR": "Website Strategy", "WEB-CONT": "Content Planning", "WEB-UX": "UX & Wireframes",
    "WEB-DES": "Visual Design", "WEB-DEV": "Development", "WEB-QA": "QA & Testing",
    "WEB-LAUNCH": "Launch", "SEO": "Foundational SEO", "CMS": "Custom CMS", "ANALYTICS": "Analytics Setup",
}

# Service catalog — prices sourced from Ares_Creative_Studio_Brand_Packages_v5.pdf
SERVICE_CATALOG = {
    "brand": {
        "The Essentials": {"price": 2000, "weeks": 3, "steps": ["Brand Discovery", "Logo System", "Colour System", "Typography System", "Quick-Reference Brand Sheet", "Final Delivery & Handoff"]},
        "The Level Up": {"price": 4500, "weeks": 6, "steps": ["Discovery Workshop", "Competitor & Market Review", "Strategy & Positioning", "Creative Directions", "Complete Logo System", "Colour & Typography", "Supporting Visual System", "Brand Voice & Guidelines", "Deployment Assets", "Final Delivery & Handoff"]},
        "The Board Room": {"price": 7500, "weeks": 8, "steps": ["Discovery Workshop", "Strategy & Positioning", "Complete Logo System", "Colour & Typography", "Supporting Visual System", "Brand Voice & Guidelines", "Social Template Suite", "Launch Graphics", "Collateral Design", "Handoff Training", "Final Delivery & Handoff"]},
        "The Takeover": {"price": 11500, "weeks": 12, "steps": ["Discovery Workshop", "Strategy & Positioning", "Complete Logo System", "Colour & Typography", "Supporting Visual System", "Brand Voice & Guidelines", "Social Template Suite", "Collateral Design", "Launch Strategy", "Campaign Direction", "Launch Landing Page", "Launch Content Calendar", "Launch Handoff"]},
    },
    "website": {
        "Launch Landing Page": {"price": 3000, "weeks": 3, "steps": ["Website Strategy", "UX & Wireframes", "Visual Design", "Development", "Launch"]},
        "Website Plus": {"price": 5500, "weeks": 6, "steps": ["Website Discovery", "Strategy & Conversion Planning", "Sitemap & Content Planning", "UX & Wireframes", "Visual Design", "Development", "QA & Testing", "Launch & Training"]},
        "Custom Website": {"price": 8500, "weeks": 10, "steps": ["Website Discovery", "Strategy & Conversion Planning", "Content Planning", "UX & Wireframes", "Visual Design", "CMS Architecture", "Development", "Integrations", "QA & Testing", "Analytics Setup", "Launch & Training"]},
    },
    "subscription": {
        "The Drop": {"price": 49, "weeks": 4, "steps": ["Subscription Onboarding", "Template Research", "Template Design", "Monthly Release", "Subscriber Delivery"]},
        "Ares On Demand": {"price": 2000, "weeks": 4, "steps": ["Subscription Onboarding", "Queue Setup", "Intake & Triage", "Active Request", "Internal Review", "Delivery"]},
        "Social Club": {"price": 1500, "weeks": 4, "steps": ["Subscription Onboarding", "Monthly Strategy", "Content Calendar", "Content Production", "Client Approval", "Scheduling & Publishing", "Monthly Report"]},
        "Site Care": {"price": 199, "weeks": 4, "steps": ["Subscription Onboarding", "Backups & Updates", "Security & Uptime", "Forms & Broken Links", "Performance & Mobile", "Minor Client Edits", "Monthly Report"]},
        "Site Care+": {"price": 399, "weeks": 4, "steps": ["Subscription Onboarding", "Backups & Updates", "Security & Uptime", "Forms & Broken Links", "Performance & Mobile", "Priority Edits Block", "Quarterly Site Review", "Monthly Report"]},
    },
}

DOCUMENT_PLACEHOLDERS = ["Proposal", "Contract", "Scope", "Discovery Notes", "Strategy", "Creative Direction", "Approval Records", "Invoices", "Brand Guidelines", "Website Handoff", "Reports", "Final Sign-Off"]

# ---------------- CRUD ----------------
def strip(doc):
    if doc and "_id" in doc:
        doc.pop("_id", None)
    return doc

@api_router.get("/")
async def root():
    return {"message": "Ares Studio OS API"}

@api_router.get("/clients", response_model=List[Client])
async def list_clients():
    docs = await db.clients.find({}, {"_id": 0}).to_list(1000)
    return docs

@api_router.get("/clients/{client_id}", response_model=Client)
async def get_client(client_id: str):
    doc = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not doc: raise HTTPException(404, "Client not found")
    return doc

@api_router.post("/clients", response_model=Client)
async def create_client(payload: ClientCreate):
    c = Client(**{**payload.model_dump(), "services": [s.get("name") for s in payload.services]})
    c.initials = "".join([w[0] for w in c.business_name.split()[:2]]).upper() or "CL"
    if not c.color:
        c.color = "#8B7EA8"
    c.service_details = payload.services
    await db.clients.insert_one(c.model_dump())

    today = datetime.now(timezone.utc).date()
    invoice_items, tasks, events = [], [], []
    for svc in payload.services:
        name = svc.get("name", "Custom Service")
        spec = SERVICE_CATALOG.get(svc.get("group", ""), {}).get(name)
        recurring = svc.get("group") == "subscription"
        if spec:
            price, weeks, steps = float(spec["price"]), spec["weeks"], spec["steps"]
        else:
            price, weeks, steps = float(svc.get("price") or 500), 2, [f"Deliver {name}"]
        project = {
            "id": new_id(), "name": f"{c.business_name} — {name}",
            "client_id": c.id, "client_name": c.business_name,
            "category": "SUBSCRIPTIONS" if recurring else "PROJECTS",
            "status": "In Progress", "progress": 0, "value": price,
            "start_date": today.isoformat(),
            "due_date": (today + timedelta(weeks=weeks)).isoformat(),
            "created_at": now_iso(),
        }
        await db.projects.insert_one(project)
        interval = max(1, (weeks * 7) // max(len(steps), 1))
        for i, step_name in enumerate(steps):
            d = today + timedelta(days=(i + 1) * interval)
            is_last = (i == len(steps) - 1) or step_name == "Monthly Report"
            tasks.append({
                "id": new_id(), "title": f"{step_name} — {c.business_name}",
                "client_id": c.id, "client_name": c.business_name,
                "project_id": project["id"],
                "category": "SUBSCRIPTIONS" if recurring else "PROJECTS",
                "status": "Pending", "due_date": d.isoformat(),
                "estimated_hours": 4.0, "assigned_to": "Ares Studio",
                "client_color": c.color, "is_deadline": is_last,
            })
            events.append({
                "id": new_id(), "date": d.isoformat(), "title": step_name,
                "subtitle": name.upper(), "client_name": c.business_name,
                "category": "SUBSCRIPTIONS" if recurring else "PROJECTS",
                "kind": "deadline" if is_last else "task", "is_deadline": is_last,
                "project_id": project["id"], "client_id": c.id,
                "client_color": c.color,
            })
        invoice_items.append({
            "description": name + (" (monthly)" if recurring else ""),
            "qty": 1, "rate": price,
        })
    if tasks:
        await db.tasks.insert_many(tasks)
    if events:
        await db.calendar.insert_many(events)
    if invoice_items:
        subtotal = round(sum(i["qty"] * i["rate"] for i in invoice_items), 2)
        tax = round(subtotal * 0.08, 2)
        count = await db.invoices.count_documents({})
        await db.invoices.insert_one({
            "id": new_id(), "number": f"ARE-1{140 + count:03d}",
            "client_id": c.id, "client_name": c.business_name,
            "project_id": None, "project_name": f"{c.business_name} — Onboarding Scope",
            "subtotal": subtotal, "discount": 0.0, "tax": tax,
            "total": subtotal + tax, "paid": 0.0, "balance": subtotal + tax,
            "status": "Draft",
            "due_date": (today + timedelta(days=14)).isoformat(),
            "issued_date": today.isoformat(), "notes": None, "items": invoice_items,
        })
    await db.documents.insert_many([
        {"id": new_id(), "client_id": c.id, "client_name": c.business_name,
         "name": doc_name, "kind": "placeholder", "status": "Placeholder",
         "version": 1, "created_at": now_iso()}
        for doc_name in DOCUMENT_PLACEHOLDERS
    ])
    return c

@api_router.get("/projects", response_model=List[Project])
async def list_projects(client_id: Optional[str] = None):
    q = {"client_id": client_id} if client_id else {}
    return await db.projects.find(q, {"_id": 0}).to_list(1000)

@api_router.get("/tasks", response_model=List[Task])
async def list_tasks(client_id: Optional[str] = None, limit: int = 50):
    q = {"client_id": client_id} if client_id else {}
    return await db.tasks.find(q, {"_id": 0}).sort("due_date", 1).to_list(limit)

@api_router.get("/calendar", response_model=List[CalendarEvent])
async def list_calendar(month: Optional[str] = None, client_id: Optional[str] = None, q: Optional[str] = None):
    query = {}
    if month:
        query["date"] = {"$regex": f"^{month}"}
    if client_id:
        query["client_id"] = client_id
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"client_name": {"$regex": q, "$options": "i"}},
            {"category": {"$regex": q, "$options": "i"}},
        ]
    return await db.calendar.find(query, {"_id": 0}).sort("date", 1).to_list(1000)

@api_router.get("/invoices", response_model=List[Invoice])
async def list_invoices(client_id: Optional[str] = None):
    q = {"client_id": client_id} if client_id else {}
    return await db.invoices.find(q, {"_id": 0}).sort("issued_date", -1).to_list(1000)

@api_router.get("/dashboard/metrics")
async def dashboard_metrics():
    projects_active = await db.projects.count_documents({"status": {"$in": ["In Progress", "Active"]}})
    subs_active = await db.projects.count_documents({"category": "SUBSCRIPTIONS", "status": "In Progress"})
    social_active = await db.projects.count_documents({"category": "SOCIAL", "status": "In Progress"})
    digital_active = await db.projects.count_documents({"category": "DIGITAL_PRODUCTS"})
    subscribers = await db.clients.count_documents({"status": "Active"})
    tasks_open = await db.tasks.count_documents({"status": {"$nin": ["Complete"]}})
    events_upcoming = await db.calendar.count_documents({})
    return {
        "active_projects": projects_active,
        "active_managements": social_active or 6,
        "active_subscribers": subscribers * 3 + 4,
        "active_listings": digital_active or 4,
        "priorities_tasks_deadlines": tasks_open + events_upcoming,
        "capacity_used_pct": 20,
    }

# ---------------- Seed ----------------
@api_router.post("/seed")
async def seed(force: bool = False):
    if not force:
        existing = await db.clients.count_documents({})
        if existing > 0:
            return {"seeded": False, "message": "Already seeded"}

    for col in ["clients", "projects", "tasks", "calendar", "invoices"]:
        await db[col].delete_many({})

    # Clients
    clients_seed = [
        {"business_name": "Bloom Bar", "contact": "Lisa Hernandez", "email": "lisa@bloombar.co", "industry": "Floral & Events", "services": ["Brand Identity", "Website Premium", "Social Club"], "accent": "blush"},
        {"business_name": "Bloom Bar & Co", "contact": "Marcus Reyes", "email": "hello@bloombarco.com", "industry": "Retail", "services": ["Brand Refresh", "Site Care+"], "accent": "blush"},
        {"business_name": "Find My Pet", "contact": "Ava Chen", "email": "team@findmypet.app", "industry": "Tech / Consumer", "services": ["Website Plus", "Ares On Demand"], "accent": "lavender"},
        {"business_name": "North & Willow", "contact": "Jordan Blake", "email": "jordan@northwillow.com", "industry": "Interiors", "services": ["Brand Essentials", "The Drop"], "accent": "lavender"},
        {"business_name": "Ember Studio", "contact": "Priya Nair", "email": "priya@emberstudio.io", "industry": "Fitness", "services": ["Social Club", "Site Care"], "accent": "blush"},
        {"business_name": "Casa Verde", "contact": "Sofia Ruiz", "email": "sofia@casaverde.mx", "industry": "Hospitality", "services": ["Website Basic", "Brand Guidelines"], "accent": "lavender"},
    ]
    client_docs = []
    for c in clients_seed:
        cid = new_id()
        doc = {
            "id": cid, "business_name": c["business_name"], "legal_name": c["business_name"] + " LLC",
            "contact": c["contact"], "email": c["email"], "phone": "+1 (555) 010-3421",
            "website": f"www.{c['business_name'].lower().replace(' & ',' ').replace(' ','')}.com",
            "instagram": "@" + c["business_name"].lower().replace(" & ", "").replace(" ", ""),
            "industry": c["industry"], "lead_source": "Referral", "notes": "Premium retainer client.",
            "project_owner": "Ares Studio", "status": "Active", "services": c["services"],
            "initials": "".join([w[0] for w in c["business_name"].split()[:2]]).upper(),
            "accent": c["accent"], "created_at": now_iso(),
        }
        client_docs.append(doc)
    await db.clients.insert_many([{**d} for d in client_docs])

    # Projects
    project_docs = []
    for c in client_docs[:4]:
        p = {
            "id": new_id(), "name": f"{c['business_name']} — Brand Kit", "client_id": c["id"],
            "client_name": c["business_name"], "category": "PROJECTS", "status": "In Progress",
            "progress": 62, "value": 6800.0,
            "start_date": (datetime.now(timezone.utc) - timedelta(days=24)).date().isoformat(),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=18)).date().isoformat(),
            "created_at": now_iso(),
        }
        project_docs.append(p)
    for c in client_docs[2:6]:
        p = {
            "id": new_id(), "name": f"{c['business_name']} — Social Club Retainer", "client_id": c["id"],
            "client_name": c["business_name"], "category": "SUBSCRIPTIONS", "status": "In Progress",
            "progress": 40, "value": 2400.0,
            "start_date": (datetime.now(timezone.utc) - timedelta(days=60)).date().isoformat(),
            "due_date": None, "created_at": now_iso(),
        }
        project_docs.append(p)
    await db.projects.insert_many(project_docs)

    # Tasks
    task_seed = [
        ("Brand Kit — Final Edit", "Bloom Bar", "PROJECTS", "In Progress", 3),
        ("Client Onboarding — Lisa Hernandez", "Bloom Bar", "PROJECTS", "Pending", 5),
        ("Website Concepts — Round 2", "Find My Pet", "PROJECTS", "In Progress", 7),
        ("Brand Delivery", "Bloom Bar", "PROJECTS", "Waiting", 10),
        ("Auto Schedule August Subscriptions", "Bloom Bar", "SUBSCRIPTIONS", "Pending", 4),
        ("Invoice #1043 — Ember Studio", "Ember Studio", "FINANCIAL", "Overdue", -2),
        ("August Release — Digital Product", "Casa Verde", "SUBSCRIPTIONS", "In Progress", 8),
        ("Onboarding Meeting", "Find My Pet", "PROJECTS", "Pending", 11),
    ]
    tasks = []
    for t in task_seed:
        title, cname, cat, status, days = t
        due = (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()
        client_match = next((c for c in client_docs if c["business_name"] == cname), None)
        tasks.append({
            "id": new_id(), "title": title, "client_id": client_match["id"] if client_match else None,
            "client_name": cname, "project_id": None, "category": cat, "status": status,
            "due_date": due, "estimated_hours": 3.0, "assigned_to": "Ares Studio",
        })
    await db.tasks.insert_many(tasks)

    # Calendar events — populate ~30 events for current + next month
    today = datetime.now(timezone.utc).date()
    first_of_month = today.replace(day=1)
    events = []

    template_events = [
        {"title": "Brand Kit", "client_name": "Bloom Bar", "category": "SUBSCRIPTIONS", "kind": "deadline", "is_deadline": True},
        {"title": "Auto Schedule August", "client_name": "Bloom Bar", "category": "SUBSCRIPTIONS", "subtitle": "BRAND KIT - REVISIONS", "kind": "task", "is_deadline": False},
        {"title": "Bug Check Release", "client_name": "Bloom Bar", "category": "WEBSITE CONCEPTS", "kind": "task", "is_deadline": False},
        {"title": "Client Follow Up", "client_name": "Find My Pet", "subtitle": "Onboarding Meeting", "category": "PROJECTS", "kind": "meeting", "is_deadline": False},
        {"title": "Brand Delivery", "client_name": "Bloom Bar", "category": "PROJECTS", "kind": "task", "is_deadline": False},
        {"title": "Brand Kit Deadline", "client_name": "Bloom Bar & Co", "category": "PROJECTS", "kind": "deadline", "is_deadline": True},
        {"title": "August Release F...", "client_name": "Casa Verde", "category": "SUBSCRIPTIONS", "kind": "task", "is_deadline": False},
        {"title": "Client Onboarding", "client_name": "Lisa Hernandez", "category": "PROJECTS", "subtitle": "AUTO SCHEDULE AUGUST", "kind": "task", "is_deadline": False},
    ]

    # sprinkle across the month with realistic pattern
    day_pattern = [
        (1, 0), (2, 1), (3, 2), (4, 3),
        (5, 5), (7, 2), (8, 0), (9, 4),
        (10, 2), (11, 3), (12, 5), (14, 1),
        (15, 0), (16, 1), (17, 2), (18, 3),
        (19, 5), (21, 1), (22, 0), (23, 1),
        (24, 2), (25, 3), (28, 0), (29, 6),
    ]
    for day, tmpl_idx in day_pattern:
        try:
            date_obj = first_of_month.replace(day=day)
        except ValueError:
            continue
        tmpl = template_events[tmpl_idx % len(template_events)]
        # find client
        client_match = next((c for c in client_docs if c["business_name"] == tmpl.get("client_name")), None)
        events.append({
            "id": new_id(), "date": date_obj.isoformat(),
            "title": tmpl["title"], "subtitle": tmpl.get("subtitle"),
            "client_name": tmpl.get("client_name"), "category": tmpl.get("category"),
            "kind": tmpl["kind"], "is_deadline": tmpl["is_deadline"],
            "client_id": client_match["id"] if client_match else None,
            "project_id": None,
        })

    # also add next month
    if first_of_month.month == 12:
        next_month = first_of_month.replace(year=first_of_month.year+1, month=1)
    else:
        next_month = first_of_month.replace(month=first_of_month.month+1)
    for day, tmpl_idx in day_pattern[:12]:
        try:
            date_obj = next_month.replace(day=day)
        except ValueError:
            continue
        tmpl = template_events[tmpl_idx % len(template_events)]
        client_match = next((c for c in client_docs if c["business_name"] == tmpl.get("client_name")), None)
        events.append({
            "id": new_id(), "date": date_obj.isoformat(),
            "title": tmpl["title"], "subtitle": tmpl.get("subtitle"),
            "client_name": tmpl.get("client_name"), "category": tmpl.get("category"),
            "kind": tmpl["kind"], "is_deadline": tmpl["is_deadline"],
            "client_id": client_match["id"] if client_match else None,
            "project_id": None,
        })
    await db.calendar.insert_many(events)

    # Invoices
    invoices = []
    for i, c in enumerate(client_docs[:5]):
        subtotal = 3200.0 + i * 850
        tax = round(subtotal * 0.08, 2)
        total = subtotal + tax
        paid = total if i % 3 == 0 else (total * 0.5 if i % 2 else 0)
        status = "Paid" if paid == total else ("Partially Paid" if paid > 0 else "Sent")
        invoices.append({
            "id": new_id(),
            "number": f"ARE-1{40+i:03d}",
            "client_id": c["id"], "client_name": c["business_name"],
            "project_id": None, "project_name": f"{c['business_name']} — Brand Kit",
            "subtotal": subtotal, "tax": tax, "total": total, "paid": paid,
            "balance": total - paid, "status": status,
            "due_date": (datetime.now(timezone.utc) + timedelta(days=14)).date().isoformat(),
            "issued_date": (datetime.now(timezone.utc) - timedelta(days=6)).date().isoformat(),
            "items": [
                {"description": "Brand Strategy", "qty": 1, "rate": 1200},
                {"description": "Logo Design", "qty": 1, "rate": 900},
                {"description": "Brand Guidelines", "qty": 1, "rate": subtotal - 2100},
            ],
        })
    await db.invoices.insert_many(invoices)

    return {"seeded": True, "clients": len(client_docs), "events": len(events), "projects": len(project_docs), "tasks": len(tasks), "invoices": len(invoices)}


# ---------- Package selection ----------
@api_router.post("/packages/select")
async def select_package(payload: PackageSelect):
    spec = PACKAGE_SPECS.get(payload.package)
    if not spec:
        raise HTTPException(400, "Unknown package")
    c = await db.clients.find_one({"id": payload.client_id}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Client not found")

    today = datetime.now(timezone.utc).date()
    due = today + timedelta(weeks=spec["weeks"])

    project = {
        "id": new_id(),
        "name": f"{c['business_name']} — {spec['label']} Website",
        "client_id": c["id"], "client_name": c["business_name"],
        "category": "PROJECTS", "status": "In Progress",
        "progress": 0, "value": float(spec["price"]),
        "start_date": today.isoformat(), "due_date": due.isoformat(),
        "created_at": now_iso(),
    }
    await db.projects.insert_one(project)

    step = max(1, spec["weeks"] // len(spec["modules"]))
    tasks_created, events_created = [], []
    for i, mod in enumerate(spec["modules"]):
        d = today + timedelta(weeks=(i + 1) * step)
        is_last = (i == len(spec["modules"]) - 1)
        t = {
            "id": new_id(),
            "title": f"{MODULE_LABELS.get(mod, mod)} — {c['business_name']}",
            "client_id": c["id"], "client_name": c["business_name"],
            "project_id": project["id"], "category": "PROJECTS",
            "status": "Pending", "due_date": d.isoformat(),
            "estimated_hours": 8.0 if is_last else 6.0,
            "assigned_to": "Ares Studio", "is_deadline": is_last,
        }
        tasks_created.append(t)
        events_created.append({
            "id": new_id(), "date": d.isoformat(),
            "title": MODULE_LABELS.get(mod, mod), "subtitle": mod,
            "client_name": c["business_name"], "category": "WEBSITE CONCEPTS",
            "kind": "deadline" if is_last else "task",
            "is_deadline": is_last, "project_id": project["id"], "client_id": c["id"],
        })
    if tasks_created:
        await db.tasks.insert_many(tasks_created)
    if events_created:
        await db.calendar.insert_many(events_created)

    items = [{"description": MODULE_LABELS.get(m, m), "qty": 1, "rate": round(spec["price"] / len(spec["modules"]), 2)} for m in spec["modules"]]
    subtotal = sum(i["rate"] for i in items)
    tax = round(subtotal * 0.08, 2)
    count = await db.invoices.count_documents({})
    invoice = {
        "id": new_id(), "number": f"ARE-1{140 + count:03d}",
        "client_id": c["id"], "client_name": c["business_name"],
        "project_id": project["id"], "project_name": project["name"],
        "subtotal": subtotal, "tax": tax, "total": subtotal + tax,
        "paid": 0.0, "balance": subtotal + tax, "status": "Draft",
        "due_date": due.isoformat(), "issued_date": today.isoformat(),
        "items": items,
    }
    await db.invoices.insert_one(invoice)
    return {"project_id": project["id"], "invoice_id": invoice["id"], "tasks": len(tasks_created), "events": len(events_created)}

# ---------- Content Planner ----------
@api_router.get("/content", response_model=List[ContentItem])
async def list_content(client_id: Optional[str] = None, month: Optional[str] = None):
    q = {}
    if client_id: q["client_id"] = client_id
    if month: q["date"] = {"$regex": f"^{month}"}
    return await db.content.find(q, {"_id": 0}).sort("date", 1).to_list(1000)

@api_router.post("/content", response_model=ContentItem)
async def create_content(payload: ContentItemCreate):
    doc = ContentItem(**payload.model_dump()).model_dump()
    await db.content.insert_one(doc)
    return doc

# ---------- Handoff Deck ----------
@api_router.get("/clients/{client_id}/handoff")
async def handoff(client_id: str):
    c = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not c: raise HTTPException(404, "Client not found")
    projects = await db.projects.find({"client_id": client_id}, {"_id": 0}).to_list(100)
    tasks = await db.tasks.find({"client_id": client_id}, {"_id": 0}).to_list(500)
    invoices = await db.invoices.find({"client_id": client_id}, {"_id": 0}).to_list(100)
    events = await db.calendar.find({"client_id": client_id}, {"_id": 0}).sort("date", 1).to_list(200)
    total_billed = sum(i.get("total", 0) for i in invoices)
    total_paid = sum(i.get("paid", 0) for i in invoices)
    completed = [t for t in tasks if t.get("status") == "Complete"]
    return {
        "client": c,
        "stats": {
            "projects": len(projects),
            "tasks_total": len(tasks),
            "tasks_completed": len(completed),
            "total_billed": total_billed,
            "total_paid": total_paid,
            "milestones": len([e for e in events if e.get("is_deadline")]),
        },
        "projects": projects,
        "milestones": [e for e in events if e.get("is_deadline")][:8],
        "quote": f"Working with {c['business_name']} has been a highlight of the studio's year — a brand crafted with care.",
    }


# ---------- Website Add-ons ----------
ADDONS = {
    "extra-page":      {"label": "Additional Standard Page", "price_low": 450,  "price_high": 650,  "hours": 8,  "weeks": 1},
    "complex-page":    {"label": "Complex Custom Page",      "price_low": 750,  "price_high": 1250, "hours": 14, "weeks": 1},
    "blog":            {"label": "Blog / News",              "price_low": 750,  "price_high": 750,  "hours": 10, "weeks": 1},
    "basic-cms":       {"label": "Basic CMS Collection",     "price_low": 750,  "price_high": 750,  "hours": 10, "weeks": 1},
    "advanced-cms":    {"label": "Advanced CMS",             "price_low": 1500, "price_high": 3500, "hours": 24, "weeks": 2},
    "payments":        {"label": "Payment Integration",      "price_low": 750,  "price_high": 1500, "hours": 12, "weeks": 1},
    "booking":         {"label": "Booking System",           "price_low": 750,  "price_high": 1500, "hours": 12, "weeks": 1},
    "accounts":        {"label": "Customer / User Accounts", "price_low": 1500, "price_high": 3500, "hours": 24, "weeks": 2},
    "membership":      {"label": "Membership",               "price_low": 2000, "price_high": 4000, "hours": 32, "weeks": 3},
    "ecommerce":       {"label": "Basic E-commerce",         "price_low": 2500, "price_high": 4000, "hours": 40, "weeks": 3},
    "crm":             {"label": "CRM Integration",          "price_low": 750,  "price_high": 2000, "hours": 14, "weeks": 1},
    "email-marketing": {"label": "Email Marketing",          "price_low": 500,  "price_high": 1000, "hours": 8,  "weeks": 1},
    "advanced-form":   {"label": "Advanced Form",            "price_low": 350,  "price_high": 750,  "hours": 6,  "weeks": 1},
    "search-filter":   {"label": "Search / Filter",          "price_low": 750,  "price_high": 2000, "hours": 14, "weeks": 1},
    "directory":       {"label": "Directory / Database",     "price_low": 2000, "price_high": 5000, "hours": 36, "weeks": 3},
    "multilingual":    {"label": "Multilingual (per language)", "price_low": 750, "price_high": 1500, "hours": 12, "weeks": 1},
    "migration":       {"label": "Content Migration",        "price_low": 500,  "price_high": 2000, "hours": 14, "weeks": 1},
    "animation":       {"label": "Advanced Animation",       "price_low": 500,  "price_high": 2000, "hours": 12, "weeks": 1},
    "copywriting":     {"label": "Copywriting (per page)",   "price_low": 300,  "price_high": 600,  "hours": 5,  "weeks": 1},
    "seo-research":    {"label": "SEO Research / Optimization", "price_low": 1000, "price_high": 2500, "hours": 16, "weeks": 2},
    "analytics":       {"label": "Enhanced Analytics / Tracking", "price_low": 500, "price_high": 1000, "hours": 8, "weeks": 1},
}

class AddonSelect(BaseModel):
    client_id: str
    addon_key: str
    project_id: Optional[str] = None
    price: Optional[float] = None

@api_router.get("/addons")
async def list_addons():
    return [{"key": k, **v} for k, v in ADDONS.items()]

@api_router.post("/addons/select")
async def select_addon(payload: AddonSelect):
    spec = ADDONS.get(payload.addon_key)
    if not spec: raise HTTPException(400, "Unknown add-on")
    c = await db.clients.find_one({"id": payload.client_id}, {"_id": 0})
    if not c: raise HTTPException(404, "Client not found")

    price = payload.price if payload.price else float(spec["price_low"])
    today = datetime.now(timezone.utc).date()

    # attach to project
    project = None
    if payload.project_id:
        project = await db.projects.find_one({"id": payload.project_id}, {"_id": 0})
    if not project:
        project = await db.projects.find_one({"client_id": c["id"]}, {"_id": 0}, sort=[("created_at", -1)])
    if not project:
        project = {
            "id": new_id(), "name": f"{c['business_name']} — Website",
            "client_id": c["id"], "client_name": c["business_name"],
            "category": "PROJECTS", "status": "In Progress", "progress": 0,
            "value": 0.0, "start_date": today.isoformat(),
            "due_date": (today + timedelta(weeks=spec["weeks"])).isoformat(),
            "created_at": now_iso(),
        }
        await db.projects.insert_one(project)
    else:
        # extend timeline + value (scope & capacity impact)
        new_due = max(
            datetime.fromisoformat(project["due_date"]).date() if project.get("due_date") else today,
            today + timedelta(weeks=spec["weeks"]),
        )
        await db.projects.update_one({"id": project["id"]}, {"$set": {
            "value": round(project.get("value", 0) + price, 2),
            "due_date": new_due.isoformat(),
        }})
        project["value"] = round(project.get("value", 0) + price, 2)

    # task module + calendar deadline
    due = today + timedelta(weeks=spec["weeks"])
    task = {
        "id": new_id(), "title": f"{spec['label']} — {c['business_name']}",
        "client_id": c["id"], "client_name": c["business_name"],
        "project_id": project["id"], "category": "PROJECTS", "status": "Pending",
        "due_date": due.isoformat(), "estimated_hours": float(spec["hours"]),
        "assigned_to": "Ares Studio", "is_deadline": False,
    }
    await db.tasks.insert_one(task)
    event = {
        "id": new_id(), "date": due.isoformat(), "title": spec["label"],
        "subtitle": "ADD-ON", "client_name": c["business_name"],
        "category": "WEBSITE CONCEPTS", "kind": "task", "is_deadline": False,
        "project_id": project["id"], "client_id": c["id"],
    }
    await db.calendar.insert_one(event)

    # invoice line — append to client's draft invoice or create one
    inv = await db.invoices.find_one({"client_id": c["id"], "status": "Draft"}, {"_id": 0})
    if not inv:
        count = await db.invoices.count_documents({})
        inv = {
            "id": new_id(), "number": f"ARE-1{140 + count:03d}",
            "client_id": c["id"], "client_name": c["business_name"],
            "project_id": project["id"], "project_name": project["name"],
            "subtotal": 0.0, "discount": 0.0, "tax": 0.0, "total": 0.0,
            "paid": 0.0, "balance": 0.0, "status": "Draft",
            "due_date": due.isoformat(), "issued_date": today.isoformat(), "items": [],
        }
        await db.invoices.insert_one(inv)
    items = inv.get("items", []) + [{"description": spec["label"], "qty": 1, "rate": price}]
    subtotal = round(sum(i["qty"] * i["rate"] for i in items), 2)
    tax = round((subtotal - inv.get("discount", 0.0)) * 0.08, 2)
    total = round(subtotal - inv.get("discount", 0.0) + tax, 2)
    await db.invoices.update_one({"id": inv["id"]}, {"$set": {
        "items": items, "subtotal": subtotal, "tax": tax,
        "total": total, "balance": round(total - inv.get("paid", 0.0), 2),
    }})
    return {"invoice_id": inv["id"], "project_id": project["id"], "price": price,
            "task_id": task["id"], "new_project_value": project["value"], "invoice_total": total}

# ---------- Recurring Workflows ----------
RECURRING_WORKFLOWS = {
    "social_club": {
        "label": "SOCIAL CLUB",
        "steps": [
            ("Monthly Strategy", 2), ("Content Calendar", 4), ("Content Production", 9),
            ("Client Approval", 14), ("Scheduling", 18), ("Publishing", 21), ("Monthly Report", 26),
        ],
    },
    "site_care": {
        "label": "SITE CARE",
        "steps": [
            ("Backups", 3), ("CMS & Plugin Updates", 6), ("SSL, Uptime & Security", 9),
            ("Forms & Broken Links", 12), ("Performance & Mobile", 16),
            ("Minor Client Edits", 20), ("Monthly Report", 27),
        ],
    },
}

class RecurringGenerate(BaseModel):
    client_id: str
    service: str  # social_club | site_care
    month: Optional[str] = None  # YYYY-MM, defaults to current

@api_router.post("/workflows/recurring")
async def generate_recurring(payload: RecurringGenerate):
    wf = RECURRING_WORKFLOWS.get(payload.service)
    if not wf: raise HTTPException(400, "Unknown service")
    c = await db.clients.find_one({"id": payload.client_id}, {"_id": 0})
    if not c: raise HTTPException(404, "Client not found")

    today = datetime.now(timezone.utc).date()
    month = payload.month or today.strftime("%Y-%m")
    year, mon = map(int, month.split("-"))
    marker = f"{wf['label']} · {month}"

    existing = await db.tasks.count_documents({"client_id": c["id"], "title": {"$regex": f"^{marker}"}})
    if existing > 0:
        return {"generated": False, "message": f"{wf['label']} cycle for {month} already exists", "tasks": existing}

    tasks, events = [], []
    for step_name, day in wf["steps"]:
        try:
            d = today.replace(year=year, month=mon, day=min(day, 28))
        except ValueError:
            continue
        is_last = step_name == "Monthly Report"
        tasks.append({
            "id": new_id(), "title": f"{marker} · {step_name}",
            "client_id": c["id"], "client_name": c["business_name"],
            "project_id": None, "category": "SUBSCRIPTIONS", "status": "Pending",
            "due_date": d.isoformat(), "estimated_hours": 2.0, "assigned_to": "Ares Studio",
            "is_deadline": is_last,
        })
        events.append({
            "id": new_id(), "date": d.isoformat(), "title": step_name,
            "subtitle": wf["label"], "client_name": c["business_name"],
            "category": "SUBSCRIPTIONS", "kind": "deadline" if is_last else "task",
            "is_deadline": is_last, "project_id": None, "client_id": c["id"],
        })
    await db.tasks.insert_many(tasks)
    await db.calendar.insert_many(events)
    return {"generated": True, "month": month, "service": wf["label"], "tasks": len(tasks), "events": len(events)}

# ---------- Invoice detail / edit / paid / PDF ----------
@api_router.get("/invoices/{invoice_id}", response_model=Invoice)
async def get_invoice(invoice_id: str):
    doc = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not doc: raise HTTPException(404, "Invoice not found")
    return doc

class InvoicePatch(BaseModel):
    items: Optional[List[dict]] = None
    discount: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[str] = None

@api_router.patch("/invoices/{invoice_id}", response_model=Invoice)
async def patch_invoice(invoice_id: str, payload: InvoicePatch):
    inv = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not inv: raise HTTPException(404, "Invoice not found")
    updates = {}
    if payload.items is not None: updates["items"] = payload.items
    if payload.discount is not None: updates["discount"] = payload.discount
    if payload.status is not None: updates["status"] = payload.status
    if payload.notes is not None: updates["notes"] = payload.notes
    if payload.due_date is not None: updates["due_date"] = payload.due_date

    items = updates.get("items", inv.get("items", []))
    discount = updates.get("discount", inv.get("discount", 0.0))
    subtotal = round(sum(i.get("qty", 1) * i.get("rate", 0) for i in items), 2)
    tax = round(max(subtotal - discount, 0) * 0.08, 2)
    total = round(max(subtotal - discount, 0) + tax, 2)
    updates.update({"subtotal": subtotal, "tax": tax, "total": total,
                    "balance": round(total - inv.get("paid", 0.0), 2)})
    await db.invoices.update_one({"id": invoice_id}, {"$set": updates})
    return await db.invoices.find_one({"id": invoice_id}, {"_id": 0})

@api_router.post("/invoices/{invoice_id}/mark-paid", response_model=Invoice)
async def mark_invoice_paid(invoice_id: str):
    inv = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not inv: raise HTTPException(404, "Invoice not found")
    await db.invoices.update_one({"id": invoice_id}, {"$set": {
        "paid": inv["total"], "balance": 0.0, "status": "Paid"}})
    return await db.invoices.find_one({"id": invoice_id}, {"_id": 0})

@api_router.get("/invoices/{invoice_id}/pdf")
async def invoice_pdf(invoice_id: str):
    from fpdf import FPDF
    inv = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not inv: raise HTTPException(404, "Invoice not found")

    CHARCOAL, MUTE, FILL = (28, 28, 30), (142, 142, 147), (242, 242, 244)

    def safe(s):
        return str(s).replace("—", "-").replace("–", "-").encode("latin-1", "replace").decode("latin-1")
    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(False)
    pdf.set_margins(18, 18, 18)
    W = 174.0

    # header: caps label left, status pill right
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTE)
    pdf.cell(0, 5, "ARES CREATIVE STUDIO  ·  INVOICE")
    status = inv["status"].upper()
    pdf.set_font("Helvetica", "B", 7)
    pill_w = pdf.get_string_width(status) + 12
    px, py = 18 + W - pill_w, pdf.get_y() - 1
    pdf.set_fill_color(*FILL)
    pdf.rect(px, py, pill_w, 8, style="F")
    pdf.set_xy(px, py)
    pdf.set_text_color(74, 74, 80)
    pdf.cell(pill_w, 8, status, align="C")
    pdf.set_xy(18, py + 16)

    # serif number + client line
    pdf.set_font("Times", "", 30)
    pdf.set_text_color(*CHARCOAL)
    pdf.cell(0, 14, inv["number"], ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(110, 110, 116)
    pdf.cell(0, 6, safe(inv["client_name"] + (f"  ·  {inv['project_name']}" if inv.get("project_name") else "")), ln=1)
    pdf.ln(7)

    # issued / due
    y = pdf.get_y()
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*MUTE)
    pdf.cell(24, 4, "ISSUED")
    pdf.set_xy(50, y)
    pdf.cell(24, 4, "DUE")
    pdf.set_xy(18, y + 5)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*CHARCOAL)
    pdf.cell(32, 6, str(inv.get("issued_date") or "-"))
    pdf.set_xy(50, y + 5)
    pdf.cell(32, 6, str(inv.get("due_date") or "-"))
    pdf.set_xy(18, y + 15)

    # line items as filled rows
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(0, 6, "LINE ITEMS", ln=1)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*MUTE)
    pdf.cell(105, 5, "DESCRIPTION")
    pdf.cell(25, 5, "QTY", align="R")
    pdf.cell(44, 5, "RATE", align="R", ln=1)
    pdf.ln(1.5)
    pdf.set_fill_color(*FILL)
    for item in inv.get("items", []):
        y = pdf.get_y()
        pdf.rect(18, y, W, 10, style="F")
        pdf.set_xy(22, y + 2.5)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*CHARCOAL)
        pdf.cell(97, 5, safe(item.get("description", "")))
        pdf.cell(25, 5, str(item.get("qty", 1)), align="R")
        pdf.cell(40, 5, f"${item.get('rate', 0):,.2f}", align="R")
        pdf.set_xy(18, y + 12)
    pdf.ln(5)

    # notes (left) + totals (right)
    y = pdf.get_y()
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*CHARCOAL)
    pdf.cell(90, 6, "NOTES")
    if inv.get("notes"):
        pdf.set_fill_color(*FILL)
        pdf.rect(18, y + 8, 88, 26, style="F")
        pdf.set_xy(22, y + 11)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*MUTE)
        pdf.multi_cell(80, 4.5, safe(inv["notes"]))

    tx = 112.0
    def trow(label, value, bold=False, big=False):
        yy = max(pdf.get_y(), y)
        pdf.set_xy(tx, yy)
        if big:
            pdf.set_font("Times", "", 15)
            pdf.set_text_color(*CHARCOAL)
            pdf.cell(38, 9, label)
            pdf.cell(42, 9, value, align="R")
            pdf.set_xy(tx, yy + 10)
        else:
            pdf.set_font("Helvetica", "B" if bold else "", 8.5)
            if bold:
                pdf.set_text_color(*CHARCOAL)
            else:
                pdf.set_text_color(*MUTE)
            pdf.cell(38, 7, label)
            pdf.set_text_color(*CHARCOAL)
            pdf.cell(42, 7, value, align="R")
            pdf.set_xy(tx, yy + 7)

    pdf.set_y(y)
    trow("Subtotal", f"${inv.get('subtotal', 0):,.2f}")
    if inv.get("discount"):
        trow("Discount", f"-${inv['discount']:,.2f}")
    trow("Tax (8%)", f"${inv.get('tax', 0):,.2f}")
    yy = pdf.get_y()
    pdf.set_draw_color(233, 233, 236)
    pdf.line(tx, yy, tx + 80, yy)
    pdf.set_xy(tx, yy + 3)
    trow("TOTAL", f"${inv.get('total', 0):,.2f}", bold=True, big=True)
    trow("Paid", f"${inv.get('paid', 0):,.2f}")
    trow("BALANCE", f"${inv.get('balance', 0):,.2f}", bold=True)

    return Response(
        bytes(pdf.output()),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{inv["number"]}.pdf"'},
    )


@api_router.get("/invoices/{invoice_id}/html")
async def invoice_html(invoice_id: str):
    inv = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not inv: raise HTTPException(404, "Invoice not found")

    rows = "".join(
        f'''<div class="line-row">
          <div class="line-desc">{item.get("description","")}</div>
          <div class="line-qty">{item.get("qty",1)}</div>
          <div class="line-rate">${item.get("rate",0):,.2f}</div>
        </div>'''
        for item in inv.get("items", [])
    )
    discount_row = f'''<div class="total-row"><span class="mute">Discount</span><span>-${inv["discount"]:,.2f}</span></div>''' if inv.get("discount") else ""
    notes_html = f'''<div class="notes-box">{inv["notes"]}</div>''' if inv.get("notes") else '<div class="notes-box mute">Payment terms, bank details…</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{inv["number"]} — Ares Creative Studio</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400&family=Inter+Tight:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#F7F7F9; font-family:'Inter Tight',sans-serif; color:#1C1C1E; padding:48px 24px; -webkit-font-smoothing:antialiased; }}
  .page {{ max-width:900px; margin:0 auto; background:#FFFFFF; border-radius:16px; box-shadow:0 2px 12px rgba(28,28,30,0.04); padding:56px 64px; }}
  .caps {{ font-size:10.5px; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; color:#8E8E93; }}
  .caps-dark {{ font-size:11px; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; color:#1C1C1E; }}
  .head {{ display:flex; justify-content:space-between; align-items:flex-start; }}
  .status {{ background:#F2F2F4; color:#4A4A50; font-size:9px; font-weight:600; letter-spacing:0.14em; text-transform:uppercase; padding:5px 12px; border-radius:999px; }}
  .number {{ font-family:'Fraunces',serif; font-weight:400; font-size:44px; letter-spacing:-0.02em; margin-top:14px; }}
  .client {{ color:#6E6E74; font-size:13px; margin-top:8px; }}
  .dates {{ display:flex; gap:40px; margin-top:28px; font-size:12px; }}
  .dates .caps {{ display:inline; margin-right:8px; }}
  .dates span.val {{ color:#1C1C1E; }}
  .section {{ margin-top:44px; }}
  .table-head {{ display:grid; grid-template-columns:1fr 80px 130px 36px; gap:12px; padding:0 16px; margin:14px 0 10px; }}
  .table-head span {{ font-size:9.5px; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; color:#8E8E93; }}
  .table-head span:nth-child(2), .table-head span:nth-child(3) {{ text-align:right; }}
  .line-row {{ display:grid; grid-template-columns:1fr 80px 130px 36px; gap:12px; align-items:center; margin-bottom:8px; }}
  .line-row > div {{ background:#F2F2F4; border-radius:9px; padding:11px 16px; font-size:13px; }}
  .line-qty, .line-rate {{ text-align:right; }}
  .bottom {{ display:grid; grid-template-columns:1fr 1fr; gap:48px; margin-top:44px; }}
  .notes-box {{ background:#F2F2F4; border-radius:9px; padding:16px; font-size:13px; min-height:80px; margin-top:12px; color:#6E6E74; line-height:1.6; }}
  .total-row {{ display:flex; justify-content:space-between; padding:8px 0; font-size:13px; }}
  .total-row .mute {{ color:#8E8E93; }}
  .divider {{ border-top:1px solid #E9E9EC; margin:10px 0; }}
  .grand {{ font-family:'Fraunces',serif; font-size:24px; }}
  .grand-label {{ font-size:11px; letter-spacing:0.14em; font-weight:600; }}
  .balance {{ font-weight:500; font-size:15px; }}
  @media print {{ body {{ background:#FFF; padding:0; }} .page {{ box-shadow:none; }} }}
</style>
</head>
<body>
  <div class="page">
    <div class="head">
      <div class="caps">Ares Creative Studio · Invoice</div>
      <span class="status">{inv["status"]}</span>
    </div>
    <div class="number">{inv["number"]}</div>
    <div class="client">{inv["client_name"]}{("  ·  " + inv["project_name"]) if inv.get("project_name") else ""}</div>
    <div class="dates">
      <div><span class="caps">Issued</span> <span class="val">{inv.get("issued_date") or "—"}</span></div>
      <div><span class="caps">Due</span> <span class="val">{inv.get("due_date") or "—"}</span></div>
    </div>
    <div class="section">
      <div class="caps-dark">Line Items</div>
      <div class="table-head"><span>Description</span><span>Qty</span><span>Rate</span><span></span></div>
      {rows}
    </div>
    <div class="bottom">
      <div>
        <div class="caps-dark">Notes</div>
        {notes_html}
      </div>
      <div>
        <div class="total-row"><span class="mute">Subtotal</span><span>${inv.get("subtotal",0):,.2f}</span></div>
        {discount_row}
        <div class="total-row"><span class="mute">Tax (8%)</span><span>${inv.get("tax",0):,.2f}</span></div>
        <div class="divider"></div>
        <div class="total-row"><span class="grand-label">TOTAL</span><span class="grand">${inv.get("total",0):,.2f}</span></div>
        <div class="total-row"><span class="mute">Paid</span><span>${inv.get("paid",0):,.2f}</span></div>
        <div class="total-row"><span class="grand-label">BALANCE</span><span class="balance">${inv.get("balance",0):,.2f}</span></div>
      </div>
    </div>
  </div>
</body>
</html>"""
    return Response(
        html,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{inv["number"]}.html"'},
    )


# ---------- Service catalog / client patch / documents ----------
@api_router.get("/services/catalog")
async def services_catalog():
    return SERVICE_CATALOG

class ClientPatch(BaseModel):
    business_name: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    instagram: Optional[str] = None
    industry: Optional[str] = None
    lead_source: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    color: Optional[str] = None
    brand_kit: Optional[dict] = None
    welcome_message: Optional[str] = None
    journey: Optional[dict] = None

@api_router.patch("/clients/{client_id}", response_model=Client)
async def patch_client(client_id: str, payload: ClientPatch):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Nothing to update")
    res = await db.clients.update_one({"id": client_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(404, "Client not found")
    if "color" in updates:
        await db.calendar.update_many({"client_id": client_id}, {"$set": {"client_color": updates["color"]}})
        await db.tasks.update_many({"client_id": client_id}, {"$set": {"client_color": updates["color"]}})
    return await db.clients.find_one({"id": client_id}, {"_id": 0})

@api_router.get("/documents")
async def list_documents(client_id: Optional[str] = None):
    q = {"client_id": client_id} if client_id else {}
    return await db.documents.find(q, {"_id": 0}).sort("name", 1).to_list(500)


# ---------- Task status / client delete ----------
TASK_STATUSES = ["In Progress", "Pending", "Waiting", "Overdue", "Complete"]

class TaskPatch(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None

@api_router.patch("/tasks/{task_id}", response_model=Task)
async def patch_task(task_id: str, payload: TaskPatch):
    updates = {}
    if payload.status is not None:
        if payload.status not in TASK_STATUSES:
            raise HTTPException(400, "Invalid status")
        updates["status"] = payload.status
    if payload.assignee is not None:
        if payload.assignee not in ["Vana", "Jessica"]:
            raise HTTPException(400, "Invalid assignee")
        updates["assignee"] = payload.assignee
    if not updates:
        raise HTTPException(400, "Nothing to update")
    res = await db.tasks.update_one({"id": task_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(404, "Task not found")
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    # keep project progress in sync everywhere
    if payload.status and task.get("project_id"):
        total = await db.tasks.count_documents({"project_id": task["project_id"]})
        done = await db.tasks.count_documents({"project_id": task["project_id"], "status": "Complete"})
        await db.projects.update_one({"id": task["project_id"]}, {"$set": {"progress": round(done / total * 100) if total else 0}})
    return task

@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str):
    res = await db.clients.delete_one({"id": client_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Client not found")
    for col in ["projects", "tasks", "calendar", "invoices", "documents", "content"]:
        await db[col].delete_many({"client_id": client_id})
    return {"deleted": True, "client_id": client_id}


# ---------- Manual task / event creation ----------
OPS_CATEGORIES = {"OPERATIONS", "FINANCIAL"}

class TaskCreate(BaseModel):
    title: str
    client_id: Optional[str] = None
    project_id: Optional[str] = None
    category: str = "PROJECTS"
    due_date: str
    estimated_hours: float = 2.0
    assignee: Optional[str] = None
    kind: str = "task"  # task | deadline

@api_router.post("/tasks", response_model=Task)
async def create_task(payload: TaskCreate):
    c = await db.clients.find_one({"id": payload.client_id}, {"_id": 0}) if payload.client_id else None
    assignee = payload.assignee or ("Jessica" if payload.category in OPS_CATEGORIES else "Vana")
    is_deadline = payload.kind == "deadline"
    task = {
        "id": new_id(), "title": payload.title,
        "client_id": payload.client_id, "client_name": c["business_name"] if c else None,
        "project_id": payload.project_id, "category": payload.category,
        "status": "Pending", "due_date": payload.due_date,
        "estimated_hours": payload.estimated_hours, "assigned_to": assignee,
        "assignee": assignee, "client_color": c.get("color") if c else None,
        "is_deadline": is_deadline,
    }
    await db.tasks.insert_one(task)
    await db.calendar.insert_one({
        "id": new_id(), "date": payload.due_date, "title": payload.title,
        "subtitle": payload.category, "client_name": task["client_name"],
        "category": payload.category, "kind": "deadline" if is_deadline else "task",
        "is_deadline": is_deadline, "project_id": payload.project_id,
        "client_id": payload.client_id, "client_color": task["client_color"],
    })
    task.pop("_id", None)
    return task

class EventCreate(BaseModel):
    date: str
    title: str
    kind: str = "event"  # event | meeting | deadline
    category: Optional[str] = None
    client_id: Optional[str] = None

@api_router.post("/calendar", response_model=CalendarEvent)
async def create_calendar_event(payload: EventCreate):
    c = await db.clients.find_one({"id": payload.client_id}, {"_id": 0}) if payload.client_id else None
    is_deadline = payload.kind == "deadline"
    ev = {
        "id": new_id(), "date": payload.date, "title": payload.title,
        "subtitle": payload.category, "client_name": c["business_name"] if c else None,
        "category": payload.category, "kind": payload.kind, "is_deadline": is_deadline,
        "project_id": None, "client_id": payload.client_id,
        "client_color": c.get("color") if c else None,
    }
    await db.calendar.insert_one(ev)
    ev.pop("_id", None)
    return ev

# ---------- Leads ----------
LEAD_STATUSES = ["New", "Contacted", "Qualified", "Proposal", "Won", "Lost"]

class Lead(BaseModel):
    id: str = Field(default_factory=new_id)
    business_name: str
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    service_interest: Optional[str] = None
    status: str = "New"
    notes: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)

class LeadCreate(BaseModel):
    business_name: str
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    service_interest: Optional[str] = None
    status: str = "New"
    notes: Optional[str] = None

@api_router.get("/leads", response_model=List[Lead])
async def list_leads():
    return await db.leads.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)

@api_router.post("/leads", response_model=Lead)
async def create_lead(payload: LeadCreate):
    doc = Lead(**payload.model_dump()).model_dump()
    await db.leads.insert_one(doc)
    doc.pop("_id", None)
    return doc

class LeadPatch(BaseModel):
    status: str

@api_router.patch("/leads/{lead_id}", response_model=Lead)
async def patch_lead(lead_id: str, payload: LeadPatch):
    if payload.status not in LEAD_STATUSES:
        raise HTTPException(400, "Invalid status")
    res = await db.leads.update_one({"id": lead_id}, {"$set": {"status": payload.status}})
    if res.matched_count == 0:
        raise HTTPException(404, "Lead not found")
    return await db.leads.find_one({"id": lead_id}, {"_id": 0})

@api_router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str):
    res = await db.leads.delete_one({"id": lead_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Lead not found")
    return {"deleted": True, "lead_id": lead_id}


# ---------- Brand documents ----------
class DocumentCreate(BaseModel):
    client_id: str
    name: str
    kind: str = "brand"
    type: Optional[str] = "File"
    access: Optional[str] = "Internal"
    status: str = "Draft"

@api_router.post("/documents")
async def create_document(payload: DocumentCreate):
    c = await db.clients.find_one({"id": payload.client_id}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Client not found")
    doc = {
        "id": new_id(), "client_id": c["id"], "client_name": c["business_name"],
        "name": payload.name, "kind": payload.kind, "type": payload.type,
        "access": payload.access, "status": payload.status, "version": 1,
        "created_at": now_iso(),
    }
    await db.documents.insert_one(doc)
    doc.pop("_id", None)
    return doc


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def auto_seed():
    await seed()

@app.on_event("startup")
async def ensure_client_colors():
    palette = ["#C97F87", "#8B7EA8", "#8A9B8E", "#C4A77D", "#5C6B7A", "#B0766A"]
    clients = await db.clients.find({}, {"_id": 0}).to_list(1000)
    for i, c in enumerate(clients):
        color = c.get("color") or palette[i % len(palette)]
        if not c.get("color"):
            await db.clients.update_one({"id": c["id"]}, {"$set": {"color": color}})
        await db.calendar.update_many(
            {"client_id": c["id"], "client_color": {"$exists": False}},
            {"$set": {"client_color": color}})
        await db.tasks.update_many(
            {"client_id": c["id"], "client_color": {"$exists": False}},
            {"$set": {"client_color": color}})
    # default assignees: Vana default, Jessica for ops/financial
    await db.tasks.update_many(
        {"assignee": {"$exists": False}, "category": {"$in": ["OPERATIONS", "FINANCIAL"]}},
        {"$set": {"assignee": "Jessica"}})
    await db.tasks.update_many(
        {"assignee": {"$exists": False}},
        {"$set": {"assignee": "Vana"}})
    if await db.leads.count_documents({}) == 0:
        await db.leads.insert_many([
            {"id": new_id(), "business_name": "Atlas Roasters", "contact": "Dana Kim", "email": "dana@atlasroasters.com",
             "phone": "+1 (555) 221-8840", "source": "Instagram", "service_interest": "The Level Up",
             "status": "Qualified", "notes": "Rebrand before Q4 launch.", "created_at": now_iso()},
            {"id": new_id(), "business_name": "Lumen Legal", "contact": "Peter Shaw", "email": "peter@lumenlegal.com",
             "phone": "+1 (555) 903-1124", "source": "Referral", "service_interest": "Website Plus",
             "status": "Contacted", "notes": "Sent intro deck.", "created_at": now_iso()},
            {"id": new_id(), "business_name": "Wildwood Yoga", "contact": "Mia Torres", "email": "mia@wildwoodyoga.com",
             "phone": "+1 (555) 447-9902", "source": "Website", "service_interest": "Social Club",
             "status": "New", "notes": None, "created_at": now_iso()},
        ])

LEGACY_RENAMES = [
    ("business website", "Website Plus"),
    ("plus website", "Website Plus"),
    ("basic website", "Website Basic"),
    ("website premium", "Custom Website"),
]

def _rename_str(v):
    if not isinstance(v, str):
        return v
    out = v
    for old, new in LEGACY_RENAMES:
        out = re.sub(re.escape(old), new, out, flags=re.IGNORECASE)
    return out

@app.on_event("startup")
async def rename_legacy_strings():
    pattern = "|".join(re.escape(o) for o, _ in LEGACY_RENAMES)
    rx = re.compile(pattern, re.IGNORECASE)
    for col, fields in [("projects", ["name"]), ("tasks", ["title"]), ("calendar", ["title", "subtitle", "category"]), ("leads", ["service_interest"]), ("invoices", ["project_name"])]:
        async for doc in db[col].find({"$or": [{f: {"$regex": rx}} for f in fields]}):
            updates = {f: _rename_str(doc[f]) for f in fields if _rename_str(doc.get(f)) != doc.get(f)}
            if updates:
                await db[col].update_one({"_id": doc["_id"]}, {"$set": updates})
    async for inv in db.invoices.find({"items.description": {"$regex": rx}}):
        items = inv.get("items", [])
        for it in items:
            nd = _rename_str(it.get("description"))
            if nd != it.get("description"):
                it["description"] = nd
        await db.invoices.update_one({"_id": inv["_id"]}, {"$set": {"items": items}})
    async for c in db.clients.find({}):
        updates = {}
        services = [_rename_str(s) for s in c.get("services", [])]
        if services != c.get("services", []):
            updates["services"] = services
        sds = c.get("service_details", [])
        changed = False
        for s in sds:
            nn = _rename_str(s.get("name"))
            if nn != s.get("name"):
                s["name"] = nn
                changed = True
        if changed:
            updates["service_details"] = sds
        if updates:
            await db.clients.update_one({"_id": c["_id"]}, {"$set": updates})

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
