"""Pure helper libraries for the discovery / editorial pipeline.

Modules here MUST be free of HTTP / Notion writes / external side effects
unless their docstring says otherwise. They are imported by Stage 7+
scripts and by Hilo 6's Stage 10 publisher. Pure Python helpers — no I/O
outside SQLite — shared across stages.
"""
