"""kanban-tool: the mechanical half of the kanban plugin.

Claude decides which session belongs to which card and writes the card text.
Everything else (reading transcripts, merging fields, caches) is done here.
Standard library only. Works on Python 3.8 and later.
"""
__version__ = "0.1.0"
