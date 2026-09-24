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

FIELDS = ["date", "time", "receipt_no", "sales", "rendered", "change", "payment_type"]

DEFAULT_CONFIG = [
    "store_name=Ah Beng Vegetarian Food",
    "payment_types=Cash,PayNow,PayLah,PayWave",
    "cash_type=Cash",
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


# ---------------------------------------------------------------------------
# Section 3 - Calculations (plain functions, easy to test)
# ---------------------------------------------------------------------------

def money(value):
    """Show a number as dollars and cents, e.g. 4.5 -> '4.50'."""
    return f"{value:.2f}"


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
    """Print the paper-style receipt of the sale that was just saved."""
    if "last_receipt" not in st.session_state:
        return
    r = st.session_state["last_receipt"]

    st.success("Transaction saved. Receipt no. " + r["receipt_no"])
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

    suffix = "_" + str(input_round())
    left, right = st.columns([3, 2])

    with left:
        payment_type = st.selectbox("Payment type", payment_types, key="in_pay")
        is_cash = (payment_type == cash_type)

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

    change = calc_change(sales, rendered)

    with right:
        st.markdown("**Change due**")
        if change is None:
            st.markdown("## S$ --.--")
            st.warning("Cash received is less than the amount payable.")
        else:
            st.markdown("## S$ " + money(change))
            if not is_cash:
                st.caption("No change for " + payment_type + " payments.")

    st.divider()

    if st.button("Save transaction", type="primary"):
        if sales <= 0:
            st.error("Amount payable must be more than zero.")
        elif change is None:
            st.error("Cannot save: the cash received is not enough.")
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
# Section 8 - Main program
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Hawker Cash Register", page_icon="🧾")

    ensure_files()
    config = load_config()
    rows, bad = read_all()

    st.title(config.get("store_name", "My Store"))
    st.caption("Simple cash register - AN6100 Assignment Part 3")

    if bad > 0:
        st.warning(
            "Skipped " + str(bad) + " damaged line(s) in " + SALES_FILE
            + ". The rest of the data is still usable."
        )

    st.sidebar.title("Menu")
    screen = st.sidebar.radio(
        "Go to",
        ["Cash Register", "Daily Report", "Monthly Report"],
    )
    st.sidebar.divider()
    st.sidebar.caption("Transactions on file: " + str(len(rows)))

    if screen == "Cash Register":
        render_register(config, rows)
    elif screen == "Daily Report":
        render_day_report(rows)
    else:
        render_month_report(rows)


if __name__ == "__main__":
    main()
