"""The blog-writing agent: a LangGraph pipeline served over FastAPI.

See `docs/specs/0001-blog-writing-agent.md` and `GLOSSARY.md` for the domain
language: Run, Brief, Artifact, Researcher, Outline, Draft, Critique,
Verdict, Revision, Gate, Gate Decision, Checkpoint.
"""

from blog_agent import _ormsgpack_compat, _xxhash_compat

# Must run before anything imports LangGraph (see module docstrings).
_xxhash_compat.install()
_ormsgpack_compat.install()

