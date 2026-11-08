"""Build playbook.docx: the operating model, cadence, agendas and flow specs.
Usage: python build_playbook.py [output.docx]
"""
import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "playbook.docx"

doc = Document()
st = doc.styles["Normal"]
st.font.name, st.font.size = "Calibri", Pt(11)
for lvl in (1, 2, 3):
    doc.styles[f"Heading {lvl}"].font.color.rgb = RGBColor(0x1F, 0x4E, 0x78)

H = doc.add_heading
def P(t, style=None): return doc.add_paragraph(t, style=style)
def B(items):
    for i in items: P(i, "List Bullet")
def N(items):
    for i in items: P(i, "List Number")
def T(header, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for c, h in zip(t.rows[0].cells, header): c.text = h
    for r in rows:
        for c, v in zip(t.add_row().cells, r): c.text = str(v)
    doc.add_paragraph()

doc.add_heading("Scrum at portfolio scale", 0)
P("An operating playbook for running about 10 agile data science projects with Microsoft 365 and VS Code. "
  "It keeps every Scrum event and artifact. Routine status work moves to automation, and live time goes to demos, decisions and blockers.")

H("1. The problem in numbers", 1)
P("Run standard Scrum separately on 10 projects and the PM's calendar fills up fast:")
T(["Event", "Per project", "10 projects, hours per week"], [
    ["Daily Scrum", "15 min x 5 days", "12.5"],
    ["Sprint Planning", "2 h per 2-week sprint", "10.0"],
    ["Sprint Review", "1 h per sprint", "5.0"],
    ["Retrospective", "1 h per sprint", "5.0"],
    ["Refinement", "1 h per week", "10.0"],
    ["Total", "", "42.5"],
])
P("This playbook gets that down to about 6 hours a week of live meetings:")
T(["Live event", "Frequency", "Hours per week"], [
    ["Scrum of Scrums (blockers only)", "15 min, Tue and Thu", "0.5"],
    ["Sprint Day: Review 45 min + Retro 30 min + Planning 60 min, per cluster", "3 clusters, every 2 weeks", "3.4"],
    ["Refinement (rotating projects)", "45 min weekly", "0.75"],
    ["Reading standup digests", "15 min daily", "1.25"],
    ["Total", "", "about 5.9"],
])

H("2. Operating model", 1)
H("Shared cadence", 2)
B(["All projects run 2-week sprints that start and end on the same days. This is the release train idea from enterprise agile frameworks such as SAFe, and it lets ceremonies be batched.",
   "Sprint Day is every second Monday. Each cluster runs Review, then Retro, then Planning, back to back.",
   "Every 6 sprints (one quarter) there is a half-day PI planning session: quarterly objectives per project, a dependency map, and a risk log using ROAM (Resolved, Owned, Accepted, Mitigated)."])
H("Clusters", 2)
T(["Cluster", "Projects", "Typical stakeholders"], [
    ["Forecasting", "Demand Forecast, Price Elasticity, Churn Model, Inventory Optimisation", "Supply chain, commercial, retention"],
    ["NLP", "Ticket Classifier, Document Search, Sentiment Monitor", "Support, legal, brand"],
    ["Platform", "Feature Store, MLOps Pipeline, Data Quality Monitor", "Head of Data, governance"],
])
P("Group by shared stakeholders first and shared people second. A data scientist on two projects should sit in one cluster where possible, so they attend one Sprint Day block.")
H("Roles", 2)
B(["Product Owner per project (can cover 2 or 3 projects in one cluster). Owns the backlog and sprint goal.",
   "PM / Scrum Master across the portfolio. Owns cadence, automation, impediments and the portfolio view.",
   "Development Team: data scientists, ML engineers, data engineers. Own estimates and how the work gets done.",
   "Cluster lead (optional, senior DS). Runs the cluster's technical refinement and attends Scrum of Scrums."])
H("Data science adaptations", 2)
T(["Work type", "Sized by", "Done means"], [
    ["Story", "Story points", "Acceptance criteria met, code reviewed, tests pass"],
    ["Experiment / Spike", "Timebox in days (3 or 5)", "Hypothesis tested, result written up, outcome recorded: Go, Pivot or Kill"],
    ["Data task", "Story points", "Data versioned, documented, quality checks pass"],
    ["Model deployment", "Story points", "Model card updated, monitoring on, rollback tested"],
])
P("Experiments are written as hypotheses: \"If we add lag features, then MAPE falls by 3 points.\" A Kill is a good result if it was cheap. Sprint reviews report experiments closed and the win rate, so stakeholders see learning as well as features.")
H("Definition of Done (all work)", 2)
B(["Code in the repo and peer reviewed", "Metrics and parameters logged in the experiment tracker",
   "Training data versioned and reproducible", "Backlog item updated with outcome and links"])

H("3. Events: what stays live and what goes async", 1)
T(["Scrum event", "Live", "Automated or async"], [
    ["Daily Scrum", "15-min Scrum of Scrums, Tue and Thu, blockers only", "Teams adaptive-card check-in at 9:00, digest per project at 10:30"],
    ["Sprint Planning", "60-90 min per cluster on Sprint Day", "Draft scope, capacity and carry-over sent the Friday before"],
    ["Sprint Review", "30-45 min per cluster, demos and decisions", "Auto-generated deck and portfolio summary sent the Friday before"],
    ["Retrospective", "30 min per cluster, top 3 themes", "Forms survey opens 2 working days before, responses grouped into themes"],
    ["Refinement", "45 min weekly, 3 or 4 projects in rotation", "Hygiene script flags unready items, owners fix them async"],
])
H("Agendas", 2)
H("Scrum of Scrums (15 min)", 3)
N(["Overdue blockers from the Impediments list (auto-tagged after 48 hours)", "Cross-project dependencies due this week",
   "Anything a digest flagged that needs a decision"])
P("Attendees: PM, one person per cluster, POs only if needed. No status updates. Status is in the digest.")
H("Sprint Day, per cluster (about 2 h 15 min)", 3)
N(["Review (45 min): demos of done work and closed experiments. Stakeholders read the deck beforehand. Decisions recorded in the Backlog.",
   "Retro (30 min): the three highest-voted survey themes. One improvement action per project goes into the next sprint's backlog.",
   "Planning (60 min): each PO confirms the sprint goal; the team adjusts the draft scope against capacity. Cross-project dependencies checked."])
H("Sprint Day schedule", 3)
T(["Time", "Block"], [["09:30-11:45", "Forecasting"], ["12:30-14:45", "NLP"], ["15:00-17:15", "Platform"]])

H("4. Tools and data model", 1)
P("Single source of truth: one Microsoft List called Backlog (or Azure DevOps Boards if the company uses it). Every project shares the same columns so automation and reporting work across the portfolio.")
T(["List", "Key columns"], [
    ["Backlog", "ID, Project, Cluster, Type, Title, Status, Owner, Sprint, Estimate, Timebox, Acceptance Criteria, Blocked, Blocker Note, Hypothesis, Outcome, Started, Done Date, Last Updated"],
    ["Standup Log", "Date, Person, Project, Yesterday, Today, Blocked, Blocker Note"],
    ["Impediments", "ID, Project, Backlog ID, Raised, Owner, Description, Status, Resolved, Escalated"],
    ["Risks", "ID, Project, Type (Risk or Dependency), Description, ROAM, Owner, Depends On"],
    ["Sprint Snapshots", "Sprint, Project, Committed, Completed, Carried Over, Goal Met"],
])
T(["Tool", "Used for"], [
    ["Microsoft Lists / Azure DevOps", "Backlog and supporting lists"],
    ["Teams", "One channel per project, one per cluster, adaptive-card check-ins"],
    ["Power Automate", "Scheduled and event-driven flows (section 5)"],
    ["Forms", "Retro survey, quarterly stakeholder pulse"],
    ["Excel / Power BI", "Portfolio dashboard"],
    ["Loop / OneNote", "Retro notes, decision log, PI planning board"],
    ["VS Code + Python", "Hygiene checks, metrics, sprint review packs (section 6)"],
])

H("5. Power Automate flows", 1)
flows = [
    ("Flow 1: Async daily check-in",
     "Recurrence, 09:00 Mon-Fri (skip Sprint Day).",
     ["Get team members from the Projects list or a Teams group.",
      "Apply to each: \"Post adaptive card and wait for a response\" (Teams) using flows/standup_card.json.",
      "On response: Create item in Standup Log.",
      "If blocked = Y: start Flow 2.",
      "Second flow at 10:30: Get today's Standup Log items, group by project, post an HTML table to each project channel. Send the PM one cross-project summary listing missing check-ins and blockers."]),
    ("Flow 2: Blocker escalation",
     "When a Standup Log item or Backlog item has Blocked = Y.",
     ["Create an Impediments item (Status Open, Raised = now).",
      "Notify the PM and the PO in Teams with a link.",
      "Delay until Raised + 48 hours, then get the item again.",
      "If still Open: set Escalated = Y, add to the Scrum of Scrums agenda (Loop or Planner), and email the stakeholder."]),
    ("Flow 3: Sprint rollover",
     "Recurrence, 18:00 on the last working day of each sprint (read from the Calendar list).",
     ["Get Backlog items in the ending sprint.",
      "For each project: sum committed and done points, write a Sprint Snapshots row.",
      "Move unfinished items to the next sprint and tag them carry-over.",
      "Post a summary to the cluster channel."]),
    ("Flow 4: Retro survey",
     "Recurrence, 2 working days before Sprint Day.",
     ["Post the Forms link (went well, didn't, one change, 1-5 sprint score) to each cluster channel.",
      "On each response: add a row to the Retro Responses Excel table.",
      "Morning of Sprint Day: run Copilot or scripts to group responses into themes and post the top 3 per cluster."]),
    ("Flow 5: Stale work alert",
     "Recurrence, 08:00 daily.",
     ["Get Backlog items with Status In Progress or In Review and Last Updated older than 5 days.",
      "Send each owner one Teams message listing their stale items, with a link to update them."]),
    ("Flow 6: Weekly portfolio digest",
     "Recurrence, Friday 15:00.",
     ["Refresh the dashboard dataset (or run metrics.py on a schedule and save to SharePoint).",
      "Email leadership: RAG per project, decisions needed, top risks, link to the dashboard."]),
]
for title, trigger, steps in flows:
    H(title, 2)
    P(f"Trigger: {trigger}")
    N(steps)

H("6. VS Code scripts", 1)
P("The scripts read an Excel export of the lists (or a OneDrive-synced copy). If IT approves an app registration, they can read Microsoft Graph directly instead. Run them from the VS Code terminal or a scheduled task.")
T(["Script", "When", "Output"], [
    ["backlog_hygiene.py", "Before each refinement session", "Issues by owner: missing estimates, acceptance criteria, hypotheses, stale items, old blockers, missed check-ins"],
    ["metrics.py", "Weekly and at sprint end", "metrics.xlsx: velocity, say/do, carry-over, cycle time, experiment win rate, RAG"],
    ["sprint_report.py", "Friday before Sprint Day", "One review deck per cluster (.pptx) and a one-page portfolio summary (.docx)"],
])
P("Commands:")
for c in ["pip install pandas openpyxl python-docx python-pptx",
          "python scripts/backlog_hygiene.py --book backlog_export.xlsx --sprint S5",
          "python scripts/metrics.py --book backlog_export.xlsx --sprint S5",
          "python scripts/sprint_report.py --book backlog_export.xlsx --sprint S5"]:
    p = P(c); p.runs[0].font.name = "Consolas"; p.runs[0].font.size = Pt(9.5)

H("7. Metrics and dashboard", 1)
T(["Metric", "Why it matters", "Watch for"], [
    ["Sprint goal met (Y/N)", "The one number stakeholders care about", "Below 70% of sprints"],
    ["Say/Do ratio", "Planning accuracy", "Under 0.75 for 2 sprints"],
    ["Carry-over rate", "Overcommitment", "Over 25%"],
    ["Median cycle time", "Flow", "Rising trend"],
    ["Experiment win rate", "Healthy research mix", "Near 100% means experiments are too safe"],
    ["Blocker age", "PM effectiveness", "Anything over 48 hours"],
    ["Live meeting hours", "Whether the system works", "Creeping back above 8 per week"],
])
P("RAG rule used by the scripts: Red if 2+ blockers older than 48 hours or under 40% of the sprint done; Amber if any open blocker, under 65% done, or say/do under 0.75; otherwise Green.")

H("8. Rollout (first 90 days)", 1)
T(["When", "What", "Measure"], [
    ["Weeks 1-2", "Sit in on current ceremonies, count meeting hours, set up the Backlog list", "Baseline hours and pain points"],
    ["Weeks 3-4", "Pilot async check-in and blocker flow with one team", "Check-in response rate over 85%"],
    ["Month 2", "Align sprint dates, launch Sprint Day, retro survey and review packs", "Live hours under 8 per week"],
    ["Month 3", "Portfolio dashboard, first PI planning", "Stakeholder pulse score, blocker age"],
])
H("Risks and how to handle them", 2)
B(["Async check-ins become box-ticking. Keep the twice-weekly live huddle, read the digests, and act on them the same day.",
   "IT limits Power Automate connectors or Graph. Fall back to Excel exports and the Python scripts.",
   "Data scientists resist story points for research. Use timeboxes for experiments.",
   "Aligning sprint dates disrupts teams mid-sprint. Move each team at its next natural sprint boundary.",
   "Stakeholders still want a live status meeting. Send the pack first, then offer 15 minutes of questions."])

H("9. Interview talking points", 1)
B(["\"I'd keep every Scrum event, but run them at the right level: daily sync async, blockers live, ceremonies batched by cluster.\"",
   "\"For data science I treat experiments as time-boxed bets with a Go, Pivot or Kill outcome, so we report learning as well as delivery.\"",
   "\"I'd start by measuring. Ten projects under standard Scrum is about 40 hours of meetings a week for the PM. My target is under 8.\"",
   "\"Everything uses tools you already license: Lists, Teams, Power Automate, Forms, Excel or Power BI, plus a few Python scripts.\""])

H("Appendix: standup adaptive card", 1)
card = json.loads((ROOT / "flows" / "standup_card.json").read_text())
p = P(json.dumps(card, indent=1)[:3000])
for r in p.runs:
    r.font.name, r.font.size = "Consolas", Pt(8)

doc.save(OUT)
print(f"Wrote {OUT}")
