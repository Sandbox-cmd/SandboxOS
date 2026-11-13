# Scrum automation for a data science portfolio

A working system for running about 10 agile data science projects with Microsoft 365 and VS Code, without 10 sets of ceremonies a day. Read `playbook.docx` first.

## What's here

- `playbook.docx`: operating model, meeting design, agendas, Power Automate flow specs, metrics, 90-day rollout and interview talking points.
- `backlog_template.xlsx`: the data model (Backlog, Standup Log, Impediments, Risks, Sprint Snapshots, Calendar, Projects) with sample data for 10 projects and a live-formula Dashboard sheet. Mirror these columns in Microsoft Lists or Azure DevOps.
- `flows/standup_card.json`: the Teams adaptive card for the async daily check-in. Paste it into Power Automate's "Post adaptive card and wait for a response" action.
- `scripts/`: Python tools you run from VS Code.
- `pitch/`: one-page wireframe explainer for pitching the system to a manager. `system_explainer.png` (image), `.pdf` (print), `.pptx` (one slide with a 60-second script in the speaker notes) and `.html` (editable source).

## Scripts

```bash
pip install pandas openpyxl python-docx python-pptx
```

```bash
python scripts/backlog_hygiene.py --sprint S5
```

```bash
python scripts/metrics.py --sprint S5
```

```bash
python scripts/sprint_report.py --sprint S5
```

Each takes `--book <export.xlsx>` (defaults to the sample template), `--today now` to evaluate against today's date, and `--out <folder>` (defaults to `output/`).

| Script | Output |
|---|---|
| `backlog_hygiene.py` | `hygiene_report.md/.xlsx`: missing estimates, acceptance criteria, hypotheses, stale work, old blockers, missed check-ins, grouped by owner |
| `metrics.py` | `metrics.xlsx`: per-project % done, velocity, say/do, carry-over, cycle time, experiment win rate, RAG |
| `sprint_report.py` | `sprint_review_<cluster>.pptx` per cluster and `portfolio_summary.docx` |
| `build_template.py` | regenerates the sample workbook |
| `build_playbook.py` | regenerates the playbook |
