.sbgn_ml_03 <- "http://sbgn.org/libsbgn/0.3"
.sbgn_ml_02 <- "http://sbgn.org/libsbgn/0.2"
.namespace_policy_strict <- "strict-0.3"
.namespace_policy_allow_02 <- "allow-sbgnml-0.2"

#' Compile an authoritative libSBGN Schematron schema
#'
#' @param schema_path Path to an original libSBGN `.sch` file.
#' @param phase Schematron phase name.
#' @param namespace_policy Namespace policy identifier used during compilation.
#' @param effective_sbgn_namespace Effective namespace for the Schematron
#'   `sbgn` prefix.
#' @return An external pointer to an immutable compiled schema.
#' @export
schematron_compile <- function(schema_path, phase = "basic",
                               namespace_policy = "strict-0.3",
                               effective_sbgn_namespace =
                                 "http://sbgn.org/libsbgn/0.3") {
  schematron_compile_cpp(
    schema_path,
    phase,
    namespace_policy,
    effective_sbgn_namespace
  )
}

#' Validate an SBGN-ML document
#'
#' @param schema Compiled schema returned by [schematron_compile()].
#' @param document_path Path to an SBGN-ML document.
#' @return An SVRL-aligned normalized validation report list.
#' @export
schematron_validate <- function(schema, document_path) {
  schematron_validate_cpp(schema, document_path)
}

#' Report the provenance of the built-in Schematron rules
#'
#' @return A named list describing the packaged ruleset.
#' @export
rules_info <- function() {
  path <- system.file("schematron", "manifest.json", package = "sbgnvalidator")
  if (identical(path, "")) {
    stop("BUILTIN_RULES_MISSING: manifest.json", call. = FALSE)
  }
  manifest <- jsonlite::fromJSON(path, simplifyVector = FALSE)
  list(
    source = "builtin",
    ruleset = manifest$ruleset,
    ruleset_version = manifest$ruleset_version,
    ruleset_digest = manifest$ruleset_digest,
    source_revision = manifest$source_revision
  )
}

#' Validate an SBGN-ML document with packaged or custom rules
#'
#' @param document_path Path to an SBGN-ML document.
#' @param rules_path Optional path to an explicit Schematron override.
#' @param phase Schematron phase name.
#' @param allow_sbgnml_0_2 Allow legacy SBGN-ML 0.2 semantic validation.
#' @return An SVRL-aligned normalized validation report list.
#' @export
validate_sbgn <- function(document_path, rules_path = NULL, phase = "basic",
                          allow_sbgnml_0_2 = FALSE) {
  document_info <- sbgn_document_info_cpp(document_path)
  document_namespace <- document_info$namespace
  namespace_policy <- if (allow_sbgnml_0_2) {
    .namespace_policy_allow_02
  } else {
    .namespace_policy_strict
  }
  accepted_namespaces <- .sbgn_ml_03
  if (allow_sbgnml_0_2) {
    accepted_namespaces <- c(accepted_namespaces, .sbgn_ml_02)
  }
  if (!document_namespace %in% accepted_namespaces) {
    expected <- paste(accepted_namespaces, collapse = " or ")
    found <- if (identical(document_namespace, "")) {
      "<missing>"
    } else {
      document_namespace
    }
    stop(
      sprintf("SBGN_NAMESPACE_ERROR: expected %s; found %s", expected, found),
      call. = FALSE
    )
  }
  if (is.null(rules_path)) {
    language <- document_info$language
    schema_names <- c(
      "activity flow" = "sbgn_af.sch",
      "AF" = "sbgn_af.sch",
      "entity relationship" = "sbgn_er.sch",
      "ER" = "sbgn_er.sch",
      "process description" = "sbgn_pd.sch",
      "PD" = "sbgn_pd.sch"
    )
    rules_name <- unname(schema_names[language])
    if (is.na(rules_name)) {
      stop(
        sprintf(
          "SCHEMATRON_SCHEMA_ERROR: unsupported SBGN language %s",
          language
        ),
        call. = FALSE
      )
    }
    rules_path <- system.file(
      "schematron",
      rules_name,
      package = "sbgnvalidator"
    )
    if (identical(rules_path, "")) {
      stop(sprintf("BUILTIN_RULES_MISSING: %s", rules_name), call. = FALSE)
    }
  }
  schema <- schematron_compile(
    rules_path,
    phase,
    namespace_policy,
    document_namespace
  )
  schematron_validate(schema, document_path)
}
