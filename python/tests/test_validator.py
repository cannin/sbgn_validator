from pathlib import Path

import concurrent.futures

import pytest

from sbgn_validator import SchematronValidator, rules_info, validate_sbgn

ROOT = Path(__file__).parents[2]


def test_compiles_all_authoritative_schemas() -> None:
    for language in ("af", "er", "pd"):
        SchematronValidator(ROOT / f"validation/rules/sbgn_{language}.sch")


def test_pd_fixture_reports_expected_rule() -> None:
    validator = SchematronValidator(ROOT / "validation/rules/sbgn_pd.sch")
    result = validator.validate(ROOT / "tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn")
    assert "pd10110" in {finding["id"] for finding in result["findings"]}


def test_builtin_rules_detect_language_and_report_digest() -> None:
    document = ROOT / "tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn"
    result = validate_sbgn(document)
    canonical = validate_sbgn(document, ROOT / "validation/rules/sbgn_pd.sch")
    assert result["schema"] == "sbgn_pd.sch"
    assert "pd10110" in {finding["id"] for finding in result["findings"]}
    assert result == canonical
    assert rules_info()["ruleset_digest"].startswith("sha256:")


def test_legacy_policy_runs_semantic_rules() -> None:
    schema = ROOT / "validation/rules/sbgn_pd.sch"
    document = ROOT / "tests/examples/go_mf_conflicts.sbgn"
    report = SchematronValidator(schema).validate(document)
    assert report["valid"] is False
    assert {finding["id"] for finding in report["findings"]} == {"sbgn-namespace-0.3"}
    compatible = validate_sbgn(
        document,
        schema,
        allow_sbgnml_0_2=True,
    )
    assert compatible["phase"] == "basic-allow-sbgnml-0.2"
    assert compatible["valid"] is False
    assert {"pd10102", "pd10132", "pd10141"} <= {
        finding["id"] for finding in compatible["findings"]
    }
    expected_test = (
        "$port-class='process' or $port-class='omitted process' or "
        "$port-class='uncertain process' or $port-class='association' or "
        "$port-class='dissociation' or $port-class='phenotype'"
    )
    assert {
        finding["test"] for finding in compatible["findings"] if finding["id"] == "pd10102"
    } == {expected_test}


@pytest.mark.parametrize(
    "relative_path",
    [
        "tests/examples/go_mf_conflicts.sbgn",
        "tests/fixtures/compatibility/missing-namespace.sbgn",
        "tests/fixtures/compatibility/unrelated-namespace.sbgn",
        "tests/fixtures/compatibility/future-namespace.sbgn",
    ],
)
def test_namespace_policy_rejects_unaccepted_namespaces(relative_path: str) -> None:
    with pytest.raises(ValueError, match="^SBGN_NAMESPACE_ERROR:"):
        validate_sbgn(ROOT / relative_path)
    if relative_path != "tests/examples/go_mf_conflicts.sbgn":
        with pytest.raises(ValueError, match="^SBGN_NAMESPACE_ERROR:"):
            validate_sbgn(ROOT / relative_path, allow_sbgnml_0_2=True)


def test_legacy_policy_supports_all_languages_and_custom_rules() -> None:
    cases = {
        "af": "tests/fixtures/compatibility/sbgnml-0.2-af-valid.sbgn",
        "er": "tests/fixtures/compatibility/sbgnml-0.2-er-valid.sbgn",
        "pd": "tests/fixtures/compatibility/sbgnml-0.2-pd-valid.sbgn",
    }
    for language, relative_path in cases.items():
        document = ROOT / relative_path
        assert validate_sbgn(document, allow_sbgnml_0_2=True)["valid"] is True
        assert validate_sbgn(
            document,
            ROOT / f"validation/rules/sbgn_{language}.sch",
            allow_sbgnml_0_2=True,
        )["valid"] is True


def test_namespace_policy_has_no_sequential_or_concurrent_contamination() -> None:
    legacy = ROOT / "tests/fixtures/compatibility/sbgnml-0.2-pd-valid.sbgn"
    current = ROOT / "tests/fixtures/error-test-files/PD/pd10110-pass.sbgn"
    paths = [legacy, current, legacy, current]

    def validate(path: Path) -> bool:
        return bool(validate_sbgn(path, allow_sbgnml_0_2=True)["valid"])

    assert [validate(path) for path in paths] == [True, True, True, True]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        assert list(executor.map(validate, paths)) == [True, True, True, True]


def test_custom_schema_rebinds_only_the_sbgn_prefix() -> None:
    document = ROOT / "tests/fixtures/compatibility/custom-sbgnml-0.2.sbgn"
    schema = ROOT / "tests/fixtures/compatibility/custom-sbgn.sch"
    assert validate_sbgn(
        document,
        schema,
        allow_sbgnml_0_2=True,
    )["valid"] is True
    with pytest.raises(ValueError, match="^SCHEMATRON_NAMESPACE_ERROR:"):
        validate_sbgn(
            document,
            ROOT / "tests/fixtures/compatibility/custom-unsafe-sbgn.sch",
            allow_sbgnml_0_2=True,
        )
