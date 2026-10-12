"""Arithmetic on PUBLISHED summary statistics for the Cboe PutWrite index (PUT).

Run from the repo root:
    PYTHONPATH=. python3 scripts/run_published_stats_arithmetic.py

The inputs below are not data from this repo. They are summary figures reported
in the sources listed in ledger/claims.md (rows A5 and A5b), reproduced by
web-search summaries, and the risk-free rate in the second block is an
ASSUMPTION. The point is to show how much statistical weight a 30 to 37 year
Sharpe-ratio advantage carries. The test for a difference of two correlated
Sharpe ratios follows Jobson and Korkie (1981) as corrected by Memmel (2003); the
correlation between PUT and the S&P 500 is not given in the sources, so a range
is shown.
"""
import numpy as np


def sr_diff_t(sr1, sr2, years, rho):
    var = (1.0 / years) * (2.0 * (1.0 - rho) + 0.5 * (sr1 ** 2 + sr2 ** 2 - 2.0 * sr1 * sr2 * rho ** 2))
    return (sr1 - sr2) / np.sqrt(var)


def show(label, sr1, sr2, years):
    print(f"{label}: SR_put={sr1:.2f} SR_spx={sr2:.2f} diff={sr1 - sr2:.2f} over {years:.1f} years")
    for rho in [0.80, 0.85, 0.90, 0.95]:
        print(f"    assumed correlation {rho:.2f}: t(diff) = {sr_diff_t(sr1, sr2, years, rho):.2f}")


def capm_alpha(r_put, r_mkt, beta, rf, sd_put, sd_mkt, years):
    """Linear CAPM alpha of PUT and its iid t-statistic from summary figures (all inputs in decimals)."""
    alpha = (r_put - rf) - beta * (r_mkt - rf)
    resid_sd = np.sqrt(max(sd_put ** 2 - (beta * sd_mkt) ** 2, 0.0))
    se = resid_sd / np.sqrt(years)
    return alpha, resid_sd, alpha / se


def main():
    print("Block 1: Sharpe ratios as published (gross), Jun 1986 to Dec 2015, about 29.5 years")
    show("  2015 window", 0.67, 0.47, 29.5)

    print("\nBlock 2: Cboe figures to Aug 2023 (annual return, annual std), risk-free rate ASSUMED")
    for rf in [0.025, 0.034, 0.045]:
        sr_put = (0.0940 - rf) / 0.1026
        sr_spx = (0.0991 - rf) / 0.1538
        show(f"  rf={rf:.3f}", sr_put, sr_spx, 37.1)
    block3()


def block3():
    print("\nBlock 3: implied linear CAPM alpha of PUT from summary figures (illustrative, gross of costs)")
    print("  inputs: PUT 10.0% and S&P 500 total return 10.1% a year, beta 0.55 (1988 to 2018 figures reported in a search summary")
    print("  attributed to Russell Investments); return volatilities 10.1% and 15.3% (CXO, 1986 to 2015); 31 years; risk-free ASSUMED.")
    for rf in [0.025, 0.034, 0.045]:
        a, rsd, t = capm_alpha(0.100, 0.101, 0.55, rf, 0.101, 0.153, 31.0)
        print(f"  rf={rf:.3f}: alpha = {a:.2%} a year, residual vol = {rsd:.1%}, iid t = {t:.1f}")
    print("  Caveats: windows are mixed; the iid t ignores autocorrelation; a LINEAR benchmark is the wrong model for a short-gamma payoff")
    print("  (Broadie, Chernov, Johannes 2009), so the alpha is better read as the price of crash exposure than as free excess return;")
    print("  all of it is before trading costs and before any fund fee (the WisdomTree PUT fund launched at a 0.38% expense ratio).")


if __name__ == "__main__":
    main()
