# Part 3 — Hawker Cash Register (Ah Beng Vegetarian Food)

Streamlit application that works like an old-style cash receipting machine.

## Files to submit

| File | Purpose |
|---|---|
| `app.py` | The whole application |
| `config.txt` | Shop name, payment types, opening float (start-up file) |
| `sales.txt` | Transaction storage (start-up file, ships with demo data) |
| `cashup.txt` | One line per day that has been closed (start-up file) |
| `screenshots/` | Screen dumps for the operational manual |
| `Part3_Documentation.docx` | AI prompts + code explanation + operational manual |

## How to run

```
pip install streamlit
streamlit run app.py
```

## Data format

`sales.txt` — comma separated, one line per transaction, first line is the header:

```
date,time,receipt_no,sales,rendered,change,payment_type
2026-09-17,12:31:05,0001,4.50,5.00,0.50,Cash
```

Dates are written as `YYYY-MM-DD` on purpose: sorting the text sorts the dates,
and `date[:7]` gives the month. No date library is needed for the reports.

`cashup.txt` — one line per closed day:

```
date,time,opening_float,cash_sales,expected,counted,variance
2026-09-17,20:29:02,50.00,62.50,112.50,111.00,-1.50
```

`config.txt` — one `setting=value` per line. Adding a new payment type is a text
edit, not a code change. `opening_float` is the small change the drawer starts
the day with.

## Screens

1. **Cash Register** — key in the amount payable and the cash received, press
   **Total**, and the change plus a receipt are shown.
   Electronic payments auto-fill the received amount and disable the box.
2. **Daily Cash-Up** — count the drawer at closing time. Opening float plus cash
   sales gives what the drawer should hold; the counted amount gives the
   variance. Electronic payments are listed separately because that money never
   reaches the drawer. Prints a Z reading, the way an old till did.
3. **Daily Report** — every transaction of one day + sales by payment type.
4. **Monthly Report** — sales summarised by day + sales by payment type.

### Why the amounts sit inside a form

An earlier version worked out the change while the amounts were being typed.
That version could show one figure on screen and write a different one to the
file: a mouse wheel passing over an amount box nudges the number in the browser,
but Streamlit is only told about it when the box loses focus, which happens at
the very moment the save button is pressed. The screen said S$ 14.20 while
S$ 14.15 went into the file.

`st.form` removes the gap. Every box in a form is read once, at the instant
**Total** is pressed, so the change that is worked out and the change that is
written to the file always come from the same reading. The figures shown after
the sale are read back out of the saved record, not recalculated.

## Coding limits observed

No `class`, no `lambda`, no `pandas`, no database. All totals are produced with
dictionary accumulation inside `for` loops.

## Known limitation

Amounts are stored as floating point numbers rounded to 2 decimals. For a real
production system, money should be stored in cents as whole numbers to avoid any
floating point rounding drift.

## Resetting the demo data

Keep only the header line in `sales.txt`:

```
date,time,receipt_no,sales,rendered,change,payment_type
```
