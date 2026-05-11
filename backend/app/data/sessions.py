"""Mock conference session catalog.

All sessions, speakers, companies, and descriptions are fictional and
are inspired by — but not copied from — public enterprise conferences
such as Stripe Sessions, AWS re:Invent, RSAC, and Google Cloud Next.
"""
from __future__ import annotations

from typing import List

from app.models import Session


# Three-day fictional "Atlas Conference 2026" running June 9–11, 2026
# Rooms loosely modeled on a large convention center floor plan.

SESSIONS_RAW: List[dict] = [
    # ─────────────── Track 1: Payments & Fintech ───────────────
    {
        "session_id": "S001",
        "title": "Building Payment Flows for Global Marketplaces",
        "description": (
            "A practical walkthrough of designing multi-party payment flows "
            "for two-sided marketplaces operating across 30+ countries. "
            "We cover split payouts, marketplace KYC, dispute orchestration, "
            "and the operational tradeoffs of platform vs. merchant-of-record models."
        ),
        "track": "Payments & Fintech",
        "topic": "Marketplace Payments",
        "date": "2026-06-09",
        "start_time": "09:00",
        "end_time": "10:00",
        "room": "Hall A1",
        "speaker": "Maya Okafor",
        "company": "Northwind Commerce",
        "level": "intermediate",
        "capacity": 300,
        "registered_count": 268,
    },
    {
        "session_id": "S002",
        "title": "Reducing Authorization Decline Rates with Network Tokens",
        "description": (
            "Card declines silently cost merchants billions a year. Learn how "
            "network tokenization, account updater services, and intelligent "
            "retry logic can recover 1–3 points of authorization rate."
        ),
        "track": "Payments & Fintech",
        "topic": "Authorization Optimization",
        "date": "2026-06-09",
        "start_time": "10:30",
        "end_time": "11:15",
        "room": "Hall A1",
        "speaker": "Daniel Roth",
        "company": "Helix Pay",
        "level": "advanced",
        "capacity": 220,
        "registered_count": 145,
    },
    {
        "session_id": "S003",
        "title": "Subscription Billing at Scale: Lessons from 50M Active Customers",
        "description": (
            "How to architect dunning, proration, mid-cycle plan changes, and "
            "tax for global subscription products without drowning in edge cases."
        ),
        "track": "Payments & Fintech",
        "topic": "Subscriptions",
        "date": "2026-06-10",
        "start_time": "13:30",
        "end_time": "14:30",
        "room": "Hall A2",
        "speaker": "Priya Raman",
        "company": "Tessera Cloud",
        "level": "intermediate",
        "capacity": 250,
        "registered_count": 250,
    },
    {
        "session_id": "S004",
        "title": "Embedded Finance for Vertical SaaS",
        "description": (
            "A field guide for SaaS founders adding payments, lending, and card "
            "issuing into their products without becoming a bank themselves."
        ),
        "track": "Payments & Fintech",
        "topic": "Embedded Finance",
        "date": "2026-06-11",
        "start_time": "09:30",
        "end_time": "10:30",
        "room": "Hall A2",
        "speaker": "Elena Martínez",
        "company": "Vertica Systems",
        "level": "beginner",
        "capacity": 180,
        "registered_count": 92,
    },
    {
        "session_id": "S005",
        "title": "Fraud Models that Don't Hate Good Customers",
        "description": (
            "Modern risk teams need ML systems that catch fraud rings without "
            "blocking legitimate buyers. We discuss feature engineering, "
            "shadow scoring, and human-in-the-loop review queues."
        ),
        "track": "Payments & Fintech",
        "topic": "Fraud & Risk",
        "date": "2026-06-10",
        "start_time": "16:00",
        "end_time": "17:00",
        "room": "Hall A1",
        "speaker": "Jordan Lee",
        "company": "Northwind Commerce",
        "level": "advanced",
        "capacity": 200,
        "registered_count": 185,
    },

    # ─────── Track 2: Stablecoins & Global Money Movement ───────
    {
        "session_id": "S006",
        "title": "Stablecoins for Cross-Border Payouts",
        "description": (
            "Treasury and ops leaders share how regulated stablecoins have "
            "started to replace correspondent banking for B2B payouts in LATAM, "
            "Africa, and Southeast Asia, and what compliance teams need to know."
        ),
        "track": "Stablecoins & Global Money Movement",
        "topic": "Cross-Border Payments",
        "date": "2026-06-09",
        "start_time": "11:30",
        "end_time": "12:30",
        "room": "Hall B1",
        "speaker": "Adaeze Nwosu",
        "company": "Meridian Treasury",
        "level": "intermediate",
        "capacity": 350,
        "registered_count": 339,
    },
    {
        "session_id": "S007",
        "title": "On-Ramps and Off-Ramps: Designing the Boring Parts",
        "description": (
            "The interesting work in stablecoin products is rarely on-chain. "
            "We walk through KYC orchestration, sanction screening, banking "
            "partners, and reconciliation patterns that actually scale."
        ),
        "track": "Stablecoins & Global Money Movement",
        "topic": "On/Off Ramps",
        "date": "2026-06-09",
        "start_time": "14:00",
        "end_time": "15:00",
        "room": "Hall B1",
        "speaker": "Felix Brandt",
        "company": "Lattice Rails",
        "level": "intermediate",
        "capacity": 200,
        "registered_count": 124,
    },
    {
        "session_id": "S008",
        "title": "Treasury Automation with Programmable Money",
        "description": (
            "How CFO teams are using stablecoin rails for automated supplier "
            "payments, intra-day liquidity, and 24/7 reconciliation."
        ),
        "track": "Stablecoins & Global Money Movement",
        "topic": "Treasury",
        "date": "2026-06-10",
        "start_time": "09:00",
        "end_time": "10:00",
        "room": "Hall B1",
        "speaker": "Sara Devlin",
        "company": "Meridian Treasury",
        "level": "advanced",
        "capacity": 150,
        "registered_count": 121,
    },
    {
        "session_id": "S009",
        "title": "Compliance Patterns for Regulated Stablecoin Issuance",
        "description": (
            "A deep dive into reserve attestations, redemption SLAs, and "
            "MiCA/US framework alignment for teams shipping issuer products."
        ),
        "track": "Stablecoins & Global Money Movement",
        "topic": "Stablecoin Compliance",
        "date": "2026-06-11",
        "start_time": "11:00",
        "end_time": "12:00",
        "room": "Hall B2",
        "speaker": "Hiroshi Tanaka",
        "company": "Lattice Rails",
        "level": "advanced",
        "capacity": 160,
        "registered_count": 78,
    },
    {
        "session_id": "S010",
        "title": "FX in a Stablecoin World",
        "description": (
            "Exploring multi-currency stablecoin baskets, cross-rate pricing, "
            "and hedging strategies for global payment platforms."
        ),
        "track": "Stablecoins & Global Money Movement",
        "topic": "FX",
        "date": "2026-06-11",
        "start_time": "14:30",
        "end_time": "15:30",
        "room": "Hall B1",
        "speaker": "Camille Laurent",
        "company": "Helix Pay",
        "level": "intermediate",
        "capacity": 180,
        "registered_count": 60,
    },

    # ──────────── Track 3: AI Agents & Automation ────────────
    {
        "session_id": "S011",
        "title": "Agentic Commerce: How AI Changes Checkout",
        "description": (
            "Buyer agents are starting to negotiate, compare, and complete "
            "purchases on behalf of users. We cover the new contracts merchants "
            "need: agent identity, intent verification, and machine-friendly checkout."
        ),
        "track": "AI Agents & Automation",
        "topic": "Agentic Commerce",
        "date": "2026-06-09",
        "start_time": "13:00",
        "end_time": "14:00",
        "room": "Hall C1",
        "speaker": "Ravi Subramanian",
        "company": "Atlas Labs",
        "level": "intermediate",
        "capacity": 400,
        "registered_count": 397,
    },
    {
        "session_id": "S012",
        "title": "Designing Reliable Tool-Calling Agents",
        "description": (
            "Practical patterns for building agents that call tools deterministically: "
            "schema design, retries, idempotency keys, and recovery from partial failures."
        ),
        "track": "AI Agents & Automation",
        "topic": "Tool Use",
        "date": "2026-06-09",
        "start_time": "15:00",
        "end_time": "16:00",
        "room": "Hall C2",
        "speaker": "Wen Zhang",
        "company": "Northbeam AI",
        "level": "advanced",
        "capacity": 220,
        "registered_count": 218,
    },
    {
        "session_id": "S013",
        "title": "From Prompt to Production: Agent Lifecycle Management",
        "description": (
            "How leading teams version, test, deploy, and observe agent behavior "
            "across thousands of customer-facing flows."
        ),
        "track": "AI Agents & Automation",
        "topic": "Agent Ops",
        "date": "2026-06-10",
        "start_time": "11:00",
        "end_time": "12:00",
        "room": "Hall C1",
        "speaker": "Olivia Park",
        "company": "Sentinel AI",
        "level": "intermediate",
        "capacity": 280,
        "registered_count": 200,
    },
    {
        "session_id": "S014",
        "title": "Multi-Agent Workflows in the Enterprise",
        "description": (
            "Lessons learned from deploying systems where many specialized agents "
            "collaborate on tasks like procurement, HR onboarding, and IT support."
        ),
        "track": "AI Agents & Automation",
        "topic": "Multi-Agent Systems",
        "date": "2026-06-10",
        "start_time": "14:30",
        "end_time": "15:30",
        "room": "Hall C2",
        "speaker": "Marcus Hale",
        "company": "Atlas Labs",
        "level": "advanced",
        "capacity": 260,
        "registered_count": 155,
    },
    {
        "session_id": "S015",
        "title": "Agents for Customer Support that Actually Resolve Tickets",
        "description": (
            "Beyond demos: a real implementation story including escalation "
            "logic, knowledge integration, and measurable CSAT outcomes."
        ),
        "track": "AI Agents & Automation",
        "topic": "Customer Support",
        "date": "2026-06-11",
        "start_time": "10:00",
        "end_time": "11:00",
        "room": "Hall C1",
        "speaker": "Aisha Khan",
        "company": "Helix Pay",
        "level": "beginner",
        "capacity": 320,
        "registered_count": 184,
    },
    {
        "session_id": "S016",
        "title": "Voice Agents for Contact Centers",
        "description": (
            "Latency budgets, barge-in, and turn-taking. What it really takes "
            "to ship a voice agent that customers prefer over the IVR menu."
        ),
        "track": "AI Agents & Automation",
        "topic": "Voice AI",
        "date": "2026-06-11",
        "start_time": "13:00",
        "end_time": "14:00",
        "room": "Hall C2",
        "speaker": "Tomás García",
        "company": "Sentinel AI",
        "level": "intermediate",
        "capacity": 200,
        "registered_count": 110,
    },

    # ──────── Track 4: AI Safety & Agent Evaluation ────────
    {
        "session_id": "S017",
        "title": "LLM-as-a-Judge for Enterprise AI Evaluation",
        "description": (
            "When and how to trust LLM judges. We discuss calibration, "
            "rubric design, jury-of-models patterns, and pitfalls when using "
            "models to evaluate other models in production."
        ),
        "track": "AI Safety & Agent Evaluation",
        "topic": "Evaluation",
        "date": "2026-06-09",
        "start_time": "10:00",
        "end_time": "11:00",
        "room": "Hall D1",
        "speaker": "Dr. Yuki Tanaka",
        "company": "Polaris Research",
        "level": "advanced",
        "capacity": 240,
        "registered_count": 230,
    },
    {
        "session_id": "S018",
        "title": "Building Evaluation Datasets that Reflect Reality",
        "description": (
            "From production traces to high-signal eval sets: sampling, "
            "labeling pipelines, and avoiding eval drift over time."
        ),
        "track": "AI Safety & Agent Evaluation",
        "topic": "Eval Datasets",
        "date": "2026-06-09",
        "start_time": "16:30",
        "end_time": "17:30",
        "room": "Hall D1",
        "speaker": "Ingrid Sørensen",
        "company": "Polaris Research",
        "level": "intermediate",
        "capacity": 180,
        "registered_count": 89,
    },
    {
        "session_id": "S019",
        "title": "Red Teaming Agentic Systems",
        "description": (
            "Adversarial evaluation strategies for agents with tool access: "
            "prompt injection, goal hijacking, exfiltration tests, and "
            "automated attack libraries."
        ),
        "track": "AI Safety & Agent Evaluation",
        "topic": "Red Teaming",
        "date": "2026-06-10",
        "start_time": "10:00",
        "end_time": "11:00",
        "room": "Hall D2",
        "speaker": "Nadia Hassan",
        "company": "Bastion Security",
        "level": "advanced",
        "capacity": 200,
        "registered_count": 199,
    },
    {
        "session_id": "S020",
        "title": "Measuring Agent Reliability in Long-Running Tasks",
        "description": (
            "How to design metrics that capture multi-step success, partial "
            "credit, and recovery behavior for agents that run for hours."
        ),
        "track": "AI Safety & Agent Evaluation",
        "topic": "Reliability",
        "date": "2026-06-10",
        "start_time": "15:30",
        "end_time": "16:30",
        "room": "Hall D1",
        "speaker": "Ben Carter",
        "company": "Sentinel AI",
        "level": "intermediate",
        "capacity": 160,
        "registered_count": 88,
    },
    {
        "session_id": "S021",
        "title": "Safety Cases for Production AI",
        "description": (
            "Borrowing from aviation and medical devices: how to write a "
            "structured safety case for an AI feature, and what regulators "
            "are starting to expect."
        ),
        "track": "AI Safety & Agent Evaluation",
        "topic": "Safety Cases",
        "date": "2026-06-11",
        "start_time": "09:00",
        "end_time": "10:00",
        "room": "Hall D1",
        "speaker": "Dr. Renata Costa",
        "company": "Polaris Research",
        "level": "advanced",
        "capacity": 140,
        "registered_count": 70,
    },

    # ──────── Track 5: Cybersecurity & Identity ────────
    {
        "session_id": "S022",
        "title": "Securing AI Workloads with Defense-in-Depth",
        "description": (
            "From inference endpoints to vector stores: a layered approach "
            "to securing modern AI infrastructure, including secrets, network "
            "policies, and runtime detection."
        ),
        "track": "Cybersecurity & Identity",
        "topic": "AI Security",
        "date": "2026-06-09",
        "start_time": "11:00",
        "end_time": "12:00",
        "room": "Hall E1",
        "speaker": "Liam O'Brien",
        "company": "Bastion Security",
        "level": "intermediate",
        "capacity": 320,
        "registered_count": 305,
    },
    {
        "session_id": "S023",
        "title": "Identity Governance for AI-Powered Applications",
        "description": (
            "How to grant least-privilege access to agents acting on behalf of "
            "users, including delegated OAuth scopes, just-in-time access, and "
            "audit logging that holds up in court."
        ),
        "track": "Cybersecurity & Identity",
        "topic": "Identity Governance",
        "date": "2026-06-09",
        "start_time": "14:00",
        "end_time": "15:00",
        "room": "Hall E2",
        "speaker": "Rachel Kim",
        "company": "Ironwood Identity",
        "level": "advanced",
        "capacity": 220,
        "registered_count": 211,
    },
    {
        "session_id": "S024",
        "title": "Zero Trust Patterns for Modern SaaS Platforms",
        "description": (
            "What zero trust actually means for B2B SaaS: device posture, "
            "continuous authentication, and replacing VPNs with identity-aware proxies."
        ),
        "track": "Cybersecurity & Identity",
        "topic": "Zero Trust",
        "date": "2026-06-10",
        "start_time": "11:00",
        "end_time": "12:00",
        "room": "Hall E1",
        "speaker": "Marcus Hale",
        "company": "Ironwood Identity",
        "level": "intermediate",
        "capacity": 280,
        "registered_count": 180,
    },
    {
        "session_id": "S025",
        "title": "Detecting and Responding to Prompt Injection at Scale",
        "description": (
            "Practical detection strategies, instrumentation, and response "
            "playbooks for prompt injection in customer-facing AI surfaces."
        ),
        "track": "Cybersecurity & Identity",
        "topic": "Prompt Injection",
        "date": "2026-06-10",
        "start_time": "16:00",
        "end_time": "17:00",
        "room": "Hall E2",
        "speaker": "Nadia Hassan",
        "company": "Bastion Security",
        "level": "advanced",
        "capacity": 200,
        "registered_count": 198,
    },
    {
        "session_id": "S026",
        "title": "Passkeys at Scale: A Migration Story",
        "description": (
            "Lessons from a multi-year passkey rollout to 80M users, including "
            "fallback flows, device transfer, and analytics on phishing reduction."
        ),
        "track": "Cybersecurity & Identity",
        "topic": "Authentication",
        "date": "2026-06-11",
        "start_time": "13:30",
        "end_time": "14:30",
        "room": "Hall E1",
        "speaker": "Sven Olsson",
        "company": "Ironwood Identity",
        "level": "intermediate",
        "capacity": 240,
        "registered_count": 145,
    },

    # ──────── Track 6: Cloud Infrastructure ────────
    {
        "session_id": "S027",
        "title": "Scaling Event-Driven Architectures on Cloud",
        "description": (
            "Backpressure, exactly-once delivery, and schema evolution for "
            "event-driven systems handling tens of billions of messages per day."
        ),
        "track": "Cloud Infrastructure",
        "topic": "Event-Driven Architecture",
        "date": "2026-06-09",
        "start_time": "13:30",
        "end_time": "14:30",
        "room": "Hall F1",
        "speaker": "Carlos Mendes",
        "company": "Tessera Cloud",
        "level": "advanced",
        "capacity": 320,
        "registered_count": 290,
    },
    {
        "session_id": "S028",
        "title": "Multi-Region Active-Active for the 99.99% Crowd",
        "description": (
            "Database replication strategies, conflict resolution, and "
            "operational practices for true multi-region active-active services."
        ),
        "track": "Cloud Infrastructure",
        "topic": "High Availability",
        "date": "2026-06-09",
        "start_time": "15:30",
        "end_time": "16:30",
        "room": "Hall F2",
        "speaker": "Hannah Mueller",
        "company": "Tessera Cloud",
        "level": "advanced",
        "capacity": 240,
        "registered_count": 220,
    },
    {
        "session_id": "S029",
        "title": "Kubernetes for the AI Era",
        "description": (
            "GPU scheduling, multi-tenant inference, and right-sizing "
            "training workloads on shared clusters."
        ),
        "track": "Cloud Infrastructure",
        "topic": "Kubernetes",
        "date": "2026-06-10",
        "start_time": "09:30",
        "end_time": "10:30",
        "room": "Hall F1",
        "speaker": "Diego Alvarez",
        "company": "Stratos Compute",
        "level": "intermediate",
        "capacity": 300,
        "registered_count": 260,
    },
    {
        "session_id": "S030",
        "title": "Cost-Aware Cloud Architecture",
        "description": (
            "Finops in practice: chargeback models, spot capacity strategies, "
            "and how to design services that gracefully degrade when budgets are tight."
        ),
        "track": "Cloud Infrastructure",
        "topic": "FinOps",
        "date": "2026-06-10",
        "start_time": "13:00",
        "end_time": "14:00",
        "room": "Hall F2",
        "speaker": "Olivia Park",
        "company": "Stratos Compute",
        "level": "intermediate",
        "capacity": 200,
        "registered_count": 130,
    },
    {
        "session_id": "S031",
        "title": "Edge Compute for Low-Latency AI",
        "description": (
            "Architectures for serving small specialized models at the edge "
            "while keeping orchestration centralized."
        ),
        "track": "Cloud Infrastructure",
        "topic": "Edge Compute",
        "date": "2026-06-11",
        "start_time": "11:00",
        "end_time": "12:00",
        "room": "Hall F1",
        "speaker": "Anika Desai",
        "company": "Stratos Compute",
        "level": "advanced",
        "capacity": 180,
        "registered_count": 95,
    },

    # ──────── Track 7: Data Engineering & Analytics ────────
    {
        "session_id": "S032",
        "title": "Observability for Distributed Systems",
        "description": (
            "Modern tracing, metrics, and logging stacks for systems with "
            "hundreds of services. We focus on cardinality control, sampling, "
            "and the cost/insight tradeoff."
        ),
        "track": "Data Engineering & Analytics",
        "topic": "Observability",
        "date": "2026-06-09",
        "start_time": "09:30",
        "end_time": "10:30",
        "room": "Hall G1",
        "speaker": "Owen Walsh",
        "company": "Cinder Analytics",
        "level": "intermediate",
        "capacity": 280,
        "registered_count": 240,
    },
    {
        "session_id": "S033",
        "title": "Data Quality for Real-Time Analytics",
        "description": (
            "Design patterns for catching upstream schema breakage, drift, "
            "and bad data in streaming pipelines before dashboards lie to executives."
        ),
        "track": "Data Engineering & Analytics",
        "topic": "Data Quality",
        "date": "2026-06-10",
        "start_time": "10:00",
        "end_time": "11:00",
        "room": "Hall G2",
        "speaker": "Priya Raman",
        "company": "Cinder Analytics",
        "level": "intermediate",
        "capacity": 240,
        "registered_count": 188,
    },
    {
        "session_id": "S034",
        "title": "Lakehouse Architectures for the Mid-Sized Enterprise",
        "description": (
            "How a 2,000-person company adopted a lakehouse pattern in 9 months "
            "without a heroic platform team."
        ),
        "track": "Data Engineering & Analytics",
        "topic": "Lakehouse",
        "date": "2026-06-10",
        "start_time": "14:00",
        "end_time": "15:00",
        "room": "Hall G1",
        "speaker": "Felix Brandt",
        "company": "Cinder Analytics",
        "level": "beginner",
        "capacity": 220,
        "registered_count": 100,
    },
    {
        "session_id": "S035",
        "title": "Vector Search in Production",
        "description": (
            "Index choice, hybrid retrieval, and cost-aware re-ranking for "
            "vector workloads at billion-document scale."
        ),
        "track": "Data Engineering & Analytics",
        "topic": "Vector Search",
        "date": "2026-06-11",
        "start_time": "10:30",
        "end_time": "11:30",
        "room": "Hall G2",
        "speaker": "Wen Zhang",
        "company": "Northbeam AI",
        "level": "advanced",
        "capacity": 200,
        "registered_count": 175,
    },
    {
        "session_id": "S036",
        "title": "Self-Serve Analytics that Doesn't Hate Analysts",
        "description": (
            "Semantic layers, governed metrics, and the political work of "
            "making BI tools that PMs actually use without breaking the warehouse bill."
        ),
        "track": "Data Engineering & Analytics",
        "topic": "Self-Serve BI",
        "date": "2026-06-11",
        "start_time": "14:00",
        "end_time": "15:00",
        "room": "Hall G1",
        "speaker": "Rachel Kim",
        "company": "Cinder Analytics",
        "level": "intermediate",
        "capacity": 180,
        "registered_count": 80,
    },

    # ──────── Track 8: Developer Platforms ────────
    {
        "session_id": "S037",
        "title": "Building Internal Developer Platforms",
        "description": (
            "From golden paths to portals: lessons learned standing up an "
            "IDP that 800 engineers actually adopted, and the org structure "
            "that made it possible."
        ),
        "track": "Developer Platforms",
        "topic": "Internal Developer Platforms",
        "date": "2026-06-09",
        "start_time": "11:30",
        "end_time": "12:30",
        "room": "Hall H1",
        "speaker": "Tomás García",
        "company": "Forge Platforms",
        "level": "intermediate",
        "capacity": 260,
        "registered_count": 235,
    },
    {
        "session_id": "S038",
        "title": "Paved Roads for AI Application Development",
        "description": (
            "How to give your engineers a sane, opinionated toolkit for "
            "building LLM-powered features without reinventing eval, "
            "secrets, and observability fifty times."
        ),
        "track": "Developer Platforms",
        "topic": "AI Platforms",
        "date": "2026-06-10",
        "start_time": "09:00",
        "end_time": "10:00",
        "room": "Hall H2",
        "speaker": "Olivia Park",
        "company": "Forge Platforms",
        "level": "intermediate",
        "capacity": 240,
        "registered_count": 198,
    },
    {
        "session_id": "S039",
        "title": "Service Catalogs that Aren't Spreadsheets",
        "description": (
            "Real-world strategies for keeping a service catalog current, "
            "ownership clear, and on-call rotations sane."
        ),
        "track": "Developer Platforms",
        "topic": "Service Catalog",
        "date": "2026-06-10",
        "start_time": "15:00",
        "end_time": "16:00",
        "room": "Hall H1",
        "speaker": "Carlos Mendes",
        "company": "Forge Platforms",
        "level": "beginner",
        "capacity": 200,
        "registered_count": 95,
    },
    {
        "session_id": "S040",
        "title": "DX Metrics that Predict Velocity",
        "description": (
            "Beyond DORA: what to measure, what to ignore, and how to talk "
            "about developer productivity with leadership without lying."
        ),
        "track": "Developer Platforms",
        "topic": "Developer Experience",
        "date": "2026-06-11",
        "start_time": "09:00",
        "end_time": "10:00",
        "room": "Hall H1",
        "speaker": "Sara Devlin",
        "company": "Forge Platforms",
        "level": "intermediate",
        "capacity": 220,
        "registered_count": 150,
    },

    # ──────── Track 9: Product Leadership ────────
    {
        "session_id": "S041",
        "title": "Product Strategy in the AI Platform Era",
        "description": (
            "How product leaders are repositioning their roadmaps as "
            "foundation models commoditize features that took years to build."
        ),
        "track": "Product Leadership",
        "topic": "AI Strategy",
        "date": "2026-06-09",
        "start_time": "16:00",
        "end_time": "17:00",
        "room": "Keynote Stage",
        "speaker": "Elena Martínez",
        "company": "Vertica Systems",
        "level": "intermediate",
        "capacity": 600,
        "registered_count": 580,
    },
    {
        "session_id": "S042",
        "title": "Pricing AI Features Without Going Bankrupt",
        "description": (
            "Usage-based, seat-based, value-based: a structured way to "
            "decide how to price features whose marginal cost is real."
        ),
        "track": "Product Leadership",
        "topic": "AI Pricing",
        "date": "2026-06-10",
        "start_time": "13:30",
        "end_time": "14:30",
        "room": "Keynote Stage",
        "speaker": "Daniel Roth",
        "company": "Tessera Cloud",
        "level": "advanced",
        "capacity": 500,
        "registered_count": 460,
    },
    {
        "session_id": "S043",
        "title": "PM as Editor-in-Chief: Leading AI Product Teams",
        "description": (
            "Why managing AI products requires more taste, faster iteration, "
            "and a different relationship with engineering than classical SaaS."
        ),
        "track": "Product Leadership",
        "topic": "Product Management",
        "date": "2026-06-11",
        "start_time": "10:00",
        "end_time": "11:00",
        "room": "Keynote Stage",
        "speaker": "Aisha Khan",
        "company": "Atlas Labs",
        "level": "intermediate",
        "capacity": 500,
        "registered_count": 320,
    },
    {
        "session_id": "S044",
        "title": "From Discovery to GTM for Vertical AI Products",
        "description": (
            "Designing AI products for verticals like healthcare, legal, "
            "and logistics: domain partnerships, evals, and pilot rollouts."
        ),
        "track": "Product Leadership",
        "topic": "Vertical AI",
        "date": "2026-06-11",
        "start_time": "15:00",
        "end_time": "16:00",
        "room": "Keynote Stage",
        "speaker": "Camille Laurent",
        "company": "Vertica Systems",
        "level": "beginner",
        "capacity": 400,
        "registered_count": 180,
    },

    # ──────── Track 10: Compliance & Risk ────────
    {
        "session_id": "S045",
        "title": "Compliance Automation for Regulated Industries",
        "description": (
            "How to use evidence collectors, control libraries, and continuous "
            "monitoring to keep SOC 2, ISO 27001, and HIPAA reviews from "
            "becoming all-hands fire drills."
        ),
        "track": "Compliance & Risk",
        "topic": "Compliance Automation",
        "date": "2026-06-09",
        "start_time": "10:30",
        "end_time": "11:30",
        "room": "Hall I1",
        "speaker": "Hiroshi Tanaka",
        "company": "Aegis Compliance",
        "level": "intermediate",
        "capacity": 240,
        "registered_count": 210,
    },
    {
        "session_id": "S046",
        "title": "Third-Party Risk Management for AI Vendors",
        "description": (
            "A modern playbook for evaluating model vendors, eval providers, "
            "and AI infrastructure partners — including DPAs, model "
            "transparency, and incident response expectations."
        ),
        "track": "Compliance & Risk",
        "topic": "Vendor Risk",
        "date": "2026-06-10",
        "start_time": "11:30",
        "end_time": "12:30",
        "room": "Hall I2",
        "speaker": "Renata Costa",
        "company": "Aegis Compliance",
        "level": "advanced",
        "capacity": 200,
        "registered_count": 145,
    },
    {
        "session_id": "S047",
        "title": "Privacy Engineering for AI Products",
        "description": (
            "Practical patterns for data minimization, purpose limitation, "
            "and user consent in features that learn from user behavior."
        ),
        "track": "Compliance & Risk",
        "topic": "Privacy",
        "date": "2026-06-10",
        "start_time": "16:30",
        "end_time": "17:30",
        "room": "Hall I1",
        "speaker": "Ingrid Sørensen",
        "company": "Aegis Compliance",
        "level": "intermediate",
        "capacity": 180,
        "registered_count": 120,
    },
    {
        "session_id": "S048",
        "title": "Audit-Ready Logging for Agent Decisions",
        "description": (
            "What a 'reasonable' audit trail looks like when an AI agent "
            "made a consequential decision, and how to capture it without "
            "drowning your storage budget."
        ),
        "track": "Compliance & Risk",
        "topic": "Audit & Logging",
        "date": "2026-06-11",
        "start_time": "11:30",
        "end_time": "12:30",
        "room": "Hall I1",
        "speaker": "Ben Carter",
        "company": "Aegis Compliance",
        "level": "intermediate",
        "capacity": 160,
        "registered_count": 80,
    },
    {
        "session_id": "S049",
        "title": "Regulatory Roundup: AI, Payments, and Data Across Jurisdictions",
        "description": (
            "A panel of regulatory affairs leaders comparing notes on "
            "the EU AI Act, US state-level AI regulation, and the next wave "
            "of global payment rules."
        ),
        "track": "Compliance & Risk",
        "topic": "Regulatory Affairs",
        "date": "2026-06-11",
        "start_time": "16:00",
        "end_time": "17:00",
        "room": "Hall I2",
        "speaker": "Adaeze Nwosu",
        "company": "Aegis Compliance",
        "level": "advanced",
        "capacity": 220,
        "registered_count": 110,
    },
    {
        "session_id": "S050",
        "title": "Closing Keynote: The Next Decade of Agentic Enterprise",
        "description": (
            "An optimistic, opinionated look at what changes when every "
            "knowledge worker has a fleet of agents — and what enterprises "
            "must invest in to stay competitive."
        ),
        "track": "Product Leadership",
        "topic": "Closing Keynote",
        "date": "2026-06-11",
        "start_time": "17:30",
        "end_time": "18:30",
        "room": "Keynote Stage",
        "speaker": "Ravi Subramanian",
        "company": "Atlas Labs",
        "level": "beginner",
        "capacity": 1000,
        "registered_count": 612,
    },
]


def _bucket_time_of_day(start_time: str) -> str:
    hour = int(start_time.split(":")[0])
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def build_sessions() -> List[Session]:
    """Materialize raw dicts into Session models, deriving time_of_day."""
    sessions: List[Session] = []
    for raw in SESSIONS_RAW:
        data = dict(raw)
        data["time_of_day"] = _bucket_time_of_day(data["start_time"])
        sessions.append(Session(**data))
    return sessions


__all__ = ["build_sessions", "SESSIONS_RAW"]
