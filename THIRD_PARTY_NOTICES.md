# Third-Party Notices

This file lists every element of this repository that was adapted, in any form, from
material outside our own original work. Full reasoning and classification for each
item lives in `integration_lab/audit/reference_reuse_plan.md`. Nothing below is
substantial verbatim code; each item is either a small teaching-sample idiom explicitly
marked reusable by its source, or a narrow interoperability convention.

1. **Commit-reveal hash shape** (`state|move|intent|nonce` -> SHA-256 over canonical
   JSON): adapted from `assignment_materials/police_thief_p2p.pdf`, Ch.5.3.2 (printed
   p.37) — the course's own generic teaching sample, explicitly marked reusable. Not
   derived from the reference repository's source code.
2. **Token-bucket rate limiter algorithm**: adapted from the same book, Ch.9.3.2
   (printed p.77), a generic teaching sample.
3. **Gmail OAuth send-only flow**: adapted from the same book, Appendix A (printed
   pp.107-108), a generic teaching sample. Scope hardcoded to `gmail.send` only.
4. **`game_id`/`game_uid` deterministic derivation scheme** (sorted group-id pairing +
   UUID from SHA-256 of canonical terms): studied from
   `reference_only/src/police_thief/domain/game_ids.py` (Dr. Yoram Segal / GTAI,
   Educational Use EULA) for cross-group wire compatibility; reimplemented
   independently in our own code.
5. **FastMCP tool-name convention** (`negotiate`/`receive_turn`/`submit_audit`/
   `receive_control`) and per-message-type inbox pattern: studied from
   `reference_only/src/police_thief/infra/mcp_server.py` and `domain/protocol.py`
   (same EULA) for cross-group wire compatibility; reimplemented independently.
6. **Gmail OAuth credential load/refresh bootstrap pattern**: adapted from
   `assignment_materials/main-google-api-installtion-guid.pdf` (Dr. Segal, May 2026),
   a general teaching sample. Its demo scopes (`gmail.modify` + `calendar`) were **not**
   reused — this project's scope is `gmail.send` only, per Appendix A of the primary
   rule book.

Nothing else in this repository is derived from outside sources as of this scaffold.
This file will be updated as implementation proceeds, before any public release.
