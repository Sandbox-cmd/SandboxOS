"""Sprint and portfolio metrics. Writes a workbook that Power BI or the Excel
dashboard can read, one row per project.

Metrics: committed/done points this sprint, average velocity (last 3
sprints), say/do ratio, carry-over rate, median cycle time, experiment win
rate, open impediments, overdue blockers, and a RAG status.

Usage:  python metrics.py [--book export.xlsx] [--sprint S5]
Output: output/metrics.xlsx
"""
import pandas as pd

from common import load, parse_args


def compute(data, sprint, today):
    b, snaps, imp = data["Backlog"], data["Sprint Snapshots"], data["Impediments"]
    cur = b[b["Sprint"] == sprint]
    rows = []
    for _, p in data["Projects"].iterrows():
        name = p["Project"]
        c = cur[cur["Project"] == name]
        committed = c["Estimate (pts)"].sum()
        done = c.loc[c["Status"] == "Done", "Estimate (pts)"].sum()
        hist = snaps[snaps["Project"] == name].sort_values("Sprint Start").tail(3)
        velocity = hist["Completed (pts)"].mean()
        say_do = hist["Completed (pts)"].sum() / max(hist["Committed (pts)"].sum(), 1)
        carry = hist["Carried Over (pts)"].sum() / max(hist["Committed (pts)"].sum(), 1)
        finished = b[(b["Project"] == name) & b["Done Date"].notna() & b["Started"].notna()]
        cycle = (finished["Done Date"] - finished["Started"]).dt.days.median()
        exps = b[(b["Project"] == name) & (b["Type"] == "Experiment") & b["Outcome"].notna()]
        win = (exps["Outcome"] == "Go").mean() if len(exps) else None
        open_imp = imp[(imp["Project"] == name) & (imp["Status"] == "Open")]
        overdue = open_imp[(today - open_imp["Raised"]).dt.days >= 2]
        pct = done / committed if committed else 0
        rag = "Red" if len(overdue) >= 2 or pct < 0.4 else "Amber" if len(open_imp) or pct < 0.65 or say_do < 0.75 else "Green"
        rows.append({
            "Project": name, "Cluster": p["Cluster"], "Sprint Goal": p["Sprint Goal"],
            "Committed pts": committed, "Done pts": done, "% Done": round(pct, 2),
            "Items in sprint": len(c), "Items done": int((c["Status"] == "Done").sum()),
            "Avg velocity (3 sprints)": round(velocity, 1), "Say/Do ratio": round(say_do, 2),
            "Carry-over rate": round(carry, 2), "Median cycle time (days)": cycle,
            "Experiments closed": len(exps), "Experiment win rate": None if win is None else round(win, 2),
            "Open impediments": len(open_imp), "Blockers 48h+": len(overdue), "RAG": rag,
        })
    return pd.DataFrame(rows)


def main():
    a = parse_args(__doc__)
    data = load(a.book)
    m = compute(data, a.sprint, a.today)
    cluster = m.groupby("Cluster").agg({"Committed pts": "sum", "Done pts": "sum", "Open impediments": "sum",
                                        "Say/Do ratio": "mean"}).round(2).reset_index()
    out = a.out / "metrics.xlsx"
    with pd.ExcelWriter(out) as w:
        m.to_excel(w, sheet_name="Projects", index=False)
        cluster.to_excel(w, sheet_name="Clusters", index=False)
        data["Risks"][data["Risks"]["ROAM"] != "Resolved"].to_excel(w, sheet_name="Open risks", index=False)
    cols = ["Project", "% Done", "Say/Do ratio", "Median cycle time (days)", "Open impediments", "RAG"]
    print(m[cols].to_string(index=False))
    print(f"\nRAG: {m['RAG'].value_counts().to_dict()}\nWrote {out}")


if __name__ == "__main__":
    main()
