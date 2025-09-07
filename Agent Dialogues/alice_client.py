# alice_client.py (v2.1)
import httpx
import re

BOB_URL = "http://127.0.0.1:8000/kqml"
CONV_ID = "procure-2025-09-07-001"

def build_kqml(performative: str, **params) -> str:
    parts = [f"({performative}"]
    for k, v in params.items():
        parts.append(f"  {k} {v}")
    parts.append(")")
    return "\n".join(parts)

def msg1_ask_available_one():
    return build_kqml(
        "ask-one",
        **{
            ":sender": "Alice",
            ":receiver": "Bob",
            ":language": "KIF",
            ":ontology": "warehouse-ontology-v1",
            ":reply-with": "m1",
            ":conversation-id": CONV_ID,
            ":content": """(and
      (instance ?m TelevisionModel)
      (size-inch ?m 50)
      (model-sku ?m ?sku)
      (available-quantity ?sku ?qty))""",
        },
    )

def msg1b_ask_available_all():
    return build_kqml(
        "ask-all",
        **{
            ":sender": "Alice",
            ":receiver": "Bob",
            ":language": "KIF",
            ":ontology": "warehouse-ontology-v1",
            ":reply-with": "m1b",
            ":conversation-id": CONV_ID,
            ":content": """(and
      (instance ?m TelevisionModel)
      (size-inch ?m 50)
      (model-sku ?m ?sku)
      (available-quantity ?sku ?qty))""",
        },
    )

def extract_sku_and_qty_from_block(kif_and: str):
    sku, qty = None, None
    for line in kif_and.splitlines():
        t = line.strip()
        if t.startswith("(model-sku "):
            toks = t.replace("(", "").replace(")", "").split()
            sku = toks[-1]
        if t.startswith("(available-quantity "):
            toks = t.replace("(", "").replace(")", "").split()
            qty = toks[-1]
    return sku, qty

def msg3_ask_hdmi(sku: str):
    return build_kqml(
        "ask-one",
        **{
            ":sender": "Alice",
            ":receiver": "Bob",
            ":language": "KIF",
            ":ontology": "warehouse-ontology-v1",
            ":in-reply-to": "m2",
            ":reply-with": "m3",
            ":conversation-id": CONV_ID,
            ":content": f"(hdmi-slots {sku} ?n)",
        },
    )

def msgA_reserve(sku: str, n: int):
    return build_kqml(
        "achieve",
        **{
            ":sender": "Alice",
            ":receiver": "Bob",
            ":language": "KIF",
            ":ontology": "warehouse-ontology-v1",
            ":reply-with": "mA",
            ":conversation-id": CONV_ID,
            ":content": f"(reserve {sku} {n})",
        },
    )

# ---------- NEW: small regex helpers ----------
def extract_hdmi_line(text: str) -> str:
    m = re.search(r"\(hdmi-slots\s+[^\s\)]+\s+\d+\)", text)
    return m.group(0) if m else "N/A"

def extract_available_quantity(text: str, sku: str):
    m = re.search(rf"\(available-quantity\s+{re.escape(sku)}\s+(\d+)\)", text)
    return int(m.group(1)) if m else None

def extract_models_and_qty(text: str):
    """
    Returns list of tuples: [(model, sku, qty), ...]
    Works even if Bob wraps blocks inside (and (and ...) (and ...)).
    """
    models = {}
    for model, sku in re.findall(r"\(model-sku\s+([^\s\)]+)\s+([^\s\)]+)\)", text):
        models[sku] = {"model": model, "qty": None}
    for sku, qty in re.findall(r"\(available-quantity\s+([^\s\)]+)\s+(\d+)\)", text):
        if sku in models:
            models[sku]["qty"] = int(qty)
        else:
            models[sku] = {"model": "UNKNOWN", "qty": int(qty)}
    # Return as sorted list by SKU (just for stable printing)
    return [(v["model"], sku, v["qty"]) for sku, v in sorted(models.items(), key=lambda x: x[0])]

def main():
    tr = []

    # --- ask-one ---
    m1 = msg1_ask_available_one()
    tr.append(("Alice → Bob", m1))
    r1 = httpx.post(BOB_URL, content=m1, timeout=10)
    tr.append(("Bob → Alice", r1.text))

    # extract first block content
    s = r1.text
    cstart = s.find(":content")
    and_start = s.find("(and", cstart)
    and_end = s.rfind(")")
    block = s[and_start:and_end+1]
    sku, qty = extract_sku_and_qty_from_block(block)

    # --- ask-one (hdmi) ---
    m3 = msg3_ask_hdmi(sku)
    tr.append(("Alice → Bob", m3))
    r2 = httpx.post(BOB_URL, content=m3, timeout=10)
    tr.append(("Bob → Alice", r2.text))

    # --- achieve (reserve 5) ---
    mA = msgA_reserve(sku, 5)
    tr.append(("Alice → Bob", mA))
    r3 = httpx.post(BOB_URL, content=mA, timeout=10)
    tr.append(("Bob → Alice", r3.text))

    # --- ask-all (see both 50" models) ---
    m1b = msg1b_ask_available_all()
    tr.append(("Alice → Bob", m1b))
    r4 = httpx.post(BOB_URL, content=m1b, timeout=10)
    tr.append(("Bob → Alice", r4.text))

    print("\n===== Dialogue Transcript (v2.1) =====\n")
    for who, msg in tr:
        print(f";; {who}")
        print(msg)
        print()

    # ----- Clean summary -----
    hdmi_line = extract_hdmi_line(r2.text)
    new_qty = extract_available_quantity(r3.text, sku)
    all_models = extract_models_and_qty(r4.text)

    print("Summary:")
    print(f"- First 50\" SKU: {sku}, initial qty: {qty}")
    print(f"- HDMI reply: {hdmi_line}")
    if new_qty is not None:
        print(f"- Reserved 5 units → new available quantity for {sku}: {new_qty}")
    else:
        print("- Reserved 5 units → could not parse new quantity (check reply).")
    print("- ask-all inventory:")
    for model, ssku, q in all_models:
        print(f"  • {model} ({ssku}) → qty {q}")

if __name__ == "__main__":
    main()
