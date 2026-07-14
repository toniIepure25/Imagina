"""v007: Add normalized objective measurement and analysis provenance tables."""

VERSION = 7
DESCRIPTION = "Persist objective psychophysics and analysis provenance"


async def upgrade(db) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS objective_task_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            participant_id TEXT NOT NULL,
            period INTEGER NOT NULL,
            condition TEXT NOT NULL,
            task_family TEXT NOT NULL,
            block_index INTEGER NOT NULL,
            schedule_hash TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(session_id, task_family, block_index)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS objective_trial_specs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_id INTEGER NOT NULL REFERENCES objective_task_blocks(id),
            trial_index INTEGER NOT NULL,
            task_family TEXT NOT NULL,
            task_version TEXT NOT NULL DEFAULT '1.0',
            target_orientation REAL,
            target_hue REAL,
            target_sf REAL,
            target_pos_x REAL,
            target_pos_y REAL,
            target_size REAL,
            transformation_type TEXT DEFAULT 'none',
            transformation_magnitude REAL DEFAULT 0.0,
            delay_s REAL DEFAULT 0.0,
            difficulty REAL DEFAULT 1.0,
            is_perceptual_control INTEGER DEFAULT 0,
            schedule_position INTEGER,
            UNIQUE(block_id, trial_index)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS objective_trial_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trial_spec_id INTEGER NOT NULL REFERENCES objective_trial_specs(id),
            response_orientation REAL,
            response_hue REAL,
            response_sf REAL,
            response_pos_x REAL,
            response_pos_y REAL,
            response_size REAL,
            latency_ms REAL,
            confidence INTEGER,
            vividness INTEGER,
            effort INTEGER,
            response_provider TEXT NOT NULL DEFAULT 'synthetic',
            response_provider_version TEXT,
            recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(trial_spec_id)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS objective_trial_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            response_id INTEGER NOT NULL REFERENCES objective_trial_responses(id),
            orientation_error REAL,
            hue_error REAL,
            sf_error REAL,
            position_error REAL,
            size_error REAL,
            composite_error REAL,
            scoring_version TEXT NOT NULL DEFAULT '1.0',
            endpoint_registry_hash TEXT,
            invalidity_flags TEXT DEFAULT '[]',
            UNIQUE(response_id)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS objective_calibrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT NOT NULL,
            participant_id TEXT NOT NULL,
            task_family TEXT NOT NULL,
            calibration_method TEXT DEFAULT 'transformed_up_down',
            threshold REAL,
            n_trials INTEGER,
            converged INTEGER,
            calibration_hash TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(study_id, participant_id, task_family)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS objective_endpoint_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT NOT NULL,
            endpoint_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            role TEXT NOT NULL,
            direction TEXT NOT NULL,
            weight REAL,
            valid_range_min REAL,
            valid_range_max REAL,
            registry_hash TEXT NOT NULL,
            registry_version TEXT NOT NULL DEFAULT '1.0',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS analysis_specifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT NOT NULL,
            spec_type TEXT NOT NULL DEFAULT 'confirmatory',
            formula TEXT NOT NULL,
            estimand_id TEXT NOT NULL,
            model_version TEXT NOT NULL,
            spec_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS analysis_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spec_id INTEGER NOT NULL REFERENCES analysis_specifications(id),
            status TEXT NOT NULL DEFAULT 'queued',
            started_at TEXT,
            completed_at TEXT,
            error_message TEXT,
            seed INTEGER,
            mode TEXT DEFAULT 'unit'
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL REFERENCES analysis_runs(id),
            estimator_type TEXT NOT NULL,
            effect_estimate REAL,
            standard_error REAL,
            ci_lower REAL,
            ci_upper REAL,
            p_value REAL,
            converged INTEGER,
            is_fallback INTEGER,
            inference_valid INTEGER,
            n_participants INTEGER,
            n_trials INTEGER,
            result_json TEXT,
            UNIQUE(run_id, estimator_type)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS simulation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT,
            scenario_id TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'unit',
            n_iterations INTEGER NOT NULL,
            n_participants INTEGER NOT NULL,
            base_seed INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            started_at TEXT,
            completed_at TEXT,
            checkpoint_iteration INTEGER DEFAULT 0,
            error_message TEXT
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS simulation_replicates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL REFERENCES simulation_runs(id),
            replicate_index INTEGER NOT NULL,
            seed INTEGER NOT NULL,
            effect_estimate REAL,
            p_value REAL,
            converged INTEGER,
            is_fallback INTEGER,
            ci_lower REAL,
            ci_upper REAL,
            UNIQUE(run_id, replicate_index)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS simulation_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL REFERENCES simulation_runs(id),
            power REAL,
            type_i_error REAL,
            coverage REAL,
            bias REAL,
            rmse REAL,
            convergence_rate REAL,
            fallback_rate REAL,
            valid_inference_rate REAL,
            nc_fp_rate REAL,
            oracle_effect REAL,
            oracle_se REAL,
            summary_json TEXT,
            UNIQUE(run_id)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS oracle_estimands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT,
            scenario_id TEXT NOT NULL,
            contrast_id TEXT NOT NULL,
            oracle_effect REAL NOT NULL,
            oracle_se REAL NOT NULL,
            n_agents INTEGER NOT NULL,
            oracle_seed INTEGER NOT NULL,
            oracle_version TEXT NOT NULL DEFAULT '1.0',
            endpoint_id TEXT NOT NULL,
            spec_hash TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.commit()
