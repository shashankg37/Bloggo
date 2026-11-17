# Gate routing keys off feedback presence

A Gate Decision payload has no dedicated routing field: `{"decision": "revise", "feedback": ...}` routes the Run back to the stage that produced the artifact, and empty feedback means approved (`{"decision": "approve"}` produces `outline_feedback: ""`, which is falsy). We chose this over an explicit routing key in the payload because the API already validates the decision shape (a `Literal` type plus a validator that revise requires feedback), so the redundancy would invite inconsistency — a payload could claim "approve" while carrying feedback, and the two sources would have to be reconciled. Presence-based routing also keeps the state machine's conditional edge reading directly off persisted state (`state["outline_feedback"]`), which is what survives the Checkpoint and what the status endpoint derives from.

**Considered options:** an explicit `route`/`next_stage` field in the Gate Decision payload — rejected because the payload is written by the API layer from a validated request, not by the client, so it can never disagree with the decision itself; keeping both a decision string and a routing flag would just be two ways to say one thing.

**Consequences:** the `interrupt` node returns `{"outline_feedback": ""}` on approval rather than returning nothing — an empty-string sentinel in state that a reader must know means "approved", not "no gate happened". Adding a second Gate (Gate 2, ticket 06) means either a parallel `*_feedback` key or a generalized routing rule; if a third mechanism ever appears, revisit this decision rather than overloading feedback again.

**Status:** accepted
