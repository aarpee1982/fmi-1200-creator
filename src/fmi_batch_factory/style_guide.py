"""
FMI Article Style Guide and Anti-AI Charter.
Single source of truth — injected into every prose prompt.
Based on the actual FMI article format from live reports.
"""

ANTI_AI_CHARTER = """
ANTI-AI WRITING CHARTER — MANDATORY FOR ALL PROSE:
1. Never use "not only this but also" in any form.
2. Never use rule of three. Do not list exactly 3 reasons. Use 1, 2, 4, or 5.
3. Do not overexplain one point across multiple long sentences. One point, once.
4. Minimize double quotes in paragraphs. Only when quoting a term or source directly.
5. No parenthetical explanations inside paragraphs more than once per section.
6. Never use em dashes. Comma, period, or rewrite.
7. Never always give exactly 2 points. Vary the count across sections.
8. Vary sentence length deliberately. Mix short with long.
9. Minimize: furthermore, additionally, moreover, therefore. Once per section at most.
10. Each article must open differently. Never repeat the same sentence structure.
"""

FMI_FORMAT_GUIDE = """
FMI ARTICLE FORMAT — BASED ON REAL FMI REPORTS. FOLLOW EXACTLY.

===========================================================
SECTION 1: OPENING BLOCK
===========================================================
Heading: "[Market Name] Size and Share Forecast Outlook By FMI"

One dense paragraph. Must include:
- Market value in 2025 (base year)
- Market value in 2026
- Market value in the forecast end year
- CAGR during forecast period
- Leading segment in each segment dimension with its share % in 2026

Example:
"The [market] was valued at USD X.X billion in 2025. The market is projected to reach USD X.X billion in 2026 and USD X.X billion by [end year], expanding at a CAGR of X.X% during the forecast period. [Lead segment A] are expected to lead [dimension 1] with a X.X% share in 2026. [Lead segment B] is projected to remain the leading [dimension 2] with a X.X% share in 2026. [Lead segment C] are expected to lead [dimension 3] demand with a X.X% share in 2026."

===========================================================
SECTION 2: SUMMARY
===========================================================
Heading: "Summary of [Market Name]"

A) Subheading: "Key Drivers"
   Bullet list, 4-6 items. Each bullet = one line.
   Format: "[Short label]: [One sentence explanation]."

B) Subheading: "Key Segments Analyzed in the Report"
   Flat bullet list. One bullet per segment dimension.
   Format: "[Dimension]: [segment 1], [segment 2], [segment 3], ..."
   Always include Region as the last dimension.

C) Subheading: "Analyst Opinion"
   One short paragraph. Must start with analyst name and title.
   Format: "[Name], [Title] at FMI says, '[Specific insight about where value sits. Not a summary. A real point of view.]'"
   The insight must be specific to this market's commercial dynamics.

===========================================================
SECTION 3: MARKET DEFINITION
===========================================================
Heading: "[Market Name] Definition"

One clear paragraph. Covers:
- What product/equipment/consumable categories are in scope
- What operations or use cases are covered
- What manufacturing or commercial environments are included
No bullets. No hedging. No filler.

===========================================================
SECTION 4: INCLUSIONS
===========================================================
Heading: "[Market Name] Inclusions"

Bullet list, 3-5 items. Each = one specific line about what IS in scope.
Write as bullets, not paragraphs.

===========================================================
SECTION 5: EXCLUSIONS
===========================================================
Heading: "[Market Name] Exclusions"

Bullet list, 3-5 items. Each = one specific line about what is OUT of scope.
Write as bullets, not paragraphs.

===========================================================
SECTION 6: RESEARCH METHODOLOGY
===========================================================
Heading: "[Market Name] Research Methodology"

One paragraph. Cover:
- Base year and forecast period
- Types of evidence inputs (regulatory filings, company disclosures, product launches, technical literature)
- How the estimate was triangulated (vendor revenue anchors, modality trends, consumption intensity, etc.)
No bullet list. Real prose about this specific market.

===========================================================
SECTION 7: KEY DRIVERS, RESTRAINTS, AND TRENDS
===========================================================
Heading: "Key Drivers, Restraints, and Trends in [Market Name]"

Three sub-sections with PROSE PARAGRAPHS — no bullets at all:

A) Subheading: "Drivers"
   One paragraph. Cover 4-5 demand forces specific to this market.
   Name specific regulations, therapy types, operational pressures.

B) Subheading: "Restraints"
   One paragraph. Cover 3-4 specific friction points: supply concerns, validation costs, integration issues, switching barriers.

C) Subheading: "Trends"
   One paragraph. Cover 2-4 structural shifts: how buyer behavior is changing, how suppliers are repositioning.

ALL THREE MUST BE PROSE. NO BULLETS.

===========================================================
SECTION 8: SEGMENTAL ANALYSIS
===========================================================
Heading: "Segmental Analysis"

One sub-section per segment dimension.
Subheading format: "[Market Name] Analysis by [Segment Dimension]"

Each sub-section = ONE PROSE PARAGRAPH. Must:
- State which segment leads with its exact share %
- Explain WHY it leads — specific operational or commercial reason
- Cite a company or regulatory reference if available
NO bullets. NO "support bullets". Pure prose.

===========================================================
SECTION 9: COMPETITIVE ALIGNERS
===========================================================
Heading: "Competitive Aligners for Market Players"

Two paragraphs:
Para 1: What actually wins in this market. What buyers require beyond product breadth. Name 1-2 specific companies.
Para 2: How competitive advantage is shifting. Name specific M&A, partnerships, or strategic moves. End with what market leadership is being built around.

NO bullets. Prose only.

===========================================================
SECTION 10: KEY PLAYERS
===========================================================
Heading: "Key Players in [Market Name]"

Flat list of company names. 8-12 companies. Names only, no descriptions.

===========================================================
SECTION 11: STRATEGIC OUTLOOK BY FMI
===========================================================
Heading: "Strategic Outlook by FMI on [Market Name]"

One paragraph. The FMI house view on where the market goes next.
Specific to this market. Name the structural shift underway. Name what determines who wins.
Not generic. Not a summary of what was said earlier.

===========================================================
SECTION 12: SCOPE OF THE REPORT
===========================================================
Heading: "Scope of the Report"

Table rows:
- Market Value: "USD X.X billion in 2026 to USD X.X billion by [end year]"
- CAGR: "X.X% from 2026 to [end year]"
- Base Year: 2025
- Forecast Period: 2026 to [end year]
- [Dimension 1] Segmentation: [full list]
- [Dimension 2] Segmentation: [full list]
- [Dimension 3] Segmentation: [full list]
- Regions Covered: North America, Latin America, Europe, East Asia, South Asia Pacific, Middle East and Africa

===========================================================
SECTION 13: BIBLIOGRAPHY
===========================================================
Heading: "Bibliography"

5-7 citations. Format:
"[Organization]. [Year]. [Title]."
Examples:
"European Commission. 2022. EU GMP Annex 1: Manufacture of Sterile Medicinal Products."
"Sartorius. 2026. Preliminary Results 2025 and Annual Report 2025."

Only real citable sources: regulatory bodies, company filings, government agencies.
DO NOT fabricate citations.

===========================================================
SECTION 14: FREQUENTLY ASKED QUESTIONS
===========================================================
Heading: "Frequently Asked Questions"

8-10 Q&A pairs. Market-specific questions only. Each answer = 1-2 sentences.

Required questions (adapt to this market):
1. How large is the [market] in 2025?
2. What will be the [market] size by [end year]?
3. What is the expected growth rate?
4. Which [dimension 1] leads the market?
5. Which [dimension 2] is dominant?
6. Which [dimension 3] contributes the largest share?
7. Which region is the largest market?
8. Which region grows fastest?
9. What is the main structural shift in the market?
10. Why do [leading commercial dynamic — e.g. recurring consumables] matter so much?

===========================================================
DO NOT INCLUDE THESE SECTIONS (not in real FMI format):
===========================================================
- "This Report Addresses"
- "Recent Developments" as a standalone section
- "Market Key Takeaways" as a separate table
- "Strategic Implications" bullet list
- Generic 4-bullet methodology list
- "Country CAGR paragraph" as standalone block

===========================================================
PROSE RULES:
===========================================================
- Market name verbatim. Never shorten.
- All values: "USD X.X billion"
- All CAGRs: "a CAGR of X.X%" or "X.X% CAGR"
- Analyst views in body: "FMI is of the opinion that..."
- Analyst opinion in summary: "[Name], [Title] at FMI says, '...'"
- No: "data limitations", "not quantified", "high uncertainty", "modelled analyst estimate"
- No: "working note", "internal note", "based on norms", "based on proxy"
- Drivers, Restraints, Trends, Segmental Analysis, Competitive Aligners: PROSE PARAGRAPHS ONLY, never bullets
"""

FULL_STYLE_BLOCK = ANTI_AI_CHARTER + "\n" + FMI_FORMAT_GUIDE
