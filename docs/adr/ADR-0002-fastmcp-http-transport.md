# ADR-0002: Fastmcp Http Transport

## Status

Accepted

## Context

The book mandates real peer-to-peer FastMCP over HTTP (Ch.2), not an in-process mock, so that two independent processes on two machines can actually interoperate.

## Decision

Use `fastmcp`'s HTTP transport (`mcp.run(transport="http", ...)`) in production code; mocks/fakes are permitted only inside `tests/`.

## Consequences

Requires a real network round-trip for every integration test — slower than an in-process mock, but the only way to prove real interoperability.
