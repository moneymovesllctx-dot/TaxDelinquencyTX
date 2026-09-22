# Tax Delinquency Plugin for Claude Code

Search Texas tax delinquent properties across **11 counties** with 250,000+ records updated weekly.

## Counties covered

Bexar · Collin · Comal · Dallas · Denton · Ector · Harris · Nueces · Tarrant · Travis · Brazoria

## What you can ask

- "Find commercial properties in Bexar County owing more than $10K that are in litigation with no payment plan"
- "Show me all delinquent properties owned by [name]"
- "What's the total delinquency in Tarrant County?"
- "Find multifamily properties in Harris County with absentee owners"
- "Look up property account number 12345 in Dallas County"

## How it works

This plugin connects Claude to a live MCP server backed by Supabase. It exposes four tools:

| Tool | Description |
|------|-------------|
| `search_properties` | Filter by county, owner, amount, SPTB code, litigation, payment plan, etc. |
| `list_counties` | See all available counties and their supported filter fields |
| `get_county_summary` | County-level totals: records, total owed, litigation count |
| `get_property` | Look up a specific property by account number |

## Installation

```sh
/plugin install tax-delinquency@claude-community
```

## Data

Data is sourced from official county tax assessor-collector public records under the Texas Public Information Act. Update frequency varies by county.

## Disclaimer

This plugin provides access to **public record** data obtained from Texas county tax assessor-collector offices. By using this plugin, you agree to the following:

- **No warranty on accuracy.** Data update frequency varies by county and records may not reflect real-time payment status, ownership changes, or other modifications. Always verify data directly with the relevant county tax office before making any legal, financial, or investment decision.
- **Not legal or financial advice.** Results from this plugin do not constitute legal or financial advice. Consult a licensed attorney or financial advisor before acting on any information returned.
- **Responsible use required.** This data may not be used to harass, intimidate, or unlawfully contact property owners. Any outreach to property owners using mailing address data must comply with applicable federal and state law, including the Telephone Consumer Protection Act (TCPA), the CAN-SPAM Act, and Texas Business & Commerce Code Chapter 302.
- **No guarantee of completeness.** Not all Texas counties are represented, and data coverage varies by county. Absence of a property from results does not confirm the absence of a tax delinquency.

Money Moves LLC makes no representations regarding the fitness of this data for any particular purpose and is not liable for any decisions made based on information returned by this plugin.

## Author

TaxDelinquency.com · info@taxdelinquency.com
