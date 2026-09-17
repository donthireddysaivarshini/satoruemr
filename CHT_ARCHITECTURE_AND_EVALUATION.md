# Community Health Toolkit (CHT) Architectural Analysis & Satoru Foundation Evaluation

**Prepared for**: Satoru Foundation  
**System Evaluated**: Community Health Toolkit (CHT) by Medic vs. KoBoToolbox  
**Focus Area**: Memory Wellness Screening Camps (Urban & Rural Hyderabad)

---

## Executive Summary

Satoru Foundation's screening camps require moving away from KoBoToolbox due to its inability to maintain longitudinal health records, automate multi-stage cognitive referrals, or schedule follow-up visits. The Community Health Toolkit (CHT) provides a resilient, offline-first digital public health platform designed specifically for community health workers.

However, adopting CHT introduces architectural nuances:
- **Two distinct layers**: High-level declarative configuration (`satoru-config`) vs. the low-level platform engine (`cht-core`).
- **Development complexity**: Form and scoring modifications are fast and easy; core UI redesigns and fine-grained data isolation require deep full-stack engineering.

---

## 1. Benefits of CHT for Satoru Foundation

CHT was purpose-built by Medic for community health workers operating in low-resource, intermittent-connectivity environments.

```
                  ┌──────────────────────────────────────────────┐
                  │           SATORU CENTRAL SERVER              │
                  │   CouchDB Cluster (DigitalOcean / VPS)       │
                  └──────────────────────┬───────────────────────┘
                                         │
                   Bidirectional Sync    │ (Auto-replicates when
                   via CouchDB Protocol  │  connected to office Wi-Fi
                                         │  or mobile 4G hotspot)
                                         │
                  ┌──────────────────────▼───────────────────────┐
                  │        INTERN SMARTPHONE / TABLET            │
                  │  Embedded PouchDB Database (Local Storage)   │
                  │  • Read/Write records with 0ms latency       │
                  │  • 100% functional without internet         │
                  └──────────────────────────────────────────────┘
```

### 1.1 Offline-First Architecture (True Bidirectional Sync)
* **How it works**: Unlike applications where "offline" is an add-on (such as local caching that pushes once), CHT runs an embedded **PouchDB database inside the client app** on Android smartphones.
* **Impact**: In remote rural screening camps with zero cellular connectivity, interns can register participants, record cognitive scores (COG-5, MoCA), and review past clinical notes. When they return to network coverage or the Punjagutta office, PouchDB and CouchDB synchronize automatically with conflict resolution.

### 1.2 Longitudinal Patient Tracking vs. Isolated Form Submissions
* **How it works**: Each screened individual is treated as a persistent entity (`contact` of type `participant`) identified by a permanent UUID.
* **Impact**: When Intern A screens a participant at a camp in June, and Intern B conducts a follow-up assessment in August, Intern B sees the participant’s complete clinical history. This eliminates duplicate registrations and enables tracking cognitive decline over time.

### 1.3 Automated Task & Schedule Management
* **How it works**: CHT includes a declarative rules engine (`tasks.js`) that monitors patient records.
* **Impact**: Satoru's two-stage screening workflow is automated. If a participant scores above the threshold on Stage 1 (COG-5), the system automatically schedules a Stage 2 assessment (AD-8, HMSE, PHQ-9, EASI, SPPB) within 14 days and places it on the intern's daily task list.

### 1.4 Zero Licensing & Self-Hosted Data Sovereignty
* **License**: AGPL-3.0 (Digital Public Good).
* **Cost**: ₹0 software license fees. No per-user, per-submission, or per-gigabyte SaaS subscriptions.
* **Hosting**: Satoru owns the data completely on its own VPS (₹1,500–3,000/month on DigitalOcean, AWS Lightsail, or Hetzner), ensuring patient confidentiality and compliance with Indian data privacy standards.

---

## 2. The Two Systems: `satoru-config` vs. `cht-core`

A common source of confusion in CHT development is understanding where different features live. The platform is architecturally split into two layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      1. CHT CONFIG (satoru-config)                     │
│  • XLSForms / Enketo XML forms (COG-5, MoCA, PHQ-9)                    │
│  • contact-summary.templated.js (Patient profile cards & badges)       │
│  • tasks.js (Follow-up generation rules)                               │
│  • app_settings.json & translations (English, Telugu, Hindi)           │
│  ─► Compiled with `cht-conf`, deployed into CouchDB documents          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Runs on top of
┌───────────────────────────────────▼────────────────────────────────────┐
│                       2. CHT CORE (cht-core)                           │
│  • Webapp: Angular SPA, NgRx store, RxJS reactive streams, Webpack     │
│  • API Server: Node.js / Express backend                               │
│  • Sync & Storage: PouchDB in client, CouchDB on server                │
│  • Sentinel: Background worker daemon for transition rules             │
│  ─► Monolithic Docker images (`medic-os`, `cht-couchdb`)               │
└────────────────────────────────────────────────────────────────────────┘
```

### Layer 1: Application Configuration (`satoru-config`)
- **Nature**: Declarative rules, forms, and settings.
- **Workflow**: Non-programmers or low-code developers edit spreadsheets (XLSForms) and configuration JavaScript files. These are compiled using `cht-conf` into CouchDB configuration documents.
- **Scope**:
  - Adding or modifying screening forms (Enketo/ODK).
  - Defining clinical calculations, scoring rules, and cutoffs.
  - Designing participant summary cards and warning badges (`contact-summary.templated.js`).
  - Scheduling follow-up reminders (`tasks.js`).
  - Translations (English, Telugu, Hindi).
- **Limitation**: Cannot alter application routing, navigation tabs, branding layouts, or core database synchronization behavior.

### Layer 2: Platform Engine (`cht-core`)
- **Nature**: Full-stack enterprise web application and infrastructure.
- **Workflow**: TypeScript, Angular, NgRx (Redux pattern), RxJS reactive streams, CouchDB views/design documents, and Docker multi-container packaging.
- **Scope**:
  - Core navigation, toolbar, and layout rendering.
  - Authentication, session security, and role-based permissions.
  - Granular entity-level visibility filters (e.g., Phase 2K intern participant privacy).
  - PouchDB-to-CouchDB synchronization pipelines.
- **Limitation**: Any modification requires TypeScript compilation, bundle generation, Docker image rebuilds, and maintaining an internal fork.

---

## 3. Drawbacks & Technical Complexity

While CHT is exceptionally reliable once deployed, iterating on custom features has distinct challenges:

### 3.1 Enterprise-Scale Frontend Monolith
The web application is an enterprise Angular SPA with hundreds of interconnected services and an NgRx Redux store. Making changes to component behavior (such as filtering participants from search) requires handling:
- Reactive RxJS subscription lifecycles.
- Redux actions, reducers, and memoized selectors.
- CHT’s internal database change feed (`changes.service`).

### 3.2 The Offline CouchDB Security Constraint
In a traditional client-server architecture (e.g., Next.js + PostgreSQL), access control is simple: the server queries only records matching `WHERE created_by = current_user`.
In CHT:
- Data replicates directly into the mobile device's PouchDB database.
- CouchDB document-level replication rules cannot be easily altered per individual role without complex CouchDB replication design filters.
- Consequently, fine-grained isolation (such as hiding other interns' participants) requires disciplined multi-point guards across routes, search indices, and profile views in the Angular layer.

### 3.3 Fork Maintenance Overhead
When you modify `cht-core` directly, you are maintaining a fork of upstream Medic CHT. When Medic releases future versions (e.g., CHT 4.x to 5.x with security updates), your team must merge upstream changes and resolve code conflicts.

### 3.4 Build and Deployment Cycles
Unlike modern lightweight web apps with instant hot-reloading, compiling `cht-core` involves Angular AOT compilation (`ngc`), Webpack asset bundling, and Docker container deployment.

---

## 4. Case Study: KoBoToolbox vs. CHT for Satoru Foundation

| Feature Area | KoBoToolbox (Past) | Community Health Toolkit (CHT) |
| :--- | :--- | :--- |
| **Data Architecture** | Isolated survey submissions. Each camp visit creates a disconnected row. | **Longitudinal EMR**. Persistent participant profile holding lifetime visit history. |
| **Stage 1 ➔ Stage 2 Referral** | Manual tracking via Excel sheets. High rate of loss-to-follow-up. | **Automated Task Scheduling**. Stage 1 positive (COG-5) automatically triggers Stage 2 tasks with deadlines. |
| **Offline Reliability** | Basic browser form cache; prone to submission conflicts and data loss. | **Native PouchDB/CouchDB Sync**. Tested on over 180,000 CHWs in zero-connectivity areas. |
| **Clinical Scoring** | Calculations within single form only; cannot compare across visits. | Dynamic multi-visit scoring (evaluates cognitive change between June and August visits). |
| **User Interface** | Generic survey form list. | Role-tailored health worker UI with patient directory, clinical cards, and task checklists. |
| **Cost** | Free tier has submission limits; server setup required. | 100% Free & Open-Source (AGPL-3.0). Self-hosted on VPS for ₹1,500–3,000/month. |
| **Technical Maintenance** | Low (No developer required). | Medium-High (Requires developer for setup and core customizations). |

---

## 5. Future Extensibility: How Complex Is It to Change UI or Add Features?

When Satoru Foundation plans future enhancements, use this matrix to estimate effort:

```
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 1: CONFIG-LAYER CHANGES (Low Complexity: Hours to 1-2 Days)      │
│ Done purely inside `satoru-config` — No code compile, no Docker rebuild│
├────────────────────────────────────────────────────────────────────────┤
│ • Add a new assessment scale (e.g., AD-8, HMSE, EASI, SPPB).           │
│ • Update clinical cutoff thresholds or scoring formulas.               │
│ • Add new demographic fields (e.g., Aadhaar, ABHA ID, education level).│
│ • Update participant summary cards, badges, and status banners.        │
│ • Add or modify Telugu/English/Hindi translations.                     │
│ • Adjust follow-up task time windows (e.g., 14 days ➔ 7 days).         │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 2: CORE-LAYER CHANGES (Medium to High Complexity: 1 to 2 Weeks)  │
│ Touches `cht-core` Angular TypeScript source and requires build/deploy │
├────────────────────────────────────────────────────────────────────────┤
│ • Custom UI redesigns (modifying top navigation bar, tabs, CSS themes).│
│ • Role-based data visibility rules (such as Phase 2K ownership guard). │
│ • Custom data export engines for research papers (SPSS / R / CSV).     │
│ • Integration with external national health systems (ABDM M1/M2 APIs). │
│ • Custom analytics charts not supported by standard CHT targets.       │
└────────────────────────────────────────────────────────────────────────┘
```

### Strategic Guidance for Satoru Foundation:
1. **Maximize `satoru-config`**: Whenever possible, implement requirements through forms, summary scripts, and task definitions. This preserves compatibility with upstream Medic updates.
2. **Modularize Core Changes**: When core changes are essential (such as the intern access boundary in Phase 2K), keep them encapsulated in dedicated services (like `ParticipantAccessService`) with comprehensive unit-test coverage to ensure smooth future upgrades.
