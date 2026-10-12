"""Bayesian evidence accumulation for per-field, per-glyph-type priors.

After each run, posterior means are stored in the evidence DB.
Next run reads them as priors, producing sharper scores over time.

Formula:
    alpha = max(alpha_min, 1.0 / (1.0 + n * decay))
    posterior = alpha * likelihood + (1 - alpha) * prior_mean
    posterior_var = (alpha * likelihood + (1 - alpha) * prior_mean)^2
                    + alpha * (1 - alpha) * (likelihood - prior_mean)^2

Where:
    likelihood = conf_visual * p_prior * s_spatial * c_consistency
    prior_mean  = historical mean composite score for (field_key, glyph_type)
    n           = number of observations for that (field_key, glyph_type)
    decay       = how fast prior trust grows (default 0.1 per observation)
    alpha_min   = floor on alpha so prior never fully dominates (default 0.2)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldPrior:
    """Running Bayesian state for one (field_key, glyph_type) pair."""
    field_key: str
    glyph_type: str
    n: int = 0
    mean: float = 0.5
    var: float = 0.25

    def update(self, score: float) -> None:
        """Online update: running mean and variance (Welford)."""
        self.n += 1
        delta = score - self.mean
        self.mean += delta / self.n
        delta2 = score - self.mean
        self.var = ((self.n - 1) * self.var + delta * delta2) / self.n

    def to_dict(self) -> dict:
        return {
            "field_key": self.field_key,
            "glyph_type": self.glyph_type,
            "n": self.n,
            "mean": round(self.mean, 6),
            "std": round(math.sqrt(self.var), 6),
        }


@dataclass
class BayesianConfig:
    decay: float = 0.1
    alpha_min: float = 0.2
    prior_default: float = 0.5


class BayesianScorer:
    """Accumulates evidence across runs and computes Bayesian posteriors."""

    def __init__(self, config: BayesianConfig | None = None):
        self.config = config or BayesianConfig()
        self._priors: dict[tuple[str, str], FieldPrior] = {}

    def load_from_db(self, rows: list[dict]) -> None:
        """Hydrate priors from evidence_log rows (previous runs)."""
        buckets: dict[tuple[str, str], list[float]] = {}
        for row in rows:
            key = (row.get("field_key", ""), row.get("glyph_type", ""))
            score = row.get("score", 0.0)
            if score > 0.0:
                buckets.setdefault(key, []).append(score)
        for key, scores in buckets.items():
            prior = FieldPrior(field_key=key[0], glyph_type=key[1])
            for s in scores:
                prior.update(s)
            self._priors[key] = prior

    def load_from_prior_table(self, rows: list[dict]) -> None:
        """Hydrate from dedicated field_priors table (serialized FieldPrior)."""
        for row in rows:
            key = (row["field_key"], row["glyph_type"])
            self._priors[key] = FieldPrior(
                field_key=row["field_key"],
                glyph_type=row["glyph_type"],
                n=row["n"],
                mean=row["mean"],
                var=row["var"],
            )

    def _get_prior(self, field_key: str, glyph_type: str) -> FieldPrior:
        key = (field_key, glyph_type)
        if key not in self._priors:
            self._priors[key] = FieldPrior(field_key=field_key, glyph_type=glyph_type)
        return self._priors[key]

    def score(
        self,
        field_key: str,
        glyph_type: str,
        conf_visual: float,
        p_prior: float,
        s_spatial: float,
        c_consistency: float,
    ) -> dict[str, Any]:
        """Compute Bayesian posterior for a single cell.

        Returns:
            {
                "posterior": float,        # final composite score [0, 1]
                "prior_mean": float,       # historical mean before this observation
                "prior_n": int,            # observation count before this run
                "alpha": float,            # learning rate used
                "likelihood": float,       # raw product term
                "requires_human": bool,    # posterior < threshold
                "route": str,              # "auto" or "low_confidence"
                "updated_prior": FieldPrior,  # state after incorporating this observation
            }
        """
        cfg = self.config
        prior = self._get_prior(field_key, glyph_type)

        likelihood = max(0.0, min(1.0, conf_visual)) * max(0.0, min(1.0, p_prior)) \
                     * max(0.0, min(1.0, s_spatial)) * max(0.0, min(1.0, c_consistency))

        alpha = max(cfg.alpha_min, 1.0 / (1.0 + prior.n * cfg.decay))
        posterior = alpha * likelihood + (1.0 - alpha) * prior.mean

        prior_mean_before = prior.mean
        prior_n_before = prior.n
        prior.update(likelihood)

        threshold = 0.88
        return {
            "posterior": round(posterior, 6),
            "prior_mean": round(prior_mean_before, 6),
            "prior_n": prior_n_before,
            "alpha": round(alpha, 6),
            "likelihood": round(likelihood, 6),
            "requires_human": posterior < threshold,
            "route": "auto" if posterior >= threshold else "low_confidence",
            "updated_prior": prior,
        }

    def get_priors_snapshot(self) -> list[dict]:
        return [p.to_dict() for p in self._priors.values()]
