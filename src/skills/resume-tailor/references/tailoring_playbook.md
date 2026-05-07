# Tailoring Playbook

How to map a job description onto Vincent's master profile and produce a resume that reads like it was written for that specific job.

## Tailoring is editing, not invention

Tailoring means selecting and rephrasing what's already in the master profile. Inventing experience to match a JD is fabrication, ends careers, and makes you a worse advisor. If the JD asks for something he doesn't have, the right move is to call out the closest adjacent experience and flag the gap so Vincent can decide whether to apply.

## Anonymize the client (hard rule)

The master profile names PwC as the engagement client for internal accuracy. **On every generated artifact (resume, cover letter, recruiter pitch), the client must be anonymized as "Big 4 Accounting Firm" or "Big 4 professional services client" - never named as PwC.** See the master profile's "Anonymization Rule" section for the full substitution table. Inversion: if the JD is from PwC itself, name PwC as the target employer (it's then no longer the client to anonymize).

## Respect the master profile Flags section before every output

Before any bullet ships, scan the master profile's Flags section. Hard rules from the 2026-05-06 resolution pass:

- **AI Hooks framework** - never include. Was a proposal, never implemented.
- **FlowSource demo** - never include. Vincent directed it be skipped on all resumes.
- **MongoDB Certified Developer** - never include. Removed at user direction.
- **Claude Architect Certification** - never include. Not earned.
- **AI POC for partner's team** - Vincent's role was *reviewer / strategist*. Use "reviewed", "advised on", "set direction for". NEVER use "built", "led", "architected" for this POC.
- **15% productivity baseline** - IS claimable, with this exact framing: drove AI-tooling adoption (Cursor, Copilot, Claude) that *contributed to* a ~15% productivity baseline measured by the AI Productivity Index. Do NOT claim he designed the metric or owned the dashboard.
- **NGA delivery remediation** - IS claimable with minimal framing only: "provided architecture and domain context to NGA delivery-remediation discussions." Do NOT claim leadership of the recovery - that was someone else.

## Step-by-step

### 1. Decode the JD

Read the JD twice. First pass to understand the role; second pass to extract structured signals.

Pull out:
- **Title and seniority** - "Director of Engineering" vs. "Staff Engineer" vs. "Solution Architect" demand different framings of the same career.
- **Must-haves** - anything in "Required" / "Minimum qualifications" / "5+ years of X". These are ATS gates.
- **Nice-to-haves** - "Preferred" / "Bonus". These differentiate, not gate.
- **Technical stack** - exact technology names (Azure / AWS / GCP, .NET / Java, Angular / React, Kubernetes / ECS).
- **Methodology signals** - "Agile", "SAFe", "DevOps", "Platform engineering".
- **Domain signals** - financial services, audit/assurance, healthcare, AI/ML.
- **Leadership scope** - "manages a team of N", "owns roadmap", "individual contributor".
- **Cultural signals** - "fast-paced startup" implies different bullet emphasis than "Fortune 500 governance".

### 2. Pick the headline

From the master profile's Headline Inventory, choose the single closest match. Heuristics:
- "Director of Engineering" / "VP Engineering" → `Director of Software Development & Solution Architect`
- "Solution Architect" / "Principal Architect" / "System Architect" → `System Architect, Managed Services portfolio` or `Director of Software Development & Solution Architect`
- "Engineering Manager" / "Tech Lead" → consider `Associate Director, Cognizant` or `Manager of Application Architecture` framing
- AI / ML leadership roles → lead with current AI work; headline can be `Director of Software Development - AI-Assisted Engineering` (close to existing `Director of Software Development & Solution Architect` with emphasis)

Don't invent a brand-new title. Pick one from the inventory.

### 3. Write the summary (3-4 sentences)

Formula:
1. Sentence 1: years of experience + the strongest credibility signal that aligns with the JD.
2. Sentence 2: 2-3 high-impact themes from the JD's responsibilities, each tied to a specific track-record bullet from Vincent's history.
3. Sentence 3: a quantified achievement (preferably one that aligns with the JD's domain).
4. Optional sentence 4: differentiator (legal background, MS FinTech, or AI-assisted engineering certifications) only if it strengthens the case for THIS role.

Echo 2-3 of the JD's exact keywords if they're truthful. Don't shoehorn.

### 4. Order and rewrite the experience

**Default-include, default-exclude rules (RESUME only - cover letter and pitch are governed separately):**
- **Cognizant** - always include on resume.
- **Wachtell, Lipton, Rosen & Katz** - always include on resume.
- **J.P. Morgan** - DEFAULT OFF on resume. Include only if Vincent explicitly asks ("include J.P. Morgan", "show my banking background"). Cover letter and recruiter pitch MAY reference J.P. Morgan as career context when the JD is FinTech / capital markets / investment management - that's contextual prose, not work-history listing.
- **Mercer Management Consulting** - DEFAULT OFF on resume, cover letter, and pitch. Almost never adds value at this seniority.
- **Selected Projects (Where's My Train?, Definitely Typed)** - opt-in. Include only on JDs that benefit from open-source / mobile / TypeScript signals AND when the resume has space.

**Consolidate multi-role same-company entries to the senior title:**
When Vincent held multiple roles at the same company, render them as a SINGLE consolidated entry on the resume:
- **Title** = the most senior title held (e.g., "Manager of Application Architecture", "Associate Director, Solution Architecture & AI Engineering").
- **Dates** = the FULL span (junior-role start through senior-role end / Present), e.g., `07/1999 - 06/2018` for Wachtell, `08/2018 - Present` for Cognizant.
- **Context** = optional one-line note acknowledging the promotion path if it strengthens the case (e.g., "Promoted from Software Developer (1999-2004) to Manager of Application Architecture."). Skip if it adds clutter.
- **Bullets** = pull from BOTH the senior and junior roles, picking the strongest impact bullets across the entire tenure. Hard-dollar wins and quantified outcomes from the junior role are usually worth keeping. The senior bullets typically lead.

Rationale: visual fragmentation hurts readability, and a director-level resume with a single Cognizant entry showing 7+ years of progression reads stronger than two separate entries that look like job-hopping. The cover letter and recruiter pitch can still surface the promotion arc verbatim.

**Bullet count per consolidated entry (heuristic):**
- Cognizant (current, most-relevant role): 6-9 bullets.
- Wachtell (legacy, lower-relevance for most roles): 4-6 bullets.
- J.P. Morgan (when included): 1-2 lines max.
- Mercer (when included): 1 line max.

Rewrite each bullet so:
- It opens with a verb (Led, Architected, Reduced, Implemented).
- It states the **impact** before the activity if the impact is quantified.
- It uses the JD's wording where truthful - if the JD says "Kubernetes" and the master profile says "AKS", say "AKS (Kubernetes)" or "Kubernetes" depending on context.
- It does not exceed 2 lines (about 25 words).

### 5. Curate skills

Group skills semantically (Cloud & Infrastructure / Languages / Architecture / Data / AI-ML / DevOps / Leadership). Reorder so the JD-matched group leads. Within each group, lead with JD-mentioned skills.

Don't pad. If the JD asks for Java and Vincent's master profile only shows .NET / C#, do NOT add Java. Lead with .NET / C# and let Vincent decide whether to apply.

### 6. Length decisions

**Hard cap: 2 pages, no exceptions.** If the resume runs long, cut bullets - never spill to a third page.

Default heuristic for choosing 1 vs. 2 pages within the cap:
- **2 pages** for: Director / VP / Head of / Architect / Principal / Engineering Manager / Senior Lead.
- **1 page** for: Senior Engineer / Specialist / Consultant / contract roles where brevity is valued.
- **Override** if the user explicitly states a length.

For 2-page resumes, allocate the extra space to deeper Cognizant and Wachtell bullets - NOT to J.P. Morgan or Mercer, which are off by default per Step 4. For 1-page resumes, trim Wachtell to 3-4 bullets max.

If the rendered DOCX overflows 2 pages, the fix order is:
1. Trim the lowest-impact Wachtell bullet first.
2. Then trim a Cognizant Senior Manager-era bullet (if the consolidated Cognizant entry has 8+ bullets).
3. Then shorten the longest bullet to a single line.
4. Only as a last resort, condense the summary by one sentence.

### 7. Flag gaps in the tailoring notes

Always write a `tailoring_notes.md` file alongside the resume. Include:
- Headline chosen and why
- Top 3 themes emphasized
- Skills/requirements in the JD that Vincent doesn't have, and how the resume frames the gap
- Any items from the master profile's Flags section that came close to being used and were swapped
- Whether the user should apply (your honest read) - but always frame this as Vincent's call, not yours

## Common JD archetypes Vincent will see

These are recurring patterns. Pre-built tailoring notes to use as starting points.

### Director / VP of Engineering at a software company
- Lead with: people management at scale, cross-org architecture, modernization wins.
- Emphasize: Cognizant team-building, Wachtell budget ownership, microservice / cloud-native modernization.
- De-emphasize: deep individual coding bullets.

### Solution Architect / Principal Architect (consulting / services)
- Lead with: System Architect (PwC VIPR), USAT Architecture Review Board, Solution & System Architect Program Kickoff.
- Emphasize: cross-team architecture governance, enterprise patterns, multi-product platforms.
- De-emphasize: individual project deliverables unless they showcase architecture decisions.

### Staff / Principal Engineer (IC at a product company)
- Lead with: hands-on technical wins (40% perf, 35% defect reduction, microservice strategy authorship).
- Emphasize: depth on a few technologies; modern stack work; AI-assisted dev.
- De-emphasize: people management.

### AI / ML Engineering Leader
- Lead with: Professional Services AI Pilot (core team), Cursor parity validation, AI Productivity Index contribution, Anthropic certifications.
- Emphasize: enterprise AI POC delivery, governance, productivity metrics.
- De-emphasize: pre-2018 work; legal-tech specifics.

### FinTech / Capital Markets engineering
- Lead with: J.P. Morgan, Halo Investment Data Platform / JPMC AWM NA, MS FinTech (3.9 GPA, in progress / completed).
- Emphasize: financial-services domain depth, audit & assurance technology, regulatory context.
- De-emphasize: legal-tech bullets unless directly relevant.

### Big-4 / consulting account leadership
- Lead with: Cognizant Associate Director, dual-badge PwC engagement, 70% client cost savings via global delivery.
- Emphasize: architecture-team building (Dec 2024 roster), program kickoff leadership, multi-account AI enablement.
- De-emphasize: individual coding work.
