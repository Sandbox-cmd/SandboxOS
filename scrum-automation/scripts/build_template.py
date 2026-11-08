"""Build backlog_template.xlsx with sample data for 10 data science projects.

This is the single source of truth in Excel form. In production the same
columns live in Microsoft Lists (or Azure DevOps), and you export to this
layout, or point the scripts at a synced copy on OneDrive/SharePoint.

Usage:  python build_template.py [output.xlsx]
"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

random.seed(7)
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "backlog_template.xlsx"

TODAY = date(2026, 11, 6)          # "today" for the sample data (a Friday)
SPRINT_LEN = 14
SPRINT1_START = date(2026, 8, 31)  # Sprint Day Mondays
SPRINTS = [(f"S{i+1}", SPRINT1_START + timedelta(days=SPRINT_LEN * i)) for i in range(7)]
CURRENT = "S5"                     # S5 runs 26 Oct - 8 Nov
NEXT = "S6"

PROJECTS = [
    # name, cluster, product owner, stakeholder, sprint goal
    ("Demand Forecast", "Forecasting", "A. Rahman", "Supply Chain VP", "Ship weekly forecast v2 to planners"),
    ("Price Elasticity", "Forecasting", "J. Okafor", "Commercial Director", "Decide on hierarchical model approach"),
    ("Churn Model", "Forecasting", "L. Chen", "Retention Lead", "Retrain on Q3 data and A/B launch"),
    ("Inventory Optimisation", "Forecasting", "A. Rahman", "Ops Director", "Prototype safety-stock optimiser"),
    ("Ticket Classifier", "NLP", "S. Patel", "Support Manager", "Route top 5 ticket types automatically"),
    ("Document Search", "NLP", "M. Silva", "Legal Ops", "Evaluate retrieval on 200 labelled queries"),
    ("Sentiment Monitor", "NLP", "S. Patel", "Brand Lead", "Daily sentiment dashboard live"),
    ("Feature Store", "Platform", "R. Novak", "Head of Data", "Onboard 3 teams to shared features"),
    ("MLOps Pipeline", "Platform", "R. Novak", "Head of Data", "One-click model deploy to staging"),
    ("Data Quality Monitor", "Platform", "K. Haddad", "Data Governance", "Alerting on 20 critical tables"),
]
PEOPLE = {
    "Forecasting": ["Amira", "Ben", "Chloe", "Dev", "Eli"],
    "NLP": ["Farah", "Gus", "Hana", "Ivan"],
    "Platform": ["Jade", "Kofi", "Lena", "Max"],
}
TYPES = ["Story", "Experiment", "Data task", "Model deployment"]
STATUSES = ["Backlog", "Ready", "In Progress", "In Review", "Done"]
TITLES = {
    "Story": ["Expose predictions via API", "Add drill-down to dashboard", "Write model card", "Add monitoring alerts",
              "Build evaluation report", "Integrate with planner tool"],
    "Experiment": ["Test gradient boosting vs baseline", "Try transformer embeddings", "Evaluate new feature set",
                   "Compare hierarchical vs flat model", "Test synthetic data augmentation"],
    "Data task": ["Backfill 2 years of history", "Clean duplicate customer IDs", "Build training dataset v3",
                  "Label 500 samples", "Document source tables"],
    "Model deployment": ["Deploy model to staging", "Shadow-run in production", "Set up retraining schedule"],
}

HDR_FILL = PatternFill("solid", fgColor="1F4E78")
HDR_FONT = Font(bold=True, color="FFFFFF")


def write_sheet(wb, name, headers, rows, widths=None, table=True):
    ws = wb.create_sheet(name)
    ws.append(headers)
    for r in rows:
        ws.append(r)
    for c in ws[1]:
        c.fill, c.font = HDR_FILL, HDR_FONT
        c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    for i, h in enumerate(headers, 1):
        ws.column_dimensions[get_column_letter(i)].width = (widths or {}).get(h, max(12, len(h) + 4))
    if table and rows:
        ref = f"A1:{get_column_letter(len(headers))}{len(rows) + 1}"
        t = Table(displayName=name.replace(" ", ""), ref=ref)
        t.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
        ws.add_table(t)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            if isinstance(c.value, date):
                c.number_format = "yyyy-mm-dd"
    return ws


def sprint_of(d):
    for name, start in reversed(SPRINTS):
        if d >= start:
            return name
    return SPRINTS[0][0]


def build():
    wb = Workbook()
    wb.remove(wb.active)

    # ---- Projects -------------------------------------------------------
    write_sheet(wb, "Projects",
                ["Project", "Cluster", "Product Owner", "Stakeholder", "Sprint Goal"],
                [list(p) for p in PROJECTS],
                {"Project": 24, "Product Owner": 16, "Stakeholder": 22, "Sprint Goal": 44})

    # ---- Backlog --------------------------------------------------------
    backlog, n = [], 1
    for proj, cluster, *_ in PROJECTS:
        team = PEOPLE[cluster]
        for _ in range(random.randint(9, 13)):
            typ = random.choices(TYPES, weights=[45, 25, 20, 10])[0]
            sprint = random.choices([CURRENT, NEXT, ""], weights=[55, 25, 20])[0]
            if sprint == CURRENT:
                status = random.choices(STATUSES[1:], weights=[5, 18, 12, 65])[0]
            elif sprint == NEXT:
                status = random.choice(["Backlog", "Ready", "Ready"])
            else:
                status = "Backlog"
            created = TODAY - timedelta(days=random.randint(10, 60))
            start = None
            if status in ("In Progress", "In Review", "Done"):
                start = max(created, SPRINTS[4][1]) + timedelta(days=random.randint(0, 6))
            done = start + timedelta(days=random.randint(1, 6)) if status == "Done" else None
            if done and done > TODAY:
                done = TODAY
            if done:
                last = done
            elif start:  # most active work was touched recently; ~15% goes stale
                last = TODAY - timedelta(days=random.randint(5, 8) if random.random() < 0.15 else random.randint(0, 2))
                last = max(last, start)
            else:
                last = created
            if last > TODAY:
                last = TODAY
            est = random.choice([1, 2, 3, 5, 8]) if typ != "Experiment" else None
            timebox = random.choice([3, 5]) if typ == "Experiment" else None
            # deliberately leave some gaps so the hygiene script has something to find
            if random.random() < 0.12 and typ != "Experiment":
                est = None
            ac = "Given/When/Then defined" if random.random() > 0.15 else ""
            owner = random.choice(team) if (status != "Backlog" or random.random() > 0.3) else ""
            blocked = "Y" if status == "In Progress" and random.random() < 0.18 else "N"
            note = random.choice(["Waiting on data access", "Upstream schema change", "Need SME labels",
                                  "Compute quota exceeded"]) if blocked == "Y" else ""
            hyp = outcome = ""
            if typ == "Experiment":
                hyp = "If we " + random.choice(["add lag features", "use pretrained embeddings", "pool across regions",
                                                "rebalance classes"]) + " then accuracy improves by 3pts"
                if random.random() < 0.15:
                    hyp = ""
                if status == "Done":
                    outcome = random.choices(["Go", "Pivot", "Kill"], weights=[50, 30, 20])[0]
            title = random.choice(TITLES[typ])
            backlog.append([f"DS-{n:03d}", proj, cluster, typ, title, status, owner, sprint, est, timebox, ac,
                            blocked, note, hyp, outcome, created, start, done, last])
            n += 1
    ws = write_sheet(wb, "Backlog",
                     ["ID", "Project", "Cluster", "Type", "Title", "Status", "Owner", "Sprint", "Estimate (pts)",
                      "Timebox (days)", "Acceptance Criteria", "Blocked", "Blocker Note", "Hypothesis", "Outcome",
                      "Created", "Started", "Done Date", "Last Updated"],
                     backlog,
                     {"Project": 22, "Title": 34, "Acceptance Criteria": 24, "Blocker Note": 24, "Hypothesis": 48,
                      "Type": 16, "Status": 13})
    last_row = len(backlog) + 1
    for col, opts in (("D", TYPES), ("F", STATUSES), ("L", ["Y", "N"]), ("O", ["Go", "Pivot", "Kill"])):
        dv = DataValidation(type="list", formula1='"' + ",".join(opts) + '"', allow_blank=True)
        dv.add(f"{col}2:{col}{last_row}")
        ws.add_data_validation(dv)
    ws.conditional_formatting.add(f"L2:L{last_row}",
                                  CellIsRule(operator="equal", formula=['"Y"'], fill=PatternFill("solid", fgColor="F8CBAD")))

    # ---- Standup Log (this week) ----------------------------------------
    standups = []
    week = [TODAY - timedelta(days=i) for i in range(4, -1, -1)]
    for d in week:
        for proj, cluster, *_ in PROJECTS:
            for person in random.sample(PEOPLE[cluster], 2):
                if random.random() < 0.1:
                    continue  # missed check-in
                b = "Y" if random.random() < 0.08 else "N"
                standups.append([d, person, proj, random.choice(["Finished feature engineering", "Reviewed PR",
                                 "Ran baseline", "Paired on pipeline", "Labelled data"]),
                                 random.choice(["Tune hyperparameters", "Write tests", "Prepare demo",
                                                "Fix data join", "Draft model card"]),
                                 b, "Waiting on access" if b == "Y" else ""])
    write_sheet(wb, "Standup Log", ["Date", "Person", "Project", "Yesterday", "Today", "Blocked", "Blocker Note"],
                standups, {"Project": 22, "Yesterday": 30, "Today": 30, "Blocker Note": 22})

    # ---- Impediments -----------------------------------------------------
    imps = []
    for i, row in enumerate([r for r in backlog if r[11] == "Y"], 1):
        raised = TODAY - timedelta(days=random.randint(0, 5))
        resolved = random.random() < 0.3
        imps.append([f"IMP-{i:02d}", row[1], row[0], raised, row[6] or "PM", row[12],
                     "Resolved" if resolved else "Open", raised + timedelta(days=1) if resolved else None,
                     "Y" if (not resolved and (TODAY - raised).days >= 2) else "N"])
    write_sheet(wb, "Impediments", ["ID", "Project", "Backlog ID", "Raised", "Owner", "Description", "Status",
                                    "Resolved", "Escalated"], imps, {"Project": 22, "Description": 30})

    # ---- Risks & Dependencies -------------------------------------------
    risks = [
        ["R-01", "Demand Forecast", "Dependency", "Needs Feature Store promo features", "Owned", "R. Novak", "Feature Store"],
        ["R-02", "Churn Model", "Risk", "Q3 data late from CRM migration", "Mitigated", "L. Chen", ""],
        ["R-03", "Ticket Classifier", "Dependency", "Deploy path depends on MLOps Pipeline", "Owned", "S. Patel", "MLOps Pipeline"],
        ["R-04", "Document Search", "Risk", "Legal may block use of external embeddings", "Accepted", "M. Silva", ""],
        ["R-05", "Data Quality Monitor", "Risk", "Alert fatigue if thresholds too tight", "Resolved", "K. Haddad", ""],
        ["R-06", "Inventory Optimisation", "Dependency", "Uses Demand Forecast outputs", "Owned", "A. Rahman", "Demand Forecast"],
        ["R-07", "Sentiment Monitor", "Risk", "Social API pricing change", "Owned", "S. Patel", ""],
    ]
    write_sheet(wb, "Risks", ["ID", "Project", "Type", "Description", "ROAM", "Owner", "Depends On"], risks,
                {"Project": 22, "Description": 42, "Depends On": 20})

    # ---- Sprint Snapshots (history for S1-S4) ---------------------------
    snaps = []
    for proj, *_ in PROJECTS:
        base = random.randint(14, 30)
        for s, start in SPRINTS[:4]:
            committed = base + random.randint(-4, 4)
            completed = max(0, committed - random.randint(0, 9))
            snaps.append([s, start, proj, committed, completed, committed - completed,
                          "Y" if completed / committed >= 0.8 else "N"])
    write_sheet(wb, "Sprint Snapshots", ["Sprint", "Sprint Start", "Project", "Committed (pts)", "Completed (pts)",
                                         "Carried Over (pts)", "Goal Met"], snaps, {"Project": 22})

    # ---- Calendar --------------------------------------------------------
    cal = []
    for s, start in SPRINTS:
        cal.append([s, start, start + timedelta(days=SPRINT_LEN - 3), start + timedelta(days=SPRINT_LEN - 5),
                    start + timedelta(days=SPRINT_LEN)])
    write_sheet(wb, "Calendar", ["Sprint", "Sprint Day (start)", "Last working day", "Retro survey sent",
                                 "Next Sprint Day"], cal, {"Sprint Day (start)": 18, "Last working day": 18,
                                                          "Retro survey sent": 18, "Next Sprint Day": 18})

    # ---- Dashboard (live formulas) --------------------------------------
    ws = wb.create_sheet("Dashboard", 0)
    ws["A1"] = f"Portfolio dashboard, current sprint {CURRENT}"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = "Formulas read the Backlog and Impediments sheets. Refresh after each export."
    ws["A2"].font = Font(italic=True, color="666666")
    hdr = ["Project", "Cluster", "Committed pts", "Done pts", "% Done", "Blocked items", "Open impediments",
           "Experiments closed", "RAG"]
    ws.append([])
    ws.append(hdr)
    for c in ws[4]:
        c.fill, c.font = HDR_FILL, HDR_FONT
    for i, (proj, cluster, *_) in enumerate(PROJECTS, start=5):
        ws.append([
            proj, cluster,
            f'=SUMIFS(Backlog!I:I,Backlog!B:B,A{i},Backlog!H:H,"{CURRENT}")',
            f'=SUMIFS(Backlog!I:I,Backlog!B:B,A{i},Backlog!H:H,"{CURRENT}",Backlog!F:F,"Done")',
            f'=IF(C{i}=0,0,D{i}/C{i})',
            f'=COUNTIFS(Backlog!B:B,A{i},Backlog!L:L,"Y")',
            f'=COUNTIFS(Impediments!B:B,A{i},Impediments!G:G,"Open")',
            f'=COUNTIFS(Backlog!B:B,A{i},Backlog!D:D,"Experiment",Backlog!F:F,"Done")',
            f'=IF(OR(G{i}>=2,E{i}<0.5),"Red",IF(OR(G{i}=1,E{i}<0.75),"Amber","Green"))',
        ])
        ws[f"E{i}"].number_format = "0%"
    end = 4 + len(PROJECTS)
    for txt, color in (("Red", "F8CBAD"), ("Amber", "FFE699"), ("Green", "C6EFCE")):
        ws.conditional_formatting.add(f"I5:I{end}", CellIsRule(operator="equal", formula=[f'"{txt}"'],
                                                               fill=PatternFill("solid", fgColor=color)))
    for col, w in zip("ABCDEFGHI", [24, 14, 15, 11, 9, 14, 17, 18, 9]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A5"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"Wrote {OUT} ({len(backlog)} backlog items, {len(standups)} standups, {len(imps)} impediments)")


if __name__ == "__main__":
    build()
