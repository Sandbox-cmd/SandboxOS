"""Sprint review pack. Builds one PowerPoint deck per cluster and a one-page
Word summary for the whole portfolio, from the backlog and metrics.

Send these to stakeholders the day before Sprint Day. The live review then
only covers demos and decisions.

Usage:  python sprint_report.py [--book export.xlsx] [--sprint S5]
Output: output/sprint_review_<cluster>.pptx, output/portfolio_summary.docx
"""
from docx import Document
from docx.shared import Pt, RGBColor
from pptx import Presentation
from pptx.dml.color import RGBColor as PRGB
from pptx.util import Inches
from pptx.util import Pt as PPt

from backlog_hygiene import check
from common import load, parse_args
from metrics import compute

RAG_RGB = {"Red": (0xC0, 0x39, 0x2B), "Amber": (0xD6, 0x8A, 0x00), "Green": (0x2E, 0x7D, 0x32)}
NAVY = PRGB(0x1F, 0x4E, 0x78)


def add_title(slide, text):
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.3), Inches(0.8))
    p = tb.text_frame.paragraphs[0]
    p.text, p.font.size, p.font.bold, p.font.color.rgb = text, PPt(28), True, NAVY


def add_bullets(slide, items, top=1.3, size=16):
    tb = slide.shapes.add_textbox(Inches(0.6), Inches(top), Inches(12.1), Inches(5.8))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, t in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text, p.font.size = t, PPt(size)
        p.space_after = PPt(6)


def add_table(slide, header, rows, top=1.3, col_widths=None):
    shape = slide.shapes.add_table(len(rows) + 1, len(header), Inches(0.5), Inches(top), Inches(12.3),
                                   Inches(0.4 * (len(rows) + 1)))
    t = shape.table
    for j, h in enumerate(header):
        t.cell(0, j).text = h
    for i, r in enumerate(rows, 1):
        for j, v in enumerate(r):
            t.cell(i, j).text = str(v)
    for i in range(len(rows) + 1):
        for j in range(len(header)):
            for p in t.cell(i, j).text_frame.paragraphs:
                p.font.size = PPt(12)
    if col_widths:
        for j, w in enumerate(col_widths):
            t.columns[j].width = Inches(w)
    return t


def cluster_deck(cluster, m, data, sprint, out):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    mc = m[m["Cluster"] == cluster]
    b = data["Backlog"]

    s = prs.slides.add_slide(blank)
    add_title(s, f"{cluster} cluster: sprint {sprint} review")
    add_bullets(s, [f"{len(mc)} projects, {int(mc['Done pts'].sum())} of {int(mc['Committed pts'].sum())} points done",
                    f"RAG: " + ", ".join(f"{k} {v}" for k, v in mc["RAG"].value_counts().items()),
                    f"{int(mc['Open impediments'].sum())} open impediments",
                    "Live session: demos and decisions only. Status is in this pack."], top=1.5, size=20)

    s = prs.slides.add_slide(blank)
    add_title(s, "Sprint goals and status")
    t = add_table(s, ["Project", "Sprint goal", "% done", "Say/Do", "RAG"],
                  [[r["Project"], r["Sprint Goal"], f"{r['% Done']:.0%}", r["Say/Do ratio"], r["RAG"]]
                   for _, r in mc.iterrows()], col_widths=[2.6, 6.2, 1.1, 1.1, 1.3])
    for i, (_, r) in enumerate(mc.iterrows(), 1):
        cell = t.cell(i, 4)
        cell.fill.solid()
        cell.fill.fore_color.rgb = PRGB(*RAG_RGB[r["RAG"]])
        cell.text_frame.paragraphs[0].font.color.rgb = PRGB(0xFF, 0xFF, 0xFF)

    exps = b[(b["Cluster"] == cluster) & (b["Type"] == "Experiment") & b["Outcome"].notna()]
    s = prs.slides.add_slide(blank)
    add_title(s, "What we learned (closed experiments)")
    if len(exps):
        add_table(s, ["Project", "Hypothesis", "Outcome"],
                  [[r["Project"], r["Hypothesis"] if isinstance(r["Hypothesis"], str) else "(missing)", r["Outcome"]]
                   for _, r in exps.head(10).iterrows()], col_widths=[2.6, 8.4, 1.3])
    else:
        add_bullets(s, ["No experiments closed this sprint."])

    projects = set(mc["Project"])
    imp = data["Impediments"]
    risks = data["Risks"]
    s = prs.slides.add_slide(blank)
    add_title(s, "Blockers, risks and decisions needed")
    items = [f"Blocker [{r['ID']}] {r['Project']}: {r['Description']}"
             for _, r in imp[(imp["Status"] == "Open") & imp["Project"].isin(projects)].iterrows()]
    items += [f"{r['Type']} [{r['ID']}] {r['Project']}: {r['Description']} ({r['ROAM']})"
              for _, r in risks[(risks["ROAM"] != "Resolved") & risks["Project"].isin(projects)].iterrows()]
    add_bullets(s, items or ["Nothing open."])

    nxt = b[(b["Cluster"] == cluster) & (b["Sprint"] != sprint) & (b["Sprint"] != "")]
    s = prs.slides.add_slide(blank)
    add_title(s, "Draft scope for next sprint (confirm at planning)")
    add_table(s, ["Project", "Ready items", "Points", "Experiments"],
              [[p, int((g["Status"] == "Ready").sum()), int(g["Estimate (pts)"].sum()),
                int((g["Type"] == "Experiment").sum())] for p, g in nxt.groupby("Project")],
              col_widths=[4, 2.8, 2.8, 2.7])

    path = out / f"sprint_review_{cluster.lower()}.pptx"
    prs.save(path)
    return path


def portfolio_doc(m, data, sprint, today, out):
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(10.5)
    doc.add_heading(f"Portfolio summary, sprint {sprint}", level=1)
    doc.add_paragraph(f"Generated {today:%d %b %Y}. {len(m)} projects. "
                      f"{int(m['Done pts'].sum())} of {int(m['Committed pts'].sum())} committed points done. "
                      f"RAG: " + ", ".join(f"{k} {v}" for k, v in m["RAG"].value_counts().items()) + ".")
    t = doc.add_table(rows=1, cols=6)
    t.style = "Light Grid Accent 1"
    for c, h in zip(t.rows[0].cells, ["Project", "Cluster", "% done", "Say/Do", "Blockers", "RAG"]):
        c.text = h
    for _, r in m.iterrows():
        cells = t.add_row().cells
        vals = [r["Project"], r["Cluster"], f"{r['% Done']:.0%}", f"{r['Say/Do ratio']:.2f}",
                str(r["Open impediments"]), r["RAG"]]
        for c, v in zip(cells, vals):
            c.text = v
        run = cells[5].paragraphs[0].runs[0]
        run.font.bold = True
        run.font.color.rgb = RGBColor(*RAG_RGB[r["RAG"]])
    doc.add_heading("Needs attention", level=2)
    reds = m[m["RAG"] != "Green"]
    for _, r in reds.iterrows():
        why = []
        if r["% Done"] < 0.65:
            why.append(f"{r['% Done']:.0%} of sprint done")
        if r["Open impediments"]:
            why.append(f"{r['Open impediments']} open blocker(s)")
        if r["Say/Do ratio"] < 0.75:
            why.append(f"say/do {r['Say/Do ratio']:.2f}")
        doc.add_paragraph(f"{r['Project']} ({r['RAG']}): " + ", ".join(why), style="List Bullet")
    doc.add_heading("Hygiene", level=2)
    h = check(data, sprint, today)
    doc.add_paragraph(f"{len(h)} backlog items need fixing before refinement. Owners have their list.")
    path = out / "portfolio_summary.docx"
    doc.save(path)
    return path


def main():
    a = parse_args(__doc__)
    data = load(a.book)
    m = compute(data, a.sprint, a.today)
    for cluster in m["Cluster"].unique():
        print("Wrote", cluster_deck(cluster, m, data, a.sprint, a.out))
    print("Wrote", portfolio_doc(m, data, a.sprint, a.today, a.out))


if __name__ == "__main__":
    main()
