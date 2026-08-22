"""Brinson performance attribution with BHB / Fachler and multi-period linking."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class SectorAttr:
    sector: str
    w_p: float
    w_b: float
    r_p: float
    r_b: float
    allocation: float
    selection: float
    interaction: float
    total: float
    weight_active: float


@dataclass
class BrinsonReport:
    method: str
    portfolio_return: float
    benchmark_return: float
    active_return: float
    allocation: float
    selection: float
    interaction: float
    residual: float
    herfindahl_portfolio: float
    herfindahl_benchmark: float
    top_contributors: list[str]
    verdict: str
    score: float
    gates: dict[str, bool]
    sectors: list[SectorAttr]
    linked: dict[str, float] | None
    notes: list[str]


def _validate(df: pd.DataFrame, weight_tolerance: float = 0.02) -> pd.DataFrame:
    need = {"sector", "w_p", "w_b", "r_p", "r_b"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    out = df.copy()
    out["sector"] = out["sector"].astype(str)
    if out["sector"].duplicated().any():
        duplicates = sorted(out.loc[out["sector"].duplicated(), "sector"].unique())
        raise ValueError(f"duplicate sectors: {duplicates}")
    for c in ("w_p", "w_b", "r_p", "r_b"):
        out[c] = out[c].astype(float)
        if not np.isfinite(out[c]).all():
            raise ValueError(f"column {c} contains non-finite values")
    wp_sum, wb_sum = float(out["w_p"].sum()), float(out["w_b"].sum())
    if abs(wp_sum - 1.0) > weight_tolerance or abs(wb_sum - 1.0) > weight_tolerance:
        raise ValueError(
            f"portfolio and benchmark weights must sum to 1±{weight_tolerance}; "
            f"got {wp_sum:.6f}, {wb_sum:.6f}"
        )
    return out


def _single_period(df: pd.DataFrame, method: str = "fachler") -> BrinsonReport:
    method = method.lower()
    if method not in {"fachler", "bhb"}:
        raise ValueError("method must be 'fachler' or 'bhb'")

    r_b_total = float((df["w_b"] * df["r_b"]).sum())
    r_p_total = float((df["w_p"] * df["r_p"]).sum())
    sectors: list[SectorAttr] = []
    alloc = sel = inter = 0.0

    for _, row in df.iterrows():
        if method == "fachler":
            a = (row["w_p"] - row["w_b"]) * (row["r_b"] - r_b_total)
        else:  # Brinson-Hood-Beebower
            a = (row["w_p"] - row["w_b"]) * row["r_b"]
        s = row["w_b"] * (row["r_p"] - row["r_b"])
        i = (row["w_p"] - row["w_b"]) * (row["r_p"] - row["r_b"])
        sectors.append(
            SectorAttr(
                sector=str(row["sector"]),
                w_p=float(row["w_p"]),
                w_b=float(row["w_b"]),
                r_p=float(row["r_p"]),
                r_b=float(row["r_b"]),
                allocation=float(a),
                selection=float(s),
                interaction=float(i),
                total=float(a + s + i),
                weight_active=float(row["w_p"] - row["w_b"]),
            )
        )
        alloc += a
        sel += s
        inter += i

    active = r_p_total - r_b_total
    explained = alloc + sel + inter
    residual = active - explained
    hhi_p = float((df["w_p"] ** 2).sum())
    hhi_b = float((df["w_b"] ** 2).sum())
    top = sorted(sectors, key=lambda x: abs(x.total), reverse=True)[:3]
    top_names = [f"{s.sector}:{s.total:.4%}" for s in top]

    drivers = {"ALLOCATION": abs(alloc), "SELECTION": abs(sel), "INTERACTION": abs(inter)}
    verdict = max(drivers, key=drivers.get)

    wp_sum, wb_sum = float(df["w_p"].sum()), float(df["w_b"].sum())
    gates = {
        "weights_sum_near_1": bool(abs(wp_sum - 1) < 0.02 and abs(wb_sum - 1) < 0.02),
        "abs_residual<1bp": bool(abs(residual) < 1e-4),
        "active_return_explained": bool(abs(explained - active) < 1e-4),
        "has_dispersion": bool(
            float(df["r_b"].std(ddof=0)) > 0 or float(df["r_p"].std(ddof=0)) > 0
        ),
    }
    score = float(np.mean(list(gates.values())))

    return BrinsonReport(
        method=method,
        portfolio_return=r_p_total,
        benchmark_return=r_b_total,
        active_return=active,
        allocation=float(alloc),
        selection=float(sel),
        interaction=float(inter),
        residual=float(residual),
        herfindahl_portfolio=hhi_p,
        herfindahl_benchmark=hhi_b,
        top_contributors=top_names,
        verdict=verdict,
        score=score,
        gates=gates,
        sectors=sectors,
        linked=None,
        notes=[
            "Fachler allocation uses (w_p-w_b)*(r_b - R_b); BHB uses (w_p-w_b)*r_b.",
            "Interaction = active weight × active return within sector.",
            "Herfindahl = sum(w^2); higher means more concentrated.",
        ],
    )


def brinson_fachler(df: pd.DataFrame) -> BrinsonReport:
    return _single_period(_validate(df), method="fachler")


def brinson_bhb(df: pd.DataFrame) -> BrinsonReport:
    return _single_period(_validate(df), method="bhb")


def brinson_attribution(df: pd.DataFrame, method: str = "fachler") -> BrinsonReport:
    return _single_period(_validate(df), method=method)


def carino_link(period_reports: list[BrinsonReport]) -> dict[str, float]:
    """Carino (1999) smoothing to link multi-period arithmetic effects to geometric active return."""
    if not period_reports:
        raise ValueError("period_reports empty")
    rp = np.array([r.portfolio_return for r in period_reports], dtype=float)
    rb = np.array([r.benchmark_return for r in period_reports], dtype=float)
    if np.any(rp <= -1) or np.any(rb <= -1):
        raise ValueError("Carino linking requires all period returns > -100%")
    rp_g = float(np.prod(1 + rp) - 1)
    rb_g = float(np.prod(1 + rb) - 1)
    active_g = rp_g - rb_g
    # Carino factor per period
    eps = 1e-12
    factors = []
    for r_p, r_b in zip(rp, rb):
        if abs(r_p - r_b) < eps:
            # limit as r_p -> r_b of log((1+rp)/(1+rb))/(rp-rb) = 1/(1+rb)
            factors.append(1.0 / (1.0 + r_b))
        else:
            factors.append(np.log((1 + r_p) / (1 + r_b)) / (r_p - r_b))
    # rescale so sum(factor_i * active_i) = geometric active
    active_arith = rp - rb
    scale = active_g / np.sum(np.array(factors) * active_arith) if abs(np.sum(np.array(factors) * active_arith)) > eps else 1.0
    c_factors = np.array(factors) * scale

    linked = {"portfolio_return_geometric": rp_g, "benchmark_return_geometric": rb_g, "active_return_geometric": active_g}
    for key in ("allocation", "selection", "interaction"):
        vals = np.array([getattr(r, key) for r in period_reports], dtype=float)
        linked[f"{key}_linked"] = float(np.sum(c_factors * vals))
    linked["residual_linked"] = float(
        active_g - linked["allocation_linked"] - linked["selection_linked"] - linked["interaction_linked"]
    )
    return linked


def multiperiod_brinson(frames: list[pd.DataFrame], method: str = "fachler") -> BrinsonReport:
    reports = [brinson_attribution(f, method=method) for f in frames]
    base = reports[-1]
    linked = carino_link(reports)
    # Use geometric returns and linked effects in the headline fields so the
    # report is internally consistent; sector detail remains the latest period.
    avg = BrinsonReport(
        method=f"{method}+carino",
        portfolio_return=linked["portfolio_return_geometric"],
        benchmark_return=linked["benchmark_return_geometric"],
        active_return=linked["active_return_geometric"],
        allocation=linked["allocation_linked"],
        selection=linked["selection_linked"],
        interaction=linked["interaction_linked"],
        residual=linked["residual_linked"],
        herfindahl_portfolio=base.herfindahl_portfolio,
        herfindahl_benchmark=base.herfindahl_benchmark,
        top_contributors=base.top_contributors,
        verdict=base.verdict,
        score=float(np.mean([r.score for r in reports])),
        gates=base.gates,
        sectors=base.sectors,
        linked=linked,
        notes=base.notes
        + [
            f"Multi-period: {len(reports)} periods; headline returns/effects are Carino-linked.",
            "Sector rows and concentration are the latest-period snapshot.",
        ],
    )
    # Dominant driver from linked absolute values
    drivers = {
        "ALLOCATION": abs(linked["allocation_linked"]),
        "SELECTION": abs(linked["selection_linked"]),
        "INTERACTION": abs(linked["interaction_linked"]),
    }
    avg.verdict = max(drivers, key=drivers.get)
    return avg


def render_text(report: BrinsonReport) -> str:
    lines = [
        "=== Brinson Performance Attribution ===",
        f"method={report.method}",
        f"R_p={report.portfolio_return:.4%}  R_b={report.benchmark_return:.4%}  "
        f"active={report.active_return:.4%}",
        f"allocation={report.allocation:.4%}  selection={report.selection:.4%}  "
        f"interaction={report.interaction:.4%}  residual={report.residual:.4%}",
        f"HHI_p={report.herfindahl_portfolio:.3f} HHI_b={report.herfindahl_benchmark:.3f}",
        f"top_contributors={', '.join(report.top_contributors)}",
        f"quality_score={report.score:.0%}  dominant_driver={report.verdict}",
        "",
        "gates:",
    ]
    for k, v in report.gates.items():
        lines.append(f"  [{'PASS' if v else 'FAIL'}] {k}")
    if report.linked:
        lines += ["", "Carino-linked multi-period:"]
        for k, v in report.linked.items():
            lines.append(f"  {k}={v:.4%}" if "return" in k or k.endswith("_linked") else f"  {k}={v}")
    lines += ["", "sector | w_act | alloc | select | interact | total"]
    for s in sorted(report.sectors, key=lambda x: abs(x.total), reverse=True):
        lines.append(
            f"{s.sector:10s} | {s.weight_active:6.2%} | {s.allocation:7.4%} | {s.selection:7.4%} | "
            f"{s.interaction:8.4%} | {s.total:7.4%}"
        )
    lines += ["", "notes:"]
    lines += [f"- {n}" for n in report.notes]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Brinson performance attribution")
    parser.add_argument("--input", required=True, help="CSV with sector,w_p,w_b,r_p,r_b")
    parser.add_argument("--method", choices=["fachler", "bhb"], default="fachler")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    df = pd.read_csv(args.input)
    report = brinson_attribution(df, method=args.method)
    print(render_text(report))
    if args.out:
        args.out.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
