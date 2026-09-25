"""
Ah Beng Vegetarian Food - Simple Cash Register
AN6100 Assignment Part 3

Works like an old-style cash receipting machine:
  key in the amount payable -> key in the cash received -> the change is shown.

Storage is plain text only (no database):
  sales.txt   - one line per transaction
  config.txt  - shop name and accepted payment types

Coding limits followed in this file:
  no class, no lambda, no pandas.
"""

import csv
import datetime

import streamlit as st

# ---------------------------------------------------------------------------
# Section 1 - Settings and start-up
# ---------------------------------------------------------------------------

SALES_FILE = "sales.txt"
CONFIG_FILE = "config.txt"

CASHUP_FILE = "cashup.txt"

FIELDS = ["date", "time", "receipt_no", "sales", "rendered", "change", "payment_type"]

CASHUP_FIELDS = ["date", "time", "opening_float", "cash_sales",
                 "expected", "counted", "variance"]

DEFAULT_CONFIG = [
    "store_name=Ah Beng Vegetarian Food",
    "payment_types=Cash,PayNow,PayLah,PayWave",
    "cash_type=Cash",
    "opening_float=50.00",
]


def ensure_files():
    """Create the two text files on the very first run so nothing crashes."""
    try:
        with open(SALES_FILE, "r", encoding="utf-8") as f:
            f.read(1)
    except FileNotFoundError:
        with open(SALES_FILE, "w", encoding="utf-8") as f:
            f.write(",".join(FIELDS) + "\n")

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            f.read(1)
    except FileNotFoundError:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            for line in DEFAULT_CONFIG:
                f.write(line + "\n")

    try:
        with open(CASHUP_FILE, "r", encoding="utf-8") as f:
            f.read(1)
    except FileNotFoundError:
        with open(CASHUP_FILE, "w", encoding="utf-8") as f:
            f.write(",".join(CASHUP_FIELDS) + "\n")


def load_config():
    """Read config.txt into a dictionary of setting name -> setting value."""
    config = {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            parts = line.split("=", 1)
            config[parts[0].strip()] = parts[1].strip()
    return config


def opening_float_default(config):
    """The float the shop normally starts the day with, taken from config.txt."""
    try:
        return round(float(config.get("opening_float", "50.00")), 2)
    except ValueError:
        return 50.00


def get_payment_types(config):
    """Turn the comma separated setting into a clean list."""
    raw = config.get("payment_types", "Cash")
    types = []
    for item in raw.split(","):
        item = item.strip()
        if item != "":
            types.append(item)
    if len(types) == 0:
        types.append("Cash")
    return types


# ---------------------------------------------------------------------------
# Section 2 - Reading and writing transactions
# ---------------------------------------------------------------------------

def clean_row(raw):
    """Check one line read from sales.txt. Return a tidy dict, or None if broken."""
    for name in FIELDS:
        if raw.get(name) is None:
            return None
    try:
        sales = float(raw["sales"])
        rendered = float(raw["rendered"])
        change = float(raw["change"])
    except ValueError:
        return None
    if len(raw["date"]) != 10:
        return None

    record = {}
    record["date"] = raw["date"].strip()
    record["time"] = raw["time"].strip()
    record["receipt_no"] = raw["receipt_no"].strip()
    record["sales"] = sales
    record["rendered"] = rendered
    record["change"] = change
    record["payment_type"] = raw["payment_type"].strip()
    return record


def read_all():
    """Read every transaction. Returns the good rows and how many lines were bad."""
    rows = []
    bad = 0
    with open(SALES_FILE, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            record = clean_row(raw)
            if record is None:
                bad = bad + 1
            else:
                rows.append(record)
    return rows, bad


def append_txn(record):
    """Add one transaction to the end of sales.txt."""
    line = ",".join([
        record["date"],
        record["time"],
        record["receipt_no"],
        money(record["sales"]),
        money(record["rendered"]),
        money(record["change"]),
        record["payment_type"],
    ])
    with open(SALES_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def next_receipt_no(rows, day):
    """Receipt numbers restart from 0001 on each business day."""
    count = 0
    for r in rows:
        if r["date"] == day:
            count = count + 1
    return str(count + 1).zfill(4)


def clean_cashup(raw):
    """Check one line of cashup.txt. Return a tidy dict, or None if broken."""
    for name in CASHUP_FIELDS:
        if raw.get(name) is None:
            return None
    try:
        opening = float(raw["opening_float"])
        cash_sales = float(raw["cash_sales"])
        expected = float(raw["expected"])
        counted = float(raw["counted"])
        variance = float(raw["variance"])
    except ValueError:
        return None

    record = {}
    record["date"] = raw["date"].strip()
    record["time"] = raw["time"].strip()
    record["opening_float"] = opening
    record["cash_sales"] = cash_sales
    record["expected"] = expected
    record["counted"] = counted
    record["variance"] = variance
    return record


def read_cashups():
    """Read every day that has already been closed."""
    records = []
    bad = 0
    with open(CASHUP_FILE, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            record = clean_cashup(raw)
            if record is None:
                bad = bad + 1
            else:
                records.append(record)
    return records, bad


def append_cashup(record):
    """Add one closed day to the end of cashup.txt."""
    line = ",".join([
        record["date"],
        record["time"],
        money(record["opening_float"]),
        money(record["cash_sales"]),
        money(record["expected"]),
        money(record["counted"]),
        money(record["variance"]),
    ])
    with open(CASHUP_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def find_cashup(cashups, day):
    """The closing record of one day, or None when the day is still open."""
    for c in cashups:
        if c["date"] == day:
            return c
    return None


# ---------------------------------------------------------------------------
# Section 3 - Calculations (plain functions, easy to test)
# ---------------------------------------------------------------------------

def money(value):
    """Show a number as dollars and cents, e.g. 4.5 -> '4.50'."""
    return f"{value:.2f}"


def money_line(label, value):
    """One printed line of a slip: label on the left, amount on the right."""
    return label.ljust(15) + "S$ " + money(value).rjust(14)


def calc_change(sales, rendered):
    """Change due. Returns None when the cash received is not enough."""
    if rendered < sales:
        return None
    return round(rendered - sales, 2)


def filter_by_day(rows, day):
    """Keep only the transactions of one day, e.g. day = '2026-09-17'."""
    picked = []
    for r in rows:
        if r["date"] == day:
            picked.append(r)
    return picked


def filter_by_month(rows, month):
    """Keep only the transactions of one month, e.g. month = '2026-09'."""
    picked = []
    for r in rows:
        if r["date"][:7] == month:
            picked.append(r)
    return picked


def total_of(rows):
    """Add up the sales amount of the given transactions."""
    total = 0.0
    for r in rows:
        total = total + r["sales"]
    return round(total, 2)


def cash_sales_of(rows, cash_type):
    """Money that should physically be in the drawer: the cash sales only."""
    total = 0.0
    for r in rows:
        if r["payment_type"] == cash_type:
            total = total + r["sales"]
    return round(total, 2)


def summarise_by_day(rows):
    """Sales total and transaction count for each date."""
    totals = {}
    counts = {}
    for r in rows:
        key = r["date"]
        totals[key] = round(totals.get(key, 0.0) + r["sales"], 2)
        counts[key] = counts.get(key, 0) + 1
    return totals, counts


def summarise_by_payment(rows):
    """Sales total and transaction count for each payment type."""
    totals = {}
    counts = {}
    for r in rows:
        key = r["payment_type"]
        totals[key] = round(totals.get(key, 0.0) + r["sales"], 2)
        counts[key] = counts.get(key, 0) + 1
    return totals, counts


def list_months(rows):
    """All months that have data, newest first."""
    found = {}
    for r in rows:
        found[r["date"][:7]] = True
    months = sorted(found.keys())
    months.reverse()
    return months


# ---------------------------------------------------------------------------
# Section 4 - Table builders for the screen
# ---------------------------------------------------------------------------

def build_txn_table(rows):
    """Transactions sorted by receipt number, ready for st.table."""
    markers = []
    position = 0
    for r in rows:
        markers.append(r["receipt_no"] + "|" + str(position).zfill(6))
        position = position + 1
    markers.sort()

    table = []
    for marker in markers:
        r = rows[int(marker.split("|")[1])]
        table.append({
            "Receipt": r["receipt_no"],
            "Time": r["time"],
            "Sales (S$)": money(r["sales"]),
            "Received (S$)": money(r["rendered"]),
            "Change (S$)": money(r["change"]),
            "Payment": r["payment_type"],
        })
    return table


def build_payment_table(rows):
    """Sales by payment type, biggest contributor listed by name order."""
    totals, counts = summarise_by_payment(rows)
    grand = total_of(rows)

    table = []
    for name in sorted(totals.keys()):
        if grand > 0:
            share = money(totals[name] / grand * 100) + "%"
        else:
            share = "0.00%"
        table.append({
            "Payment type": name,
            "Transactions": counts[name],
            "Sales (S$)": money(totals[name]),
            "Share": share,
        })
    return table


def build_daily_table(rows):
    """Sales by day, used by the monthly report."""
    totals, counts = summarise_by_day(rows)

    table = []
    for day in sorted(totals.keys()):
        table.append({
            "Date": day,
            "Transactions": counts[day],
            "Sales (S$)": money(totals[day]),
            "Average per sale (S$)": money(totals[day] / counts[day]),
        })
    return table


# ---------------------------------------------------------------------------
# Section 5 - Screen 1: the cash register
# ---------------------------------------------------------------------------

def input_round():
    """A counter used to build the widget keys.

    Adding one to it gives the amount boxes a brand new key, so Streamlit
    draws empty boxes for the next customer instead of keeping the old
    amounts on screen.
    """
    if "txn_round" not in st.session_state:
        st.session_state["txn_round"] = 0
    return st.session_state["txn_round"]


def clear_inputs():
    """Empty the amount boxes so the next customer can be served."""
    st.session_state["txn_round"] = input_round() + 1


def show_last_receipt():
    """Show what was actually saved: the change is read back from the record."""
    if "last_receipt" not in st.session_state:
        return
    r = st.session_state["last_receipt"]

    st.success("Transaction saved. Receipt no. " + r["receipt_no"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Total**")
        st.markdown("## S$ " + money(r["sales"]))
    with col2:
        st.markdown("**Received**")
        st.markdown("## S$ " + money(r["rendered"]))
    with col3:
        st.markdown("**Change to give**")
        st.markdown("## S$ " + money(r["change"]))

    lines = []
    lines.append(r["store_name"].center(32))
    lines.append("-" * 32)
    lines.append("Receipt : " + r["receipt_no"])
    lines.append("Date    : " + r["date"] + "  " + r["time"])
    lines.append("-" * 32)
    lines.append("Total        S$ " + money(r["sales"]).rjust(9))
    lines.append("Received     S$ " + money(r["rendered"]).rjust(9))
    lines.append("Change       S$ " + money(r["change"]).rjust(9))
    lines.append("-" * 32)
    lines.append("Paid by : " + r["payment_type"])
    lines.append("Thank you, please come again!".center(32))
    st.code("\n".join(lines))


def render_register(config, rows):
    st.header("Cash Register")

    today = str(datetime.date.today())
    receipt_no = next_receipt_no(rows, today)
    payment_types = get_payment_types(config)
    cash_type = config.get("cash_type", "Cash")

    st.caption("Business day " + today + "  |  next receipt no. " + receipt_no)

    # The payment type is chosen outside the form. It has to take effect at
    # once, because an electronic payment must switch off the cash box.
    payment_type = st.selectbox("Payment type", payment_types, key="in_pay")
    is_cash = (payment_type == cash_type)

    suffix = "_" + str(input_round())

    # Both amounts sit inside a form. Streamlit reads every box in a form at
    # the moment Total is pressed, so the change that is worked out and the
    # change that is written to the file always come from the same reading.
    with st.form("register" + suffix):
        left, right = st.columns([3, 2])

        with left:
            sales = st.number_input(
                "Amount payable (S$)",
                min_value=0.00, step=0.05, format="%.2f", key="in_sales" + suffix,
            )

            if is_cash:
                rendered = st.number_input(
                    "Cash received (S$)",
                    min_value=0.00, step=0.05, format="%.2f", key="in_rendered" + suffix,
                )
            else:
                rendered = sales
                st.number_input(
                    "Cash received (S$)", value=sales, format="%.2f", disabled=True,
                    help="Electronic payment is always the exact amount.",
                )

        with right:
            st.markdown("**Paying by**")
            st.markdown("## " + payment_type)
            if is_cash:
                st.caption("Key in both amounts, then press Total.")
            else:
                st.caption("No change is given for " + payment_type + ".")

        submitted = st.form_submit_button("Total", type="primary")

    if submitted:
        if sales <= 0:
            st.error("Amount payable must be more than zero.")
        else:
            change = calc_change(sales, rendered)
            if change is None:
                # The dollar signs are escaped, otherwise Markdown reads the
                # pair of them as the start and end of a mathematics formula.
                st.error(
                    "Nothing was saved. Cash received S\\$ " + money(rendered)
                    + " is less than the amount payable S\\$ " + money(sales) + "."
                )
            else:
                now = datetime.datetime.now()
                record = {
                    "date": today,
                    "time": now.strftime("%H:%M:%S"),
                    "receipt_no": receipt_no,
                    "sales": round(sales, 2),
                    "rendered": round(rendered, 2),
                    "change": change,
                    "payment_type": payment_type,
                }
                append_txn(record)

                record["store_name"] = config.get("store_name", "My Store")
                st.session_state["last_receipt"] = record
                clear_inputs()
                st.rerun()

    show_last_receipt()


# ---------------------------------------------------------------------------
# Section 6 - Screen 2: one day's transactions
# ---------------------------------------------------------------------------

def render_day_report(rows):
    st.header("Daily Report")

    chosen = st.date_input("Business day", value=datetime.date.today())
    day = str(chosen)
    day_rows = filter_by_day(rows, day)

    if len(day_rows) == 0:
        st.info("No transaction was recorded on " + day + ".")
        return

    total = total_of(day_rows)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Transactions**")
        st.markdown("## " + str(len(day_rows)))
    with col2:
        st.markdown("**Total sales**")
        st.markdown("## S$ " + money(total))
    with col3:
        st.markdown("**Average sale**")
        st.markdown("## S$ " + money(total / len(day_rows)))

    st.subheader("All transactions of " + day)
    st.table(build_txn_table(day_rows))

    st.subheader("Sales by payment type")
    st.table(build_payment_table(day_rows))


# ---------------------------------------------------------------------------
# Section 7 - Screen 3: one month, summarised by day
# ---------------------------------------------------------------------------

def render_month_report(rows):
    st.header("Monthly Report")

    months = list_months(rows)
    if len(months) == 0:
        st.info("There is no sales data yet. Record a transaction first.")
        return

    month = st.selectbox("Business month", months)
    month_rows = filter_by_month(rows, month)
    total = total_of(month_rows)
    daily = build_daily_table(month_rows)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Business days**")
        st.markdown("## " + str(len(daily)))
    with col2:
        st.markdown("**Transactions**")
        st.markdown("## " + str(len(month_rows)))
    with col3:
        st.markdown("**Total sales**")
        st.markdown("## S$ " + money(total))

    st.subheader("Sales by day")
    st.table(daily)

    st.subheader("Sales by payment type")
    st.table(build_payment_table(month_rows))


# ---------------------------------------------------------------------------
# Section 8 - Screen 4: closing the day (cash-up / Z reading)
# ---------------------------------------------------------------------------

def build_zreport(store_name, record, other_totals, txn_count, grand_total):
    """The closing slip, printed the same width as a till receipt."""
    lines = []
    lines.append(store_name.center(32))
    lines.append("DAILY CASH-UP (Z READING)".center(32))
    lines.append("-" * 32)
    lines.append("Date    : " + record["date"])
    lines.append("Closed  : " + record["time"])
    lines.append("-" * 32)
    lines.append("IN THE CASH DRAWER")
    lines.append(money_line("Opening float", record["opening_float"]))
    lines.append(money_line("Cash sales", record["cash_sales"]))
    lines.append(money_line("Expected", record["expected"]))
    lines.append(money_line("Counted", record["counted"]))
    lines.append(money_line("Variance", record["variance"]))
    lines.append("-" * 32)

    if len(other_totals) > 0:
        lines.append("NOT IN THE DRAWER")
        for name in sorted(other_totals.keys()):
            lines.append(money_line(name, other_totals[name]))
        lines.append("-" * 32)

    lines.append(money_line("Total sales", grand_total))
    lines.append("Transactions  : " + str(txn_count))
    lines.append("-" * 32)
    return "\n".join(lines)


def split_payments(rows, cash_type):
    """Separate the electronic payments from the cash ones."""
    totals, counts = summarise_by_payment(rows)
    others = {}
    for name in totals:
        if name != cash_type:
            others[name] = totals[name]
    return others


def show_variance(variance):
    """Say in plain words whether the drawer balances."""
    if variance == 0:
        st.success("The drawer balances exactly.")
    elif variance < 0:
        st.warning(
            "The drawer is short by S\\$ " + money(-variance)
            + ". Check for a wrong change or a sale that was never keyed in."
        )
    else:
        st.warning(
            "The drawer has S\\$ " + money(variance)
            + " more than expected. Check for a sale keyed in twice."
        )


def render_cashup(config, rows, cashups):
    st.header("Daily Cash-Up")

    cash_type = config.get("cash_type", "Cash")
    store_name = config.get("store_name", "My Store")

    chosen = st.date_input("Business day", value=datetime.date.today())
    day = str(chosen)
    day_rows = filter_by_day(rows, day)

    if len(day_rows) == 0:
        st.info("Nothing was sold on " + day + ", so there is nothing to count.")
        return

    cash_sales = cash_sales_of(day_rows, cash_type)
    others = split_payments(day_rows, cash_type)
    grand = total_of(day_rows)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Cash taken**")
        st.markdown("## S$ " + money(cash_sales))
    with col2:
        st.markdown("**Paid electronically**")
        st.markdown("## S$ " + money(round(grand - cash_sales, 2)))
    with col3:
        st.markdown("**Transactions**")
        st.markdown("## " + str(len(day_rows)))

    closed = find_cashup(cashups, day)

    if closed is not None:
        st.success("This day was already closed at " + closed["time"] + ".")
        show_variance(closed["variance"])
        st.code(build_zreport(store_name, closed, others, len(day_rows), grand))
        return

    st.divider()
    st.caption(
        "Count the money in the drawer, then key in the two amounts below. "
        "Only the cash is counted here - electronic payments never reach the drawer."
    )

    with st.form("cashup_" + day):
        left, right = st.columns(2)
        with left:
            opening = st.number_input(
                "Opening float (S$)",
                min_value=0.00, step=1.00, format="%.2f",
                value=opening_float_default(config),
                help="The small change put into the drawer before opening.",
            )
        with right:
            counted = st.number_input(
                "Cash counted in the drawer (S$)",
                min_value=0.00, step=1.00, format="%.2f",
            )
        submitted = st.form_submit_button("Close the day", type="primary")

    if submitted:
        expected = round(opening + cash_sales, 2)
        variance = round(counted - expected, 2)
        now = datetime.datetime.now()
        record = {
            "date": day,
            "time": now.strftime("%H:%M:%S"),
            "opening_float": round(opening, 2),
            "cash_sales": cash_sales,
            "expected": expected,
            "counted": round(counted, 2),
            "variance": variance,
        }
        append_cashup(record)
        st.rerun()


# ---------------------------------------------------------------------------
# Section 9 - Main program
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Hawker Cash Register", page_icon="🧾")

    ensure_files()
    config = load_config()
    rows, bad = read_all()
    cashups, bad_cashups = read_cashups()

    st.title(config.get("store_name", "My Store"))
    st.caption("Simple cash register - AN6100 Assignment Part 3")

    if bad > 0:
        st.warning(
            "Skipped " + str(bad) + " damaged line(s) in " + SALES_FILE
            + ". The rest of the data is still usable."
        )

    if bad_cashups > 0:
        st.warning(
            "Skipped " + str(bad_cashups) + " damaged line(s) in " + CASHUP_FILE
            + ". The rest of the data is still usable."
        )

    st.sidebar.title("Menu")
    screen = st.sidebar.radio(
        "Go to",
        ["Cash Register", "Daily Cash-Up", "Daily Report", "Monthly Report"],
    )
    st.sidebar.divider()
    st.sidebar.caption("Transactions on file: " + str(len(rows)))

    today = str(datetime.date.today())
    if find_cashup(cashups, today) is None:
        st.sidebar.caption("Today is still open.")
    else:
        st.sidebar.caption("Today has been closed.")

    if screen == "Cash Register":
        render_register(config, rows)
    elif screen == "Daily Cash-Up":
        render_cashup(config, rows, cashups)
    elif screen == "Daily Report":
        render_day_report(rows)
    else:
        render_month_report(rows)


if __name__ == "__main__":
    main()
