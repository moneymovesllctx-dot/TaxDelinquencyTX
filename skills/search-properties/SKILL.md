---
description: Search Texas tax delinquent properties. Use when the user asks to find, look up, or filter delinquent tax properties in any Texas county. Handles queries like "find commercial properties in Bexar County owing more than $10K in litigation", "show me delinquent properties owned by [name]", "what properties are in Bexar county with no payment plan", or any property lookup by county, owner, SPTB code, amount, or status flags.
---

# Tax Delinquency Property Search

You have access to a live database of Texas tax delinquent properties across 11 counties via the `tax-delinquency` MCP tools.

## Available tools

- **search_properties** — Main search. Filter by county, owner name, min/max amount due, SPTB code, litigation, payment plan, bankruptcy, absentee owner. Returns all raw fields per property.
- **list_counties** — Lists all counties and their available filter fields.
- **get_county_summary** — Total records, amount due, and litigation counts for a county.
- **get_property** — Fetch a single property by county + account number.

## SPTB codes (Texas CAD standard)

| Category | Codes |
|----------|-------|
| Residential | A, A1, A2 |
| Multifamily | B |
| Commercial | F1 |
| Industrial | F2 |
| Vacant land | C1, C2 |
| Agricultural | D1, D2 |
| Commercial personal | L1 |
| Industrial personal | L2 |
| Oil & gas | G1, G2, G3 |
| Mobile home | M1 |

## Notes

- **Zip/city/state** come from mailing address fields, not property address (property address is street only for most counties).
- **Brazoria county** uses `amount_due` instead of `total_due` and `owner_name_1` instead of `owner_name` — normalized aliases are included in every result.
- **Dallas and Harris** don't have SPTB codes in the data.
- Results default to 50 per page; use `limit` and `offset` to paginate.
- Always show the `county` field so users know which dataset each result came from.

## Disclaimer

Data is sourced from official county public records. Update frequency varies by county. Always verify current status directly with the relevant county tax office before making any legal or financial decision.
