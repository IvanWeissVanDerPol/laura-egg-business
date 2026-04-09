# ⚠️ THIS REPO IS NOT THE LIVE WEBSITE

**As of 2026-04-09, the live Granja Cabral (Laura's egg business) website is hosted inside the Paragu-AI (formerly Vete) multi-tenant platform.**

## Where to find the live site

- **Live URL:** https://paragu-ai.com/granja-cabral
- **Tenant config:** [Ai-Whisperers/Vete/web/.content_data/granja-cabral/](https://github.com/Ai-Whisperers/Vete/tree/main/web/.content_data/granja-cabral)
- **Deploy:** Docker Swarm on agentzero VPS, Traefik → paragu-ai.com

## Where to make changes

| Change type                         | Where                                              |
|-------------------------------------|----------------------------------------------------|
| Content (copy, services, pricing)   | `Vete/web/.content_data/granja-cabral/*.json`            |
| Brand (colors, fonts, logo)         | `Vete/web/.content_data/granja-cabral/theme.json`        |
| Domain routing                      | `Vete/web/.content_data/domains.json`              |
| Custom code / components            | `Vete/web/app/[clinic]/*` (shared across tenants)  |

## What this repo is for now

This repo contains the full **farm operations management** for Granja Cabral: 18 top-level domains covering core operations, products, sales, supply chain, market intelligence, business plan, logistics, marketing, risk management, HR, and expansion. The **website content** (brand theme, contact, products) has been consolidated into the `granja-cabral` tenant in Ai-Whisperers/Vete. This repo remains the source of truth for farm ops, supplier/client contacts, financial tracking, and strategic planning.

## Do not

- Do not deploy this repo standalone to production
- Do not treat this as the source of truth for website content
- Do not make content changes here expecting them to go live

---

_This repo is kept for history and non-website assets. Website-layer consolidation tracked in Ai-Whisperers/Vete PR #65 (merged)._
