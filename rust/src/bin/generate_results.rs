use sbgn_validator::{NamespacePolicy, Validator};
use serde::Deserialize;
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Deserialize)]
struct Manifest {
    cases: Vec<ManifestCase>,
}

#[derive(Deserialize)]
struct ManifestCase {
    schema: String,
    phase: String,
    input: String,
    oracle: String,
    namespace_policy: Option<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let benchmark_root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..");
    let repository_root = benchmark_root.clone();
    let manifest: Manifest = serde_json::from_str(&fs::read_to_string(
        benchmark_root.join("conformance/manifest.json"),
    )?)?;
    let mut validators = BTreeMap::new();
    for case in &manifest.cases {
        let document = repository_root.join(&case.input);
        let report = if case.namespace_policy.as_deref() == Some("allow-sbgnml-0.2") {
            Validator::compile_for_document(
                &repository_root.join(&case.schema),
                &document,
                &case.phase,
                NamespacePolicy::AllowSbgnml02,
            )?
            .validate(&document)?
        } else {
            let key = format!("{}#{}", case.schema, case.phase);
            if !validators.contains_key(&key) {
                validators.insert(
                    key.clone(),
                    Validator::compile(&repository_root.join(&case.schema), &case.phase)?,
                );
            }
            validators
                .get(&key)
                .expect("validator was just inserted")
                .validate(&document)?
        };
        let relative = case
            .oracle
            .strip_prefix("conformance/oracle/java/")
            .ok_or("oracle path is outside the Java oracle directory")?;
        let output = benchmark_root.join("build/results/rust").join(relative);
        fs::create_dir_all(output.parent().unwrap_or(Path::new(".")))?;
        fs::write(output, serde_json::to_string_pretty(&report)? + "\n")?;
    }
    println!("generated {} Rust reports", manifest.cases.len());
    Ok(())
}
