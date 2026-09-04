use sbgn_validator::{NamespacePolicy, Validator};
use std::path::PathBuf;

#[test]
fn compiles_all_authoritative_schemas() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..");
    for language in ["af", "er", "pd"] {
        let path = root.join(format!("validation/rules/sbgn_{language}.sch"));
        Validator::compile(&path, "basic").unwrap();
    }
}

#[test]
fn legacy_policy_runs_semantic_rules() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..");
    let schema = root.join("validation/rules/sbgn_pd.sch");
    let document = root.join("tests/examples/go_mf_conflicts.sbgn");
    let report = Validator::compile(&schema, "basic")
        .expect("schema should compile")
        .validate(&document)
        .expect("Schematron should report the mismatch");
    let value = serde_json::to_value(&report).expect("report should serialize");
    assert_eq!(value["valid"], false);
    assert_eq!(value["findings"][0]["id"], "sbgn-namespace-0.3");
    let override_report = Validator::compile_for_document(
        &schema,
        &document,
        "basic",
        NamespacePolicy::AllowSbgnml02,
    )
    .expect("legacy policy should compile")
    .validate(&document)
    .expect("legacy policy should validate");
    let value = serde_json::to_value(override_report).expect("report should serialize");
    assert_eq!(value["valid"], false);
    let ids: Vec<_> = value["findings"]
        .as_array()
        .unwrap()
        .iter()
        .map(|finding| finding["id"].as_str().unwrap())
        .collect();
    assert!(ids.contains(&"pd10102"));
    assert!(ids.contains(&"pd10132"));
    assert!(ids.contains(&"pd10141"));
}

#[test]
fn builtin_rules_detect_language_and_report_digest() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..");
    let document = root.join("tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn");
    let validator = Validator::builtin_for_document(&document, "basic").unwrap();
    let report = validator.validate(&document).unwrap();
    let value = serde_json::to_value(report).unwrap();
    assert_eq!(value["valid"], false);
    let canonical = Validator::compile(&root.join("validation/rules/sbgn_pd.sch"), "basic")
        .unwrap()
        .validate(&document)
        .unwrap();
    assert_eq!(value, serde_json::to_value(canonical).unwrap());
    assert!(
        sbgn_validator::rules::rules_info()
            .unwrap()
            .ruleset_digest
            .starts_with("sha256:")
    );
}

#[test]
fn namespace_policy_rejects_unaccepted_namespaces() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..");
    for relative in [
        "tests/examples/go_mf_conflicts.sbgn",
        "tests/fixtures/compatibility/missing-namespace.sbgn",
        "tests/fixtures/compatibility/unrelated-namespace.sbgn",
        "tests/fixtures/compatibility/future-namespace.sbgn",
    ] {
        let path = root.join(relative);
        let strict =
            Validator::builtin_for_document_with_policy(&path, "basic", NamespacePolicy::Strict03);
        let strict_error = strict.err().expect("strict mode should reject SBGN-ML 0.2");
        assert!(
            strict_error
                .to_string()
                .starts_with("SBGN_NAMESPACE_ERROR:")
        );
        if relative != "tests/examples/go_mf_conflicts.sbgn" {
            let compatible = Validator::builtin_for_document_with_policy(
                &path,
                "basic",
                NamespacePolicy::AllowSbgnml02,
            );
            let error = compatible
                .err()
                .expect("compatibility mode should reject unsupported namespaces");
            assert!(error.to_string().starts_with("SBGN_NAMESPACE_ERROR:"));
        }
    }
}

#[test]
fn legacy_policy_supports_all_languages_and_custom_rules() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..");
    for (language, name) in [
        ("af", "sbgnml-0.2-af-valid.sbgn"),
        ("er", "sbgnml-0.2-er-valid.sbgn"),
        ("pd", "sbgnml-0.2-pd-valid.sbgn"),
    ] {
        let document = root.join("tests/fixtures/compatibility").join(name);
        let builtin = Validator::builtin_for_document_with_policy(
            &document,
            "basic",
            NamespacePolicy::AllowSbgnml02,
        )
        .unwrap();
        let custom = Validator::compile_for_document(
            &root.join(format!("validation/rules/sbgn_{language}.sch")),
            &document,
            "basic",
            NamespacePolicy::AllowSbgnml02,
        )
        .unwrap();
        assert_eq!(
            serde_json::to_value(builtin.validate(&document).unwrap()).unwrap()["valid"],
            true
        );
        assert_eq!(
            serde_json::to_value(custom.validate(&document).unwrap()).unwrap()["valid"],
            true
        );
    }
}

#[test]
fn namespace_policy_has_no_sequential_or_concurrent_contamination() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..");
    let legacy = root.join("tests/fixtures/compatibility/sbgnml-0.2-pd-valid.sbgn");
    let current = root.join("tests/fixtures/error-test-files/PD/pd10110-pass.sbgn");
    let cases = [legacy, current];
    for document in cases.iter().cycle().take(4) {
        let validator = Validator::builtin_for_document_with_policy(
            document,
            "basic",
            NamespacePolicy::AllowSbgnml02,
        )
        .unwrap();
        assert_eq!(
            serde_json::to_value(validator.validate(document).unwrap()).unwrap()["valid"],
            true
        );
    }
    std::thread::scope(|scope| {
        for document in &cases {
            scope.spawn(move || {
                let validator = Validator::builtin_for_document_with_policy(
                    document,
                    "basic",
                    NamespacePolicy::AllowSbgnml02,
                )
                .unwrap();
                assert_eq!(
                    serde_json::to_value(validator.validate(document).unwrap()).unwrap()["valid"],
                    true
                );
            });
        }
    });
}

#[test]
fn custom_schema_rebinds_only_the_sbgn_prefix() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..");
    let document = root.join("tests/fixtures/compatibility/custom-sbgnml-0.2.sbgn");
    let validator = Validator::compile_for_document(
        &root.join("tests/fixtures/compatibility/custom-sbgn.sch"),
        &document,
        "basic",
        NamespacePolicy::AllowSbgnml02,
    )
    .unwrap();
    assert_eq!(
        serde_json::to_value(validator.validate(&document).unwrap()).unwrap()["valid"],
        true
    );
    let unsafe_schema = Validator::compile_for_document(
        &root.join("tests/fixtures/compatibility/custom-unsafe-sbgn.sch"),
        &document,
        "basic",
        NamespacePolicy::AllowSbgnml02,
    );
    let error = unsafe_schema
        .err()
        .expect("unsafe custom binding should fail");
    assert!(error.to_string().contains("unsafe sbgn namespace binding"));
}
