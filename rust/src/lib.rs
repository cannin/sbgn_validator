#![forbid(unsafe_code)]
#![allow(clippy::collapsible_if)]

#[rustfmt::skip]
#[path = "../vendor/schematron/src/error.rs"]
pub mod error;
#[rustfmt::skip]
#[path = "../vendor/schematron/src/lint.rs"]
pub mod lint;
#[rustfmt::skip]
#[path = "../vendor/schematron/src/schema/mod.rs"]
pub mod schema;
#[rustfmt::skip]
#[path = "../vendor/schematron/src/svrl.rs"]
pub mod svrl;
#[rustfmt::skip]
#[path = "../vendor/schematron/src/text.rs"]
pub mod text;
#[rustfmt::skip]
#[path = "../vendor/schematron/src/validate/mod.rs"]
pub mod validate;
#[rustfmt::skip]
#[path = "../vendor/schematron/src/xml/mod.rs"]
pub mod xml;
#[rustfmt::skip]
#[path = "../vendor/schematron/src/xpath/mod.rs"]
pub mod xpath;

pub use error::{Error, Result};
pub use schema::{Schema, SchemaOptions};
pub use svrl::SvrlOptions;
pub use text::TextOptions;
pub use validate::{PhaseSelection, Report, ValidateOptions};
pub use xml::Document;

use crate::validate::ResultKind;
use serde::Serialize;
use std::path::Path;

pub mod rules;

/// Current SBGN-ML namespace used by the canonical rules.
pub const SBGN_ML_03: &str = "http://sbgn.org/libsbgn/0.3";
/// Legacy SBGN-ML namespace supported by compatibility mode.
pub const SBGN_ML_02: &str = "http://sbgn.org/libsbgn/0.2";
const COMPATIBILITY_PHASE: &str = "basic-allow-sbgnml-0.2";

/// Controls which SBGN-ML document namespaces validation accepts.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NamespacePolicy {
    /// Accept only SBGN-ML 0.3.
    Strict03,
    /// Accept SBGN-ML 0.3 and legacy SBGN-ML 0.2.
    AllowSbgnml02,
}

impl NamespacePolicy {
    fn effective_namespace(
        self,
        document_namespace: Option<&str>,
    ) -> std::result::Result<&'static str, String> {
        if document_namespace == Some(SBGN_ML_03) {
            return Ok(SBGN_ML_03);
        }
        if self == Self::AllowSbgnml02 && document_namespace == Some(SBGN_ML_02) {
            return Ok(SBGN_ML_02);
        }
        let expected = if self == Self::AllowSbgnml02 {
            format!("{SBGN_ML_03} or {SBGN_ML_02}")
        } else {
            SBGN_ML_03.to_owned()
        };
        Err(format!(
            "SBGN_NAMESPACE_ERROR: expected {expected}; found {}",
            document_namespace.unwrap_or("<missing>")
        ))
    }
}

#[derive(Debug, Serialize)]
pub struct BackendInfo {
    language: &'static str,
    implementation: &'static str,
    implementation_version: &'static str,
    schematron_engine: &'static str,
    xpath_engine: &'static str,
    xpath_version: &'static str,
    native_schematron: bool,
    profile_version: &'static str,
}

#[derive(Debug, Serialize)]
pub struct DiagnosticReference {
    diagnostic: String,
    text: String,
}

#[derive(Debug, Serialize)]
pub struct DerivedIdentity {
    element_id: Option<String>,
    element_kind: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct CanonicalFinding {
    id: String,
    r#type: &'static str,
    role: Option<String>,
    flag: Option<String>,
    location: Option<String>,
    test: Option<String>,
    text: String,
    diagnostic_references: Vec<DiagnosticReference>,
    derived: DerivedIdentity,
}

#[derive(Debug, Serialize)]
pub struct CanonicalReport {
    schema: String,
    phase: String,
    valid: bool,
    findings: Vec<CanonicalFinding>,
    #[serde(skip_serializing_if = "Option::is_none")]
    backend: Option<BackendInfo>,
}

impl CanonicalReport {
    /// Remove implementation metadata from serialized command output.
    pub fn without_backend(mut self) -> Self {
        self.backend = None;
        self
    }
}

pub struct Validator {
    schema_name: String,
    phase: String,
    schema: Schema,
    diagnostic_order: Vec<String>,
}

impl Validator {
    /// Compile an authoritative Schematron file once.
    pub fn compile(path: &Path, phase: &str) -> std::result::Result<Self, Error> {
        let source = std::fs::read_to_string(path).map_err(|source| Error::Io {
            path: path.display().to_string(),
            source,
        })?;
        Self::compile_source(
            path.file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .as_ref(),
            &source,
            phase,
            &path.display().to_string(),
        )
    }

    /// Compile an in-memory Schematron source once.
    pub fn compile_source(
        schema_name: &str,
        source: &str,
        phase: &str,
        base_uri: &str,
    ) -> std::result::Result<Self, Error> {
        Self::compile_source_with_policy(
            schema_name,
            source,
            phase,
            base_uri,
            NamespacePolicy::Strict03,
            SBGN_ML_03,
        )
    }

    fn compile_source_with_policy(
        schema_name: &str,
        source: &str,
        requested_phase: &str,
        base_uri: &str,
        policy: NamespacePolicy,
        effective_namespace: &str,
    ) -> std::result::Result<Self, Error> {
        // The pinned libSBGN schemas omit queryBinding despite using XPath 2.
        // Apply the documented schema-specific compatibility metadata in memory.
        let effective_source = if source.contains("queryBinding=") {
            source.to_owned()
        } else {
            source.replacen("<iso:schema", "<iso:schema queryBinding=\"xslt2\"", 1)
        };
        let mut options = SchemaOptions::new().with_base_uri(base_uri.to_owned());
        if effective_namespace == SBGN_ML_02 {
            options = options.with_namespace_override("sbgn", SBGN_ML_03, SBGN_ML_02);
        }
        let schema = Schema::from_str_with(&effective_source, &options)?;
        let phase = if policy == NamespacePolicy::AllowSbgnml02
            && requested_phase == "basic"
            && schema
                .phases()
                .any(|candidate| candidate == COMPATIBILITY_PHASE)
        {
            COMPATIBILITY_PHASE
        } else {
            requested_phase
        };
        let diagnostic_order = schema
            .model()
            .diagnostics
            .iter()
            .map(|diagnostic| diagnostic.id.clone())
            .collect();
        Ok(Self {
            schema_name: schema_name.to_owned(),
            phase: phase.to_owned(),
            schema,
            diagnostic_order,
        })
    }

    /// Compile the built-in rules selected from a document's map language.
    pub fn builtin_for_document(
        path: &Path,
        phase: &str,
    ) -> std::result::Result<Self, Box<dyn std::error::Error>> {
        Self::builtin_for_document_with_policy(path, phase, NamespacePolicy::Strict03)
    }

    /// Compile built-in rules after applying an explicit namespace policy.
    pub fn builtin_for_document_with_policy(
        path: &Path,
        phase: &str,
        policy: NamespacePolicy,
    ) -> std::result::Result<Self, Box<dyn std::error::Error>> {
        let (language, document_namespace) = inspect_document(path)?;
        let effective_namespace = policy.effective_namespace(document_namespace.as_deref())?;
        let (name, source) = rules::load(&language)?;
        Ok(Self::compile_source_with_policy(
            name,
            source,
            phase,
            name,
            policy,
            effective_namespace,
        )?)
    }

    /// Compile explicit rules for a document after applying a namespace policy.
    pub fn compile_for_document(
        schema_path: &Path,
        document_path: &Path,
        phase: &str,
        policy: NamespacePolicy,
    ) -> std::result::Result<Self, Box<dyn std::error::Error>> {
        let (_, document_namespace) = inspect_document(document_path)?;
        let effective_namespace = policy.effective_namespace(document_namespace.as_deref())?;
        let source = std::fs::read_to_string(schema_path).map_err(|source| Error::Io {
            path: schema_path.display().to_string(),
            source,
        })?;
        Ok(Self::compile_source_with_policy(
            schema_path
                .file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .as_ref(),
            &source,
            phase,
            &schema_path.display().to_string(),
            policy,
            effective_namespace,
        )?)
    }

    /// Validate one document using the cached schema.
    pub fn validate(&self, path: &Path) -> std::result::Result<CanonicalReport, Error> {
        let document = Document::from_path(path)?;
        let options = ValidateOptions::new().with_phase(PhaseSelection::from(self.phase.clone()));
        let report = self.schema.validate_with(&document, &options)?;
        let mut findings: Vec<_> = report
            .assertions()
            .map(|finding| {
                let diagnostic_references: Vec<_> = self
                    .diagnostic_order
                    .iter()
                    .flat_map(|diagnostic_id| {
                        finding
                            .diagnostics
                            .iter()
                            .filter(move |diagnostic| &diagnostic.id == diagnostic_id)
                    })
                    .map(|diagnostic| {
                        let prefix = format!("{}:", diagnostic.id);
                        let value = diagnostic
                            .text
                            .trim()
                            .strip_prefix(&prefix)
                            .unwrap_or(diagnostic.text.trim())
                            .trim()
                            .to_owned();
                        DiagnosticReference {
                            diagnostic: diagnostic.id.clone(),
                            text: value,
                        }
                    })
                    .collect();
                let element_id = diagnostic_references
                    .iter()
                    .find(|item| item.diagnostic == "id")
                    .map(|item| item.text.clone())
                    .filter(|value| !value.is_empty());
                CanonicalFinding {
                    id: finding.id.clone().unwrap_or_default(),
                    r#type: match finding.kind {
                        ResultKind::FailedAssert => "failed-assert",
                        ResultKind::SuccessfulReport => "successful-report",
                    },
                    role: finding.role.clone(),
                    flag: finding.flag.clone(),
                    location: Some(finding.location.clone()),
                    test: Some(normalize_whitespace(&finding.test)),
                    text: normalize_text(&finding.text),
                    diagnostic_references,
                    derived: DerivedIdentity {
                        element_id,
                        element_kind: element_kind(&finding.location),
                    },
                }
            })
            .collect();
        findings.sort_by(|left, right| {
            (
                &left.id,
                &left.derived.element_id,
                &left.location,
                &left.text,
            )
                .cmp(&(
                    &right.id,
                    &right.derived.element_id,
                    &right.location,
                    &right.text,
                ))
        });
        Ok(CanonicalReport {
            schema: self.schema_name.clone(),
            phase: self.phase.clone(),
            valid: report.is_valid(),
            findings,
            backend: Some(BackendInfo {
                language: "rust",
                implementation: "sbgn-validator-rust",
                implementation_version: "0.1.1",
                schematron_engine: "schematron 0.5.1",
                xpath_engine: "schematron native XPath",
                xpath_version: "1.0 plus documented 2.0 subset",
                native_schematron: true,
                profile_version: "libSBGN-Schematron-Profile-1",
            }),
        })
    }
}

/// Detect the SBGN map language without applying semantic rules.
pub fn detect_language(path: &Path) -> std::result::Result<String, Box<dyn std::error::Error>> {
    Ok(inspect_document(path)?.0)
}

/// Detect the SBGN namespace and map language without applying semantic rules.
pub fn inspect_document(
    path: &Path,
) -> std::result::Result<(String, Option<String>), Box<dyn std::error::Error>> {
    let document = Document::from_path(path)?;
    let root = document
        .document_element()
        .ok_or("SCHEMATRON_SCHEMA_ERROR: SBGN root is missing")?;
    let root_name = document
        .name(root)
        .ok_or("SCHEMATRON_SCHEMA_ERROR: SBGN root is missing")?;
    if root_name.local != "sbgn" {
        return Err("SCHEMATRON_SCHEMA_ERROR: SBGN root is missing".into());
    }
    let namespace = root_name.uri.clone();
    let map = document
        .children(root)
        .iter()
        .copied()
        .find(|node| {
            document
                .name(*node)
                .is_some_and(|name| name.local == "map" && name.uri == namespace)
        })
        .ok_or("SCHEMATRON_SCHEMA_ERROR: SBGN map is missing")?;
    for attribute in document.attributes(map) {
        if document
            .name(*attribute)
            .is_some_and(|name| name.local == "language")
        {
            return Ok((document.value(*attribute).to_owned(), namespace));
        }
    }
    Err("SCHEMATRON_SCHEMA_ERROR: SBGN map language is missing".into())
}

fn normalize_text(value: &str) -> String {
    value
        .split_whitespace()
        .map(|part| {
            let bytes = part.as_bytes();
            if bytes.len() >= 8
                && bytes[0..2].iter().all(u8::is_ascii_digit)
                && bytes[2] == b':'
                && bytes[3..5].iter().all(u8::is_ascii_digit)
                && bytes[5] == b':'
                && bytes[6..8].iter().all(u8::is_ascii_digit)
            {
                "<CURRENT_TIME>"
            } else {
                part
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

fn normalize_whitespace(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn element_kind(location: &str) -> Option<String> {
    const MARKER: &str = "local-name()='";
    if let Some(start) = location.rfind(MARKER) {
        let value = &location[start + MARKER.len()..];
        if let Some(end) = value.find('\'') {
            return Some(value[..end].to_owned());
        }
    }
    location
        .rsplit('/')
        .find(|part| !part.is_empty())
        .map(|part| part.split('[').next().unwrap_or(part))
        .map(|part| part.rsplit(':').next().unwrap_or(part).to_owned())
}
