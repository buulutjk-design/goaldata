# analysis.py
import numpy as np
import logging

logger = logging.getLogger(__name__)

def monte_carlo_over25(lambda_h, lambda_a, n_sim=5000):
    home = np.random.poisson(lambda_h, size=n_sim)
    away = np.random.poisson(lambda_a, size=n_sim)
    totals = home + away
    p = float((totals > 2.5).mean())
    sd = float(totals.std())
    exp_home = float(home.mean())
    exp_away = float(away.mean())
    return {"p_over25": p, "sd": sd, "exp_home": exp_home, "exp_away": exp_away}

def ensemble_probability(stat_p, ml_p=None, w_stat=0.55, w_ml=0.45):
    if ml_p is None:
        return stat_p
    return w_stat * stat_p + w_ml * ml_p

def compute_confidence(p, sd, calibration_score=0.5, sd_max=3.0):
    sd_norm = min(sd / sd_max, 1.0)
    confidence = 0.6 * p + 0.3 * (1 - sd_norm) + 0.1 * calibration_score
    return float(confidence)

def evaluate_match(item, n_sim=5000):
    """
    item: dict with keys: lig, home, away, lambda_h, lambda_a, ml_p (optional), lig_gol_index (optional)
    returns: dict with p, sd, confidence, label
    """
    try:
        lambda_h = float(item.get("lambda_h", 1.2))
        lambda_a = float(item.get("lambda_a", 1.0))
        ml_p = item.get("ml_p")
        sim = monte_carlo_over25(lambda_h, lambda_a, n_sim=n_sim)
        stat_p = sim["p_over25"]
        sd = sim["sd"]
        p_final = ensemble_probability(stat_p, ml_p)
        calibration_score = item.get("calibration_score", 0.5)
        confidence = compute_confidence(p_final, sd, calibration_score)
        lig_boost = float(item.get("lig_gol_index", 0.0)) * 0.03
        confidence = min(confidence + lig_boost, 1.0)
        label = "YÜKSEK GÜVEN - GÜVENLİ" if p_final >= 0.70 and sd < 1.2 and confidence >= 0.68 else "ORTA/LOW GÜVEN"
        return {
            "lig": item.get("lig"),
            "home": item.get("home"),
            "away": item.get("away"),
            "p": p_final,
            "sd": sd,
            "confidence": confidence,
            "label": label,
            "exp_home": sim["exp_home"],
            "exp_away": sim["exp_away"]
        }
    except Exception:
        logger.exception("evaluate_match error")
        return None
