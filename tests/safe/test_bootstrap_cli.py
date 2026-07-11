from database.system_bootstrap_manager import (
    BootstrapStep,
    CRSSystemBootstrapManager,
    build_argument_parser,
)


def test_help_parser_is_non_mutating():
    parser = build_argument_parser()
    assert parser.prog
    help_text = parser.format_help()
    assert "--include-site-migrations" not in help_text
    assert "always excluded" in help_text


def test_generic_bootstrap_excludes_p15_site_migration():
    manager = CRSSystemBootstrapManager(
        seed_users=False,
        verbose=False,
    )
    names = [step.name for step in manager._steps()]
    assert "P15 phase scope/data migration" not in names


def test_optional_failure_is_not_reported_as_success(tmp_path, monkeypatch):
    manager = CRSSystemBootstrapManager(
        seed_users=False,
        verbose=False,
    )
    manager.report_dir = tmp_path
    manager._steps = lambda: [
        BootstrapStep(
            "test",
            "optional failure",
            lambda: (_ for _ in ()).throw(RuntimeError("expected")),
            required=False,
        )
    ]
    monkeypatch.setattr(
        manager,
        "_write_bootstrap_history",
        lambda **kwargs: None,
    )

    result = manager.run()

    assert result["status"] == "WARNING"
    assert result["failures"][0]["error"] == "expected"
