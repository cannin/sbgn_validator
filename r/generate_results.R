# PURPOSE ----
# Generate normalized R results for every shared conformance fixture.

library(sbgnvalidator)

# FUNCTIONS ----

#' Write one normalized validation report.
#'
#' @param schema_cache Environment containing compiled schemas.
#' @param benchmark_root Absolute benchmark directory.
#' @param repository_root Absolute repository directory.
#' @param entry One fixture manifest entry.
write_result <- function(schema_cache, benchmark_root, repository_root, entry) {
  schema_path <- file.path(repository_root, entry$schema)
  document_path <- file.path(repository_root, entry$input)
  if (identical(entry$namespace_policy, "allow-sbgnml-0.2")) {
    report <- validate_sbgn(
      document_path,
      rules_path = schema_path,
      phase = entry$phase,
      allow_sbgnml_0_2 = TRUE
    )
  } else {
    cache_key <- paste(schema_path, entry$phase, sep = "::")
    if (!exists(cache_key, envir = schema_cache, inherits = FALSE)) {
      assign(
        cache_key,
        schematron_compile(schema_path, entry$phase),
        envir = schema_cache
      )
    }
    report <- schematron_validate(
      get(cache_key, envir = schema_cache, inherits = FALSE),
      document_path
    )
  }
  output_path <- file.path(
    benchmark_root,
    "build",
    "results",
    "r",
    sub("^conformance/oracle/java/", "", entry$oracle)
  )
  dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
  jsonlite::write_json(
    report,
    output_path,
    auto_unbox = TRUE,
    pretty = TRUE,
    null = "null"
  )
}

# LOAD DATA ----

benchmark_root <- normalizePath("..", mustWork = TRUE)
repository_root <- benchmark_root
manifest <- jsonlite::read_json(
  file.path(benchmark_root, "conformance", "manifest.json"),
  simplifyVector = FALSE
)

# ANALYSIS ----

schema_cache <- new.env(parent = emptyenv())
for (entry in manifest$cases) {
  write_result(schema_cache, benchmark_root, repository_root, entry)
}
message("generated ", length(manifest$cases), " R reports")
