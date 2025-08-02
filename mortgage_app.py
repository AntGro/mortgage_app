from datetime import date

import plotly.graph_objects as go
import streamlit as st


# --- Core simulation logic ---
def minimum_mortgage_repay_time_with_tracking(
        current_date: date,
        start_saving: float,
        mortgage_amount: float,
        monthly_payment: float,
        early_repay_percent: float,
        n_years_with_allowance: int,
        mortgage_interest_rate: float,
        monthly_revenue: float,
        savings_interest_rate: float,
        projection_years: float,
):
    """
    Simulates mortgage repayment over time and tracks monthly financial metrics.

    The function accounts for:
    - Fixed monthly mortgage repayments
    - Early repayment allowance (as a percentage of principal at the start of each year)
    - Unlimited early repayment after a specified number of years
    - Monthly revenue and leftover cash going into savings
    - Compound interest on both mortgage and savings

    Args:
        current_date (date): The start date of the simulation.
        start_saving (float): initial amount in savings .
        mortgage_amount (float): Total mortgage to be repaid .
        monthly_payment (float): Monthly repayment amount towards the mortgage .
        early_repay_percent (float): Annual early repayment cap (e.g., 0.10 for 10% of yearly-start principal).
        n_years_with_allowance (int): Number of years the early repayment cap applies.
            After this, 100% of the remaining principal can be repaid.
        mortgage_interest_rate (float): Annual mortgage interest rate (e.g., 0.0492 for 4.92%).
        monthly_revenue (float): Monthly available income .
        savings_interest_rate (float): Annual interest rate for savings (e.g., 0.03 for 3%).
        projection_years: track funds for that many years

    Returns:
        tuple:
            - int: Number of months required to fully repay the mortgage.
            - List[dict]: Monthly history of repayment progress, with each entry containing:
                - "date": datetime.date of the snapshot
                - "principal_remaining": remaining mortgage balance 
                - "savings": current savings balance 
                - "interest_paid": cumulative mortgage interest paid 
                - "total_paid": cumulative amount paid including principal and interest 
            - float: Total mortgage interest paid  over the course of repayment.
    """
    monthly_mortgage_rate = mortgage_interest_rate / 12
    monthly_savings_rate = savings_interest_rate / 12

    principal = mortgage_amount
    savings = start_saving
    month_count = 0
    total_interest_paid = 0.0
    history = []

    start_no_limit_allowance_date = date(current_date.year + n_years_with_allowance, current_date.month,
                                         current_date.day)
    start_date = date(current_date.year, current_date.month, current_date.day)
    yearly_principal_snapshot = principal
    early_repay_used = 0.0

    history.append({
        "date": current_date,
        "principal_remaining": principal,
        "savings": savings,
        "interest_paid": total_interest_paid,
        "total_paid": mortgage_amount - principal + total_interest_paid
    })

    n_years = 0
    time_passed = current_date - start_date
    while principal > 1e-5 or (time_passed.days // 365) < projection_years:
        interest_this_month = principal * monthly_mortgage_rate
        total_interest_paid += interest_this_month
        principal += interest_this_month

        savings *= (1 + monthly_savings_rate)

        actual_payment = min(monthly_payment, principal)
        principal -= actual_payment
        leftover = monthly_revenue - actual_payment

        if current_date.month == 1 and current_date.day == 1:
            yearly_principal_snapshot = principal
            early_repay_used = 0.0

        if current_date < start_no_limit_allowance_date:
            early_repay_limit = yearly_principal_snapshot * early_repay_percent - early_repay_used
        else:
            early_repay_limit = principal

        actual_early_repay = min(leftover + savings, early_repay_limit, principal)

        if actual_early_repay > leftover:
            from_savings = actual_early_repay - leftover
            savings = max(0.0, savings - from_savings)
            leftover = 0.0
        else:
            leftover -= actual_early_repay

        principal -= actual_early_repay
        early_repay_used += actual_early_repay
        savings += leftover

        month_count += 1
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)

        history.append({
            "date": current_date,
            "principal_remaining": principal,
            "savings": savings,
            "interest_paid": total_interest_paid,
            "total_paid": mortgage_amount - principal + total_interest_paid
        })
        time_passed = current_date - start_date
        if time_passed.days > 365 * 60:
            break

    return month_count, history, total_interest_paid


# --- Streamlit UI ---
st.set_page_config(page_title="Mortgage Simulator", layout="wide")
st.title("🏠 Mortgage Repayment Simulator")

with st.sidebar:
    st.header("Simulation Parameters")
    # Default date
    default_date = date(2025, 8, 1)

    # Let user pick a date
    start_date_input = st.date_input("Start Date (must be 1st of month)", default_date)

    if start_date_input.day != 1:
        st.error("Please select the 1st day of a month to proceed.")
        st.stop()  # prevent further execution

    start_date_ = start_date_input

    mortgage_amount_ = st.number_input("Mortgage Amount ", value=125_000, step=1_000)
    monthly_payment_ = st.number_input("Monthly Payment ", value=850, step=50)
    monthly_revenue_ = st.number_input("Monthly Available Revenue ", value=3000, step=100)
    start_saving_ = st.number_input("Initial Savings ", value=5000, step=500)

    # Early repayment toggles
    early_repay_enabled = st.checkbox("Enable Early Repayment", value=True)

    # Show early repayment settings, but freeze if not enabled
    unlimited_repay_from_start = st.checkbox(
        "Allow Full Early Repayment From Start", value=False, disabled=not early_repay_enabled
    )

    early_repay_percent_ = st.slider(
        "Early Repayment Allowance (%)",
        min_value=0.0, max_value=1.0, value=0.10, step=0.01,
        disabled=not early_repay_enabled or unlimited_repay_from_start
    )

    n_years_allowance_ = st.slider(
        "Years With Early Repay Limit", 0, 20, 4,
        disabled=not early_repay_enabled or unlimited_repay_from_start
    )

    # Assign logic depending on settings
    if not early_repay_enabled:
        early_repay_percent_ = 0.0
        n_years_allowance_ = 100  # effectively disables early repayment
    elif unlimited_repay_from_start:
        early_repay_percent_ = 1.0
        n_years_allowance_ = 0

    mortgage_interest_rate_ = st.slider("Mortgage Interest Rate (%)", 0.0, 10.0, 4.92, step=0.1) / 100
    savings_interest_rate_ = st.slider("Savings Interest Rate (%)", 0.0, 10.0, 3.0, step=0.1) / 100
    projection_years_ = st.slider("Track your money evolution on how many years", 0, 50, 25)

# Run simulation
months, history_, total_interest = minimum_mortgage_repay_time_with_tracking(
    current_date=start_date_,
    start_saving=start_saving_,
    mortgage_amount=mortgage_amount_,
    monthly_payment=monthly_payment_,
    early_repay_percent=early_repay_percent_,
    n_years_with_allowance=n_years_allowance_,
    mortgage_interest_rate=mortgage_interest_rate_,
    monthly_revenue=monthly_revenue_,
    savings_interest_rate=savings_interest_rate_,
    projection_years=projection_years_
)

# Extract data for plotting
dates = [entry["date"] for entry in history_]
principals = [entry["principal_remaining"] for entry in history_]
savings_vals = [entry["savings"] for entry in history_]
interests = [entry["interest_paid"] for entry in history_]

# Plotly figure
fig = go.Figure()
fig.add_trace(
    go.Scatter(x=dates, y=principals, mode="lines", name="📉 Principal Remaining", line=dict(width=3))
)
fig.add_trace(
    go.Scatter(x=dates, y=savings_vals, mode="lines", name="💰 Savings", line=dict(width=3))
)
fig.add_trace(
    go.Scatter(x=dates, y=interests, mode="lines", name="💸 Total Interest Paid", line=dict(width=3))
)

fig.update_layout(
    title="Mortgage Repayment Over Time",
    xaxis_title="Date",
    yaxis_title="Amount ",
    hovermode="x unified",
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

# Summary
repay_months = len([p for p in principals if p > 0])
years, rem_months = divmod(repay_months, 12)
col1, col2, col3 = st.columns(3)
col1.metric("⏳ Duration", f"{repay_months} months", f"{years}y {rem_months}m")
col2.metric("💸 Total Interest Paid", f"{total_interest:,.2f} £")
col3.metric("💰 Final Savings", f"{savings_vals[-1]:,.2f} £")

st.plotly_chart(fig, use_container_width=True)

# Optional: download history CSV
import pandas as pd

df = pd.DataFrame(history_)
csv = df.to_csv(index=False)
st.download_button("📥 Download Detailed History (CSV)", csv, "mortgage_history.csv", "text/csv")
