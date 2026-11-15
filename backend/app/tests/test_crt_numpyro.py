import numpy as np
import pytest
from analysis.crt.full_model import _log_likelihood, simulate_full_data
from analysis.crt.numpyro_model import (
    NumpyroUnavailableError,
    NutsConfig,
    _make_model,
    fit_nuts,
    numpyro_available,
    run_nuts_smoke,
)

requires_numpyro = pytest.mark.skipif(
    not numpyro_available(), reason="NumPyro/JAX is an optional extra"
)


@requires_numpyro
def test_nuts_likelihood_matches_the_numpy_model() -> None:
    from numpyro.infer.util import log_density

    data, _ = simulate_full_data("M0", n_participants=2, n_trials=3, seed=70)
    group = {name: 0.0 for name in ("alpha_d", "alpha_pi", "alpha_b", "gamma_v", "gamma_c", "delta_b", "delta_dual")}
    group.update(alpha_d=0.7, alpha_pi=0.4, alpha_b=-0.2)
    sigma = np.array([0.4, 0.3, 0.5])
    effects = np.array([[0.1, -0.2, 0.05], [-0.1, 0.2, -0.05]])
    z = effects / sigma
    params = {
        **group,
        "sigma_d": sigma[0],
        "sigma_pi": sigma[1],
        "sigma_b": sigma[2],
        "z_d": z[:, 0],
        "z_pi": z[:, 1],
        "z_b": z[:, 2],
    }
    _, trace = log_density(_make_model(data, "M0"), (), {}, params)
    jax_likelihood = float(trace["log_likelihood"]["value"])
    numpy_likelihood = _log_likelihood(data, group, effects)
    assert np.isclose(jax_likelihood, numpy_likelihood, atol=1e-5)


@requires_numpyro
def test_nuts_smoke_runs_for_confirmatory_models() -> None:
    data, _ = simulate_full_data("M0", n_participants=2, n_trials=5, seed=71)
    result = run_nuts_smoke(
        data,
        model="M0",
        config=NutsConfig(chains=1, warmup=20, draws=20, max_tree_depth=4),
    )
    assert result["decision"] in {"CRT_NUTS_SMOKE_PASS", "CRT_NUTS_SMOKE_REVIEW"}
    assert "alpha_d" in result["sample_keys"]
    assert result["divergences"] is not None


@requires_numpyro
def test_nuts_fit_returns_finite_posterior_draws() -> None:
    data, _ = simulate_full_data("M6", n_participants=2, n_trials=5, seed=72)
    fit = fit_nuts(
        data,
        model="M6",
        config=NutsConfig(chains=1, warmup=20, draws=20, max_tree_depth=4),
    )
    assert "gamma_v" in fit["samples"]
    assert np.all(np.isfinite(fit["samples"]["alpha_d"]))


def test_nuts_rejects_unavailable_backend_explicitly() -> None:
    if numpyro_available():
        pytest.skip("backend is actually installed in this environment")
    with pytest.raises(NumpyroUnavailableError):
        fit_nuts(
            simulate_full_data("M0", n_participants=2, n_trials=5, seed=73)[0],
            model="M0",
            config=NutsConfig(chains=1, warmup=5, draws=5),
        )
