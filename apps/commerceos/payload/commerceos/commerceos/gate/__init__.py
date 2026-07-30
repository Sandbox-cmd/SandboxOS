"""the gate + the record — one wall, one memory (spec/parts/gate-and-record.md).

gate.submit() decides now-or-parked; the ledger remembers every action and
its outcome; a one-use handle is the only key that writes the world; the
policy table (per store, stores/<store>/policy-table.json) is the config.

sole writer of the "ledger" table-set: ledger, handles, events.
no approve verb on any agent-facing surface — gate.resolve() belongs to
the web surface (part 7) alone.
"""
