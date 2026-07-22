# growing a skill — procedures earn their file by recurring

a skill is a procedure that ran twice and will run again. not a narrative,
not what the model already knows.

the law here is eval-first: prove the task fails (or wobbles) WITHOUT the
skill, then write the minimum that passes. a skill nobody can fail is a
comment.

shape (`<name>/SKILL.md`):

    ---
    name: <lowercase-hyphen>
    description: <what it does + WHEN — include the exact words a person
      would say. pushy triggers work; workflow summaries backfire.>
    ---
    <under 500 lines. checklists for multi-step work. "only proceed when
    the validator passes." anything deterministic and fragile becomes a
    script in scripts/, run exactly, never retyped.>

when three sessions each rewrite the same helper — that helper is the
script this skill has been waiting for.
