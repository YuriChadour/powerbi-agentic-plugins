# Quick Start: Prep Power BI for Report Copilot Pane

**Time: 5 minutes to install | 2–4 hours to run full workflow**

---

## ⚡ Installation (1 minute)

### Option A: Automated (Recommended)
```powershell
# Windows PowerShell / PowerShell 7+
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
iwr "https://raw.githubusercontent.com/bayviewasset/prep-powerbi-for-report-copilot/main/install-skill.ps1" | iex
```

### Option B: Manual Clone
```powershell
# Clone the repo
git clone https://github.com/bayviewasset/prep-powerbi-for-report-copilot.git
cd prep-powerbi-for-report-copilot

# Copy to Copilot CLI extensions
$CopilotExt = "$env:USERPROFILE\.copilot\extensions"
Copy-Item -Path . -Destination "$CopilotExt\prep-powerbi-for-report-copilot" -Recurse -Force
```

**Verify installation:**
```powershell
copilot
# You should see: "prep-powerbi-for-report-copilot" listed under loaded skills
```

---

## 🎯 Do You Need This Skill?

| You should use this if... | Skip if... |
|---|---|
| ✓ You want Copilot to reference existing visuals (not generate new ones) | ✗ Your report has <5 visuals |
| ✓ You have 10+ common questions users ask | ✗ Your report is read-only exploratory |
| ✓ You want consistent Copilot answers across your team | ✗ You''re OK with Copilot generating any visual |
| ✓ You have sensitive data to hide from Copilot | ✗ All data is public |

---

## 🚀 First 30 Minutes (Overview)

### Step 1: Gather Information (10 min)
Collect these before starting:

1. **Report location**
   - Path to your PBIP or PBIX file
   - Example: `C:\Projects\Portfolio\Portfolio.Semantic\`

2. **Business domain** (2–5 sentences)
   - "This report shows portfolio performance for loan-level analysis. Primary users are portfolio managers who monitor delinquency trends, prepayment rates, and loss severity."

3. **User personas** (2–3 examples)
   - Portfolio Manager, Risk Analyst, CFO

4. **Top 10 questions** Copilot should answer
   - "What''s the average portfolio balance by state?"
   - "Show me loans that are 60+ days delinquent"
   - "Which properties have the highest LTV?"
   - ... (list all 10)

5. **Sensitive fields** (if any)
   - SSN, taxpayer ID, borrower email
   - Internal cost basis, wholesale prices

### Step 2: Start the Skill (5 min)
```powershell
cd C:\your\powerbi\repo
copilot
/skill prep-powerbi-for-report-copilot
```

The skill will ask:
- Report name & format (PBIP/PBIX)?
- Business domain?
- User personas?
- Top questions?
- Sensitive fields policy?

### Step 3: Review Generated Docs (15 min)

After the skill completes, you''ll have:

```
docs/copilot-prep/
├── 01-report-usage-inventory.md      ← Which fields each visual uses
├── 02-ai-schema-recommendations.md   ← Include/exclude list
├── 03-ai-instructions.md              ← Terminology & defaults
├── 04-answer-pack-design.md           ← Visual strategy
└── 05-test-script-and-results.md      ← Test results
```

**Open each file and review.** You''ll see recommendations like:
- "INCLUDE [Total Current Balance $M] in Copilot schema"
- "EXCLUDE factweeklyposition[Current Balance] (use measure instead)"
- "Map ''balance'' term to [Total Current Balance $M]"

---

## ✅ Success Criteria

You''re done when:
- [ ] All 5 markdown docs complete
- [ ] ≥70% of top questions answered using existing visuals
- [ ] No sensitive fields exposed in Copilot schema
- [ ] Team agrees terminology mapping is accurate

---

**Need help?** See SKILL.md or open an issue on GitHub.
