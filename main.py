import httpx

from collections import defaultdict
from datetime import date
import threading

# ── IP rate limiter (100 req/day per IP, resets midnight UTC) ─────────────────
RATE_LIMIT = 100
_rate_lock = threading.Lock()
_ip_counts = defaultdict(lambda: {"date": None, "count": 0})

def check_rate_limit(ip: str) -> bool:
    today = date.today().isoformat()
    with _rate_lock:
        entry = _ip_counts[ip]
        if entry["date"] != today:
            entry["date"] = today
            entry["count"] = 0
        if entry["count"] >= RATE_LIMIT:
            return False
        entry["count"] += 1
        return True

"""
Tax Delinquency MCP Server
"""
import os, json
from typing import Optional, List, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import create_client, Client
BEEHIIV_API_KEY = os.environ.get("BEEHIIV_API_KEY")
BEEHIIV_PUB_ID  = "pub_5b1e1a71-df45-488b-88f6-fd8373aa2bb4"

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Tax Delinquency MCP", description="Search tax delinquent properties across Texas counties.", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

COUNTIES = {
    "bexar":    {"table": "bexar_county",    "acct": "account_number", "owner": "owner_name",   "due": "total_due",  "sptb": "sptb_code",  "litigation": "in_litigation", "payment_plan": "in_payment_agreement", "bankruptcy": "in_bankruptcy", "absentee": "is_absentee_owner", "years": "num_delinquent_years"},
    "collin":   {"table": "collin_county",   "acct": "account_number", "owner": "owner_name",   "due": "total_due",  "sptb": "sptb_code",  "litigation": "in_litigation", "payment_plan": "in_payment_agreement", "bankruptcy": None,            "absentee": None,                "years": None},
    "comal":    {"table": "comal_county",    "acct": "account_number", "owner": "owner_name",   "due": "total_due",  "sptb": "sptb_code",  "litigation": "in_litigation", "payment_plan": "in_payment_agreement", "bankruptcy": None,            "absentee": None,                "years": None},
    "dallas":   {"table": "dallas_county",   "acct": "account",        "owner": "owner_name",   "due": "total_due",  "sptb": None,         "litigation": "in_litigation", "payment_plan": None,                   "bankruptcy": None,            "absentee": None,                "years": None},
    "denton":   {"table": "denton_county",   "acct": "account_number", "owner": "owner_name",   "due": "total_due",  "sptb": "sptb_code",  "litigation": "in_litigation", "payment_plan": "in_payment_agreement", "bankruptcy": None,            "absentee": None,                "years": None},
    "ector":    {"table": "ector_county",    "acct": "account_num",    "owner": "owner_name",   "due": "total_due",  "sptb": "sptb_code",  "litigation": "in_litigation", "payment_plan": None,                   "bankruptcy": None,            "absentee": None,                "years": None},
    "harris":   {"table": "harris_county",   "acct": "account_number", "owner": "owner_name",   "due": "total_due",  "sptb": None,         "litigation": "in_litigation", "payment_plan": "in_payment_agreement", "bankruptcy": None,            "absentee": None,                "years": None},
    "nueces":   {"table": "nueces_county",   "acct": "account_num",    "owner": "owner_name",   "due": "total_due",  "sptb": "sptb_code",  "litigation": "in_litigation", "payment_plan": None,                   "bankruptcy": None,            "absentee": None,                "years": None},
    "tarrant":  {"table": "tarrant_county",  "acct": "account_number", "owner": "owner_name",   "due": "total_due",  "sptb": "sptb_code",  "litigation": "in_litigation", "payment_plan": "in_payment_agreement", "bankruptcy": None,            "absentee": None,                "years": None},
    "travis":   {"table": "travis_county",   "acct": "account_number", "owner": "owner_name",   "due": "total_due",  "sptb": "sptb_code",  "litigation": "in_suit",       "payment_plan": "in_payment_agreement", "bankruptcy": None,            "absentee": None,                "years": None},
    "brazoria": {"table": "brazoria_county", "acct": "account_number", "owner": "owner_name_1", "due": "amount_due", "sptb": None,         "litigation": "in_litigation", "payment_plan": None,                   "bankruptcy": None,            "absentee": None,                "years": None},
}

SPTB_MAP = {
    "residential": ["A","A1","A2"], "multifamily": ["B"], "vacant_land": ["C1","C2"],
    "agricultural": ["D1","D2"], "rural": ["E"], "commercial": ["F1"], "industrial": ["F2"],
    "oil_gas": ["G1","G2","G3"], "utilities": ["J"], "commercial_personal": ["L1"],
    "industrial_personal": ["L2"], "mobile_home": ["M1"], "exempt": ["X"],
}

def normalize_row(row: dict, schema: dict, county: str) -> dict:
    out = dict(row)
    out["county"] = county
    out["account_number"] = row.get(schema["acct"])
    out["owner_name"] = row.get(schema["owner"])
    out["amount_due"] = row.get(schema["due"])
    out["sptb_code"] = row.get(schema["sptb"]) if schema["sptb"] else row.get("sptb_code")
    out["in_litigation"] = row.get(schema["litigation"]) if schema["litigation"] else None
    out["in_payment_agreement"] = row.get(schema["payment_plan"]) if schema["payment_plan"] else None
    out["in_bankruptcy"] = row.get(schema["bankruptcy"]) if schema["bankruptcy"] else None
    out["is_absentee_owner"] = row.get(schema["absentee"]) if schema["absentee"] else None
    out["num_delinquent_years"] = row.get(schema["years"]) if schema["years"] else None
    return out

def search_county(county, schema, property_types, min_amount_due, max_amount_due,
                  in_litigation, in_payment_agreement, in_bankruptcy, is_absentee_owner,
                  zip_code, city, owner_name, limit, offset):
    q = supabase.table(schema["table"]).select("*")
    if min_amount_due is not None: q = q.gte(schema["due"], min_amount_due)
    if max_amount_due is not None: q = q.lte(schema["due"], max_amount_due)
    if property_types and schema["sptb"]:
        codes = []
        for pt in property_types:
            codes.extend(SPTB_MAP.get(pt.lower().replace(" ","_"), [pt.upper()]))
        if codes: q = q.in_(schema["sptb"], codes)
    if in_litigation is not None and schema["litigation"]: q = q.eq(schema["litigation"], in_litigation)
    if in_payment_agreement is not None and schema["payment_plan"]: q = q.eq(schema["payment_plan"], in_payment_agreement)
    if in_bankruptcy is not None and schema["bankruptcy"]: q = q.eq(schema["bankruptcy"], in_bankruptcy)
    if is_absentee_owner is not None and schema["absentee"]: q = q.eq(schema["absentee"], is_absentee_owner)
    if zip_code: q = q.eq("mailing_zip", zip_code)
    if city: q = q.ilike("mailing_city", f"%{city}%")
    if owner_name: q = q.ilike(schema["owner"], f"%{owner_name}%")
    q = q.order(schema["due"], desc=True).range(offset, offset + limit - 1)
    result = q.execute()
    return [normalize_row(r, schema, county) for r in (result.data or [])]

class SearchRequest(BaseModel):
    county: Optional[str] = None
    property_types: Optional[List[str]] = None
    min_amount_due: Optional[float] = None
    max_amount_due: Optional[float] = None
    in_litigation: Optional[bool] = None
    in_payment_agreement: Optional[bool] = None
    in_bankruptcy: Optional[bool] = None
    is_absentee_owner: Optional[bool] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    owner_name: Optional[str] = None
    limit: int = Field(25, ge=1, le=100)
    offset: int = Field(0, ge=0)

@app.post("/search")
def search_properties(req: SearchRequest, request: Request):
    if not check_rate_limit(request.client.host):
        raise HTTPException(429, "Rate limit exceeded: 100 requests/day per IP.")
    county_slug = req.county.lower().strip() if req.county else None
    if county_slug and county_slug not in COUNTIES:
        raise HTTPException(400, f"Unknown county. Valid: {', '.join(COUNTIES)}")
    targets = {county_slug: COUNTIES[county_slug]} if county_slug else COUNTIES
    all_results = []
    for cname, schema in targets.items():
        try:
            all_results.extend(search_county(cname, schema, req.property_types, req.min_amount_due,
                req.max_amount_due, req.in_litigation, req.in_payment_agreement, req.in_bankruptcy,
                req.is_absentee_owner, req.zip_code, req.city, req.owner_name, req.limit, req.offset))
        except Exception as e:
            all_results.append({"county": cname, "error": str(e)})
    all_results.sort(key=lambda r: r.get("amount_due") or 0, reverse=True)
    if not county_slug: all_results = all_results[:req.limit]
    return {"results": all_results, "count": len(all_results)}

@app.get("/counties")
def list_counties():
    counts = []
    for name, schema in COUNTIES.items():
        try:
            res = supabase.table(schema["table"]).select(schema["acct"], count="exact").limit(1).execute()
            counts.append({"county": name, "records": res.count})
        except Exception as e:
            counts.append({"county": name, "error": str(e)})
    return {"counties": counts}

@app.get("/counties/{county}/summary")
def county_summary(county: str):
    county = county.lower()
    if county not in COUNTIES: raise HTTPException(400, "Unknown county.")
    schema = COUNTIES[county]
    res = supabase.table(schema["table"]).select(schema["due"]).execute()
    rows = res.data or []
    total = sum(r.get(schema["due"]) or 0 for r in rows)
    return {"county": county, "total_records": len(rows), "total_amount_due": round(total, 2)}

@app.get("/property/{county}/{account_number}")
def get_property(county: str, account_number: str):
    county = county.lower()
    if county not in COUNTIES: raise HTTPException(400, "Unknown county.")
    schema = COUNTIES[county]
    res = supabase.table(schema["table"]).select("*").eq(schema["acct"], account_number).limit(1).execute()
    if not res.data: raise HTTPException(404, "Property not found.")
    return normalize_row(res.data[0], schema, county)

MCP_TOOLS = [
    {"name": "search_properties", "description": "Search tax delinquent properties across Texas counties. Filter by county, property type (residential/commercial/industrial/etc), amount owed, litigation status, payment plan, bankruptcy, absentee ownership, zip code, city, or owner name. Returns all available data. zip_code and city filter on mailing address since property-level zip codes are not always in county records.", "inputSchema": {"type": "object", "properties": {"county": {"type": "string", "description": "bexar, harris, dallas, collin, tarrant, travis, denton, nueces, comal, ector, or brazoria. Omit for all."}, "property_types": {"type": "array", "items": {"type": "string"}, "description": "residential, multifamily, commercial, industrial, vacant_land, agricultural, rural, mobile_home, oil_gas, utilities"}, "min_amount_due": {"type": "number"}, "max_amount_due": {"type": "number"}, "in_litigation": {"type": "boolean"}, "in_payment_agreement": {"type": "boolean", "description": "True=has payment plan, False=no payment plan"}, "in_bankruptcy": {"type": "boolean"}, "is_absentee_owner": {"type": "boolean"}, "zip_code": {"type": "string"}, "city": {"type": "string"}, "owner_name": {"type": "string"}, "limit": {"type": "integer", "description": "Default 25, max 100"}, "offset": {"type": "integer"}}}},
    {"name": "list_counties", "description": "List all available Texas counties with delinquent property record counts.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_county_summary", "description": "Total records and total dollars owed for a county.", "inputSchema": {"type": "object", "properties": {"county": {"type": "string"}}, "required": ["county"]}},
    {"name": "get_property", "description": "Full detail for one property by county and account number.", "inputSchema": {"type": "object", "properties": {"county": {"type": "string"}, "account_number": {"type": "string"}}, "required": ["county", "account_number"]}},
]


def _log_usage(tool_name: str, args: dict):
    """Fire-and-forget usage log — never blocks the response."""
    try:
        county = args.get("county") or None
        filters = {k: v for k, v in args.items()
                   if v is not None and k not in ("county", "limit", "offset")} or None
        supabase.table("mcp_usage_log").insert({
            "tool_name": tool_name,
            "county": county,
            "filters": filters,
        }).execute()
    except Exception:
        pass


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    if not check_rate_limit(request.client.host):
        return JSONResponse({"jsonrpc":"2.0","id":None,"error":{"code":429,"message":"Rate limit exceeded: 100 requests/day per IP."}}, status_code=429)
    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    req_id = body.get("id")
    def ok(result): return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": result})
    def err(code, msg): return JSONResponse({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": msg}})
    if method == "initialize":
        return ok({"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "tax-delinquency-mcp", "version": "1.0.0"}})
    if method == "tools/list":
        return ok({"tools": MCP_TOOLS})
    if method == "ping":
        return ok({})
    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        try:
            if tool_name == "search_properties":
                result = search_properties(SearchRequest(**args))
            elif tool_name == "list_counties":
                result = list_counties()
            elif tool_name == "get_county_summary":
                result = county_summary(args["county"])
            elif tool_name == "get_property":
                result = get_property(args["county"], args["account_number"])
            else:
                return err(-32601, f"Unknown tool: {tool_name}")
            return ok({"content": [{"type": "text", "text": json.dumps(result, indent=2)}]})
        except HTTPException as e:
            return err(-32602, e.detail)
        except Exception as e:
            return err(-32603, str(e))
    return err(-32601, f"Method not found: {method}")


class SubscribeRequest(BaseModel):
    email: str

@app.post("/subscribe")
async def subscribe_to_newsletter(req: SubscribeRequest):
    if not BEEHIIV_API_KEY:
        raise HTTPException(status_code=500, detail="Newsletter not configured.")
    email = req.email.strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Invalid email address.")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"https://api.beehiiv.com/v2/publications/{BEEHIIV_PUB_ID}/subscriptions",
            json={"email": email, "reactivate_existing": True, "send_welcome_email": True,
                  "utm_source": "taxdelinquency.com", "utm_medium": "website", "utm_campaign": "hero_form"},
            headers={"Authorization": f"Bearer {BEEHIIV_API_KEY}", "Content-Type": "application/json"},
        )
    if resp.status_code in (200, 201):
        return {"success": True}
    elif resp.status_code == 400:
        raise HTTPException(status_code=400, detail="Invalid email address.")
    raise HTTPException(status_code=500, detail="Subscription failed. Please try again.")

@app.get("/health")
def health():
    return {"status": "ok"}
