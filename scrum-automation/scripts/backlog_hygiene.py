"""Backlog hygiene check. Run before refinement so the live slot is spent on
real questions instead of chasing missing fields.

Flags: missing estimate, missing acceptance criteria, no owner on committed
work, experiments without hypothesis or timebox, closed experiments with no
outcome, stale in-progress items (5+ days without update), blockers older
than 48 hours, and standup no-shows.

Usage:  python backlog_hygiene.py [--book export.xlsx] [--sprint S5]
Output: output/hygiene_report.md and output/hygiene_report.xlsx
"""
import pandas as pd

from common import load, parse_args

STALE_DAYS = 5
BLOCKER_HOURS = 48


def check(data, sprint, today):
    b = data["Backlog"]
    upcoming = b[b["Sprint"] != ""]  # committed to current or next sprint
    nonexp = upcoming["Type"] != "Experiment"
    exp = upcoming["Type"] == "Experiment"
    rules = [
        ("Missing estimate", nonexp & upcoming["Estimate (pts)"].isna()),
        ("Missing acceptance criteria", nonexp & upcoming["Acceptance Criteria"].isna()),
        ("No owner on committed work", upcoming["Sprint"].eq(sprint) & upcoming["Owner"].isna()),
        ("Experiment without hypothesis", exp & upcoming["Hypothesis"].isna()),
        ("Experiment without timebox", exp & upcoming["Timebox (days)"].isna()),
        ("Closed experiment, no Go/Pivot/Kill outcome", exp & upcoming["Status"].eq("Done") & upcoming["Outcome"].isna()),
        (f"Stale: in progress, no update for {STALE_DAYS}+ days",
         upcoming["Status"].isin(["In Progress", "In Review"]) & ((today - upcoming["Last Updated"]).dt.days >= STALE_DAYS)),
    ]
    issues = []
    for name, mask in rules:
        for _, r in upcoming[mask].iterrows():
            issues.append({"Issue": name, "ID": r["ID"], "Project": r["Project"], "Title": r["Title"],
                           "Owner": r["Owner"] if pd.notna(r["Owner"]) else "(none)", "Sprint": r["Sprint"]})

    imp = data["Impediments"]
    old = imp[(imp["Status"] == "Open") & ((today - imp["Raised"]).dt.total_seconds() / 3600 >= BLOCKER_HOURS)]
    for _, r in old.iterrows():
        issues.append({"Issue": f"Blocker open {BLOCKER_HOURS}h+ (take to Scrum of Scrums)", "ID": r["ID"],
                       "Project": r["Project"], "Title": r["Description"], "Owner": r["Owner"], "Sprint": sprint})

    s = data["Standup Log"]
    week = s[s["Date"] > today - pd.Timedelta(days=7)]
    days = week["Date"].nunique()
    counts = week.groupby("Person").size()
    for person, n in counts[counts < days - 1].items():
        issues.append({"Issue": "Missed 2+ async standups this week", "ID": "-", "Project": "-",
                       "Title": f"{n} of {days} check-ins", "Owner": person, "Sprint": sprint})
    return pd.DataFrame(issues)


def main():
    a = parse_args(__doc__)
    issues = check(load(a.book), a.sprint, a.today)
    xlsx, md = a.out / "hygiene_report.xlsx", a.out / "hygiene_report.md"
    issues.to_excel(xlsx, index=False)

    lines = [f"# Backlog hygiene report ({a.today:%Y-%m-%d}, sprint {a.sprint})", "",
             f"{len(issues)} items need attention before refinement.", "", "## Summary by issue", ""]
    if issues.empty:
        lines.append("Nothing to fix.")
    else:
        for name, n in issues["Issue"].value_counts().items():
            lines.append(f"- {name}: {n}")
        lines += ["", "## By owner (send each person their list)", ""]
        for owner, g in issues.groupby("Owner"):
            lines.append(f"### {owner}")
            for _, r in g.iterrows():
                lines.append(f"- [{r['ID']}] {r['Project']}: {r['Title']} ({r['Issue']})")
            lines.append("")
    md.write_text("\n".join(lines))
    print("\n".join(lines[:4 + issues["Issue"].nunique() + 2] if not issues.empty else lines))
    print(f"Wrote {md} and {xlsx}")


if __name__ == "__main__":
    main()
