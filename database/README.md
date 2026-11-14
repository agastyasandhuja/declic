# Database ownership

Domain drafts:

- domains/identity and domains/entertainment — Adi.
- domains/academics — Amogh.
- domains/learning — Agastya.

Agastya assembles ordered migrations in migrations and records inter-domain
dependencies. Use additive domain files rather than editing one shared schema.
The schema is proposed; no database resources or executable migrations exist yet.

All exposed private data tables need row-level policies matching ownership.
Answer keys and credentials must not be exposed through the client-facing Data API.
Server-level privileged access still requires user authorization.
Only synthetic seed data belongs in seeds; no real Canvas exports.
