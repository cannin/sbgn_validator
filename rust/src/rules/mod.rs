//! Integrity-checked Schematron rules embedded in the crate.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

const AF: &str = include_str!("data/sbgn_af.sch");
const ER: &str = include_str!("data/sbgn_er.sch");
const PD: &str = include_str!("data/sbgn_pd.sch");
const MANIFEST: &str = include_str!("data/manifest.json");

#[derive(Deserialize)]
struct ManifestFile {
    sha256: String,
}

#[derive(Deserialize)]
struct Manifest {
    ruleset: String,
    ruleset_version: String,
    ruleset_digest: String,
    source_revision: Option<String>,
    files: std::collections::HashMap<String, ManifestFile>,
}

/// Provenance for the rules built into this crate.
#[derive(Debug, Serialize)]
pub struct RulesInfo {
    pub source: &'static str,
    pub ruleset: String,
    pub ruleset_version: String,
    pub ruleset_digest: String,
    pub source_revision: Option<String>,
}

fn manifest() -> Result<Manifest, String> {
    serde_json::from_str(MANIFEST).map_err(|error| format!("BUILTIN_RULES_CORRUPT: {error}"))
}

/// Return metadata identifying the embedded ruleset.
pub fn rules_info() -> Result<RulesInfo, String> {
    let value = manifest()?;
    Ok(RulesInfo {
        source: "builtin",
        ruleset: value.ruleset,
        ruleset_version: value.ruleset_version,
        ruleset_digest: value.ruleset_digest,
        source_revision: value.source_revision,
    })
}

/// Return the integrity-checked embedded schema for an SBGN language.
pub fn load(language: &str) -> Result<(&'static str, &'static str), String> {
    let (name, source) = match language {
        "activity flow" | "AF" => ("sbgn_af.sch", AF),
        "entity relationship" | "ER" => ("sbgn_er.sch", ER),
        "process description" | "PD" => ("sbgn_pd.sch", PD),
        _ => {
            return Err(format!(
                "SCHEMATRON_SCHEMA_ERROR: unsupported SBGN language {language:?}"
            ));
        }
    };
    let expected = manifest()?
        .files
        .get(name)
        .ok_or_else(|| format!("BUILTIN_RULES_CORRUPT: missing manifest entry for {name}"))?
        .sha256
        .clone();
    let actual = format!("{:x}", Sha256::digest(source.as_bytes()));
    if actual != expected {
        return Err(format!("BUILTIN_RULES_CORRUPT: {name}"));
    }
    Ok((name, source))
}
