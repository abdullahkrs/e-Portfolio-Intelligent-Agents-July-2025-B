# bob_server.py (v2)
from fastapi import FastAPI, Request, Response
from sexpdata import loads, Symbol
import re

app = FastAPI(title="Bob Warehouse Agent")

# --- Tiny "KB" for demo: now has TWO 50" models ---
KB = {
    "TVM-50-ULTRA": {"size": 50, "sku": "SKU-50TV-ABC", "qty": 42, "hdmi": 3},
    "TVM-50-VISTA": {"size": 50, "sku": "SKU-50TV-XYZ", "qty": 17, "hdmi": 2},
}

def parse_kqml(kqml_text: str):
    sexp = loads(kqml_text)
    performative = str(sexp[0])
    params = {}
    i = 1
    while i < len(sexp):
        key = str(sexp[i])
        val = sexp[i + 1]
        if isinstance(val, Symbol):
            val = str(val)
        if isinstance(val, list):
            def _ser(x):
                if isinstance(x, Symbol):
                    return str(x)
                if isinstance(x, list):
                    return "(" + " ".join(_ser(xx) for xx in x) + ")"
                return str(x)
            val = _ser(val)
        params[key] = val
        i += 2
    return {"performative": performative, "params": params}

def build_kqml(performative: str, **params) -> str:
    parts = [f"({performative}"]
    for k, v in params.items():
        parts.append(f"  {k} {v}")
    parts.append(")")
    return "\n".join(parts)

def facts_for_model(model_key: str) -> str:
    m = KB[model_key]
    sku = m["sku"]
    return f"""(and
      (instance {model_key} TelevisionModel)
      (size-inch {model_key} {m['size']})
      (model-sku {model_key} {sku})
      (available-quantity {sku} {m['qty']}))"""

@app.post("/kqml")
async def receive_kqml(req: Request):
    text = await req.body()
    msg = parse_kqml(text.decode("utf-8"))

    perf = msg["performative"]
    p = msg["params"]
    sender = p.get(":sender", "UNKNOWN")
    conv_id = p.get(":conversation-id", "conv-1")
    in_reply_to = p.get(":in-reply-to", None)
    reply_with = p.get(":reply-with", None)
    content = p.get(":content", "")

    # --- ask-one: “any 50-inch model with qty?”
    ask_qty_one = (
        perf == "ask-one"
        and "size-inch ?m 50" in content
        and "available-quantity ?sku ?qty" in content
    )

    # --- ask-all: “all 50-inch models with qty?”
    ask_qty_all = (
        perf == "ask-all"
        and "size-inch ?m 50" in content
        and "available-quantity ?sku ?qty" in content
    )

    # --- ask-one hdmi
    ask_hdmi = (perf == "ask-one") and "(hdmi-slots " in content and " ?n)" in content

    # --- achieve: reserve stock
    # (achieve ... :content (reserve <SKU> <N>))
    achieve_reserve = (perf == "achieve") and "(reserve " in content

    if ask_qty_one:
        # Return the first matching 50" model (demo behavior)
        model_key = next((k for k, v in KB.items() if v["size"] == 50), None)
        if not model_key:
            sorry = build_kqml(
                "sorry",
                **{
                    ":sender": "Bob",
                    ":receiver": sender,
                    ":in-reply-to": reply_with or "m1",
                    ":conversation-id": conv_id,
                    ":content": '"no-50-inch-model-found"',
                },
            )
            return Response(sorry, media_type="text/plain")
        kif = facts_for_model(model_key)
        reply = build_kqml(
            "tell",
            **{
                ":sender": "Bob",
                ":receiver": sender,
                ":language": "KIF",
                ":ontology": "warehouse-ontology-v1",
                ":in-reply-to": reply_with or "m1",
                ":reply-with": "m2",
                ":conversation-id": conv_id,
                ":content": kif,
            },
        )
        return Response(reply, media_type="text/plain")

    if ask_qty_all:
        # Return facts for ALL 50" models in one tell
        blocks = [facts_for_model(k) for k, v in KB.items() if v["size"] == 50]
        if not blocks:
            sorry = build_kqml(
                "sorry",
                **{
                    ":sender": "Bob",
                    ":receiver": sender,
                    ":in-reply-to": reply_with or "m1",
                    ":conversation-id": conv_id,
                    ":content": '"no-50-inch-model-found"',
                },
            )
            return Response(sorry, media_type="text/plain")
        kif = "(and\n" + "\n".join(blocks) + "\n)"
        reply = build_kqml(
            "tell",
            **{
                ":sender": "Bob",
                ":receiver": sender,
                ":language": "KIF",
                ":ontology": "warehouse-ontology-v1",
                ":in-reply-to": reply_with or "m1",
                ":reply-with": "m2-all",
                ":conversation-id": conv_id,
                ":content": kif,
            },
        )
        return Response(reply, media_type="text/plain")

    if ask_hdmi:
        sku_match = re.search(r"\(hdmi-slots\s+([^\s\)]+)\s+\?n\)", content)
        if sku_match:
            sku = sku_match.group(1)
            model = next((k for k, v in KB.items() if v["sku"] == sku), None)
            if model:
                n = KB[model]["hdmi"]
                kif = f"(hdmi-slots {sku} {n})"
                reply = build_kqml(
                    "tell",
                    **{
                        ":sender": "Bob",
                        ":receiver": sender,
                        ":language": "KIF",
                        ":ontology": "warehouse-ontology-v1",
                        ":in-reply-to": reply_with or "m3",
                        ":conversation-id": conv_id,
                        ":content": kif,
                    },
                )
                return Response(reply, media_type="text/plain")

    if achieve_reserve:
        # (reserve <SKU> <N>)
        m = re.search(r"\(reserve\s+([^\s\)]+)\s+([0-9]+)\)", content)
        if m:
            sku, n = m.group(1), int(m.group(2))
            model = next((k for k, v in KB.items() if v["sku"] == sku), None)
            if not model:
                deny = build_kqml(
                    "deny",
                    **{
                        ":sender": "Bob",
                        ":receiver": sender,
                        ":in-reply-to": reply_with or "mA",
                        ":conversation-id": conv_id,
                        ":content": f'"unknown-sku {sku}"',
                    },
                )
                return Response(deny, media_type="text/plain")
            if KB[model]["qty"] >= n:
                KB[model]["qty"] -= n
                kif = f"""(and
  (reserved {sku} {n})
  (available-quantity {sku} {KB[model]["qty"]})
)"""
                reply = build_kqml(
                    "tell",
                    **{
                        ":sender": "Bob",
                        ":receiver": sender,
                        ":language": "KIF",
                        ":ontology": "warehouse-ontology-v1",
                        ":in-reply-to": reply_with or "mA",
                        ":conversation-id": conv_id,
                        ":content": kif,
                    },
                )
                return Response(reply, media_type="text/plain")
            else:
                deny = build_kqml(
                    "deny",
                    **{
                        ":sender": "Bob",
                        ":receiver": sender,
                        ":in-reply-to": reply_with or "mA",
                        ":conversation-id": conv_id,
                        ":content": f'(insufficient-quantity {sku} requested {n} available {KB[model]["qty"]})',
                    },
                )
                return Response(deny, media_type="text/plain")

    # Default fallback
    not_understood = build_kqml(
        "sorry",
        **{
            ":sender": "Bob",
            ":receiver": sender,
            ":in-reply-to": reply_with or "unknown",
            ":conversation-id": conv_id,
            ":content": '"not-understood"',
        },
    )
    return Response(not_understood, media_type="text/plain")
