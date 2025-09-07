# Agent Dialogue (KQML + KIF): Alice ↔ Bob Warehouse Demo

A minimal, working example of two software agents communicating via **KQML** (for messages) and **KIF** (for logical content) over HTTP:

- **Alice** — procurement agent (client).  
- **Bob** — warehouse stock agent (FastAPI server).

The demo covers:
- `ask-one` for available stock of 50" TVs
- `ask-one` for `(hdmi-slots <SKU> ?n)`
- `achieve` to `(reserve <SKU> <N>)`
- `ask-all` to list **all** 50" models with quantities

> Arabic (مختصر): مثال عملي بسيط للتواصل بين وكيلي برمجيات باستخدام KQML و KIF عبر HTTP. أليس (الشراء) تسأل بوب (المستودع) عن المخزون وخصائص التلفزيونات، ويمكنها أيضًا حجز الكمية المطلوبة.

---

## ✨ Features
- KQML envelopes with KIF content
- FastAPI endpoint for Bob (`/kqml`)
- Simple in-memory “KB” with two 50" TV models
- Demo of `ask-one`, `ask-all`, and `achieve (reserve ...)`
- Clean client transcript + summary

---

## 📦 Requirements
- Python 3.10+ (tested on 3.11)
- Windows, macOS, or Linux

Install deps:
```bash
pip install -r requirements.txt
