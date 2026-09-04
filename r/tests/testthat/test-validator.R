test_that("all authoritative schemas compile", {
  root <- Sys.getenv("LIBSBGN_REPO_ROOT")
  skip_if(root == "", "requires the libSBGN source fixture tree")
  for (language in c("af", "er", "pd")) {
    filename <- paste0("sbgn_", language, ".sch")
    path <- file.path(root, "validation", "rules", filename)
    expect_s3_class(schematron_compile(path), "sbgn_validator_schema")
  }
})

test_that("PD fixture reports its expected rule", {
  root <- Sys.getenv("LIBSBGN_REPO_ROOT")
  skip_if(root == "", "requires the libSBGN source fixture tree")
  schema_path <- file.path(root, "validation", "rules", "sbgn_pd.sch")
  schema <- schematron_compile(schema_path)
  report <- schematron_validate(
    schema,
    file.path(
      root,
      "tests",
      "fixtures",
      "error-test-files",
      "PD",
      "pd10110-fail-1.sbgn"
    )
  )
  rule_ids <- vapply(report$findings, `[[`, character(1), "id")
  expect_true("pd10110" %in% rule_ids)
})

test_that("built-in rules detect language and report digest", {
  root <- Sys.getenv("LIBSBGN_REPO_ROOT")
  skip_if(root == "", "requires the libSBGN source fixture tree")
  document <- file.path(
    root,
    "tests",
    "fixtures",
    "error-test-files",
    "PD",
    "pd10110-fail-1.sbgn"
  )
  report <- validate_sbgn(document)
  canonical <- validate_sbgn(
    document,
    file.path(root, "validation", "rules", "sbgn_pd.sch")
  )
  expect_identical(report$schema, "sbgn_pd.sch")
  expect_true("pd10110" %in% vapply(report$findings, `[[`, character(1), "id"))
  expect_match(rules_info()$ruleset_digest, "^sha256:")
  expect_equal(report, canonical)
})

test_that("legacy policy runs semantic rules", {
  root <- Sys.getenv("LIBSBGN_REPO_ROOT")
  skip_if(root == "", "requires the libSBGN source fixture tree")
  schema_path <- file.path(root, "validation", "rules", "sbgn_pd.sch")
  schema <- schematron_compile(schema_path)
  document <- file.path(root, "tests", "examples", "go_mf_conflicts.sbgn")
  report <- schematron_validate(schema, document)
  expect_false(report$valid)
  expect_identical(report$findings[[1]]$id, "sbgn-namespace-0.3")
  compatible <- validate_sbgn(
    document,
    file.path(root, "validation", "rules", "sbgn_pd.sch"),
    allow_sbgnml_0_2 = TRUE
  )
  expect_false(compatible$valid)
  rule_ids <- vapply(compatible$findings, `[[`, character(1), "id")
  expect_true(all(c("pd10102", "pd10132", "pd10141") %in% rule_ids))
  expected_test <- paste(
    "$port-class='process' or $port-class='omitted process' or",
    "$port-class='uncertain process' or $port-class='association' or",
    "$port-class='dissociation' or $port-class='phenotype'"
  )
  pd10102_tests <- vapply(
    Filter(
      function(finding) identical(finding$id, "pd10102"),
      compatible$findings
    ),
    `[[`,
    character(1),
    "test"
  )
  expect_identical(unique(pd10102_tests), expected_test)
})

test_that("namespace policy rejects unsupported namespaces", {
  root <- Sys.getenv("LIBSBGN_REPO_ROOT")
  skip_if(root == "", "requires the libSBGN source fixture tree")
  paths <- c(
    "tests/examples/go_mf_conflicts.sbgn",
    "tests/fixtures/compatibility/missing-namespace.sbgn",
    "tests/fixtures/compatibility/unrelated-namespace.sbgn",
    "tests/fixtures/compatibility/future-namespace.sbgn"
  )
  for (relative_path in paths) {
    document <- file.path(root, relative_path)
    expect_error(validate_sbgn(document), "^SBGN_NAMESPACE_ERROR:")
    if (!identical(relative_path, "tests/examples/go_mf_conflicts.sbgn")) {
      expect_error(
        validate_sbgn(file.path(root, relative_path), allow_sbgnml_0_2 = TRUE),
        "^SBGN_NAMESPACE_ERROR:"
      )
    }
  }
})

test_that("legacy policy supports AF, ER, PD, and custom rules", {
  root <- Sys.getenv("LIBSBGN_REPO_ROOT")
  skip_if(root == "", "requires the libSBGN source fixture tree")
  cases <- c(
    af = "sbgnml-0.2-af-valid.sbgn",
    er = "sbgnml-0.2-er-valid.sbgn",
    pd = "sbgnml-0.2-pd-valid.sbgn"
  )
  for (language in names(cases)) {
    document <- file.path(
      root,
      "tests",
      "fixtures",
      "compatibility",
      cases[[language]]
    )
    expect_true(validate_sbgn(document, allow_sbgnml_0_2 = TRUE)$valid)
    expect_true(validate_sbgn(
      document,
      file.path(root, "validation", "rules", paste0("sbgn_", language, ".sch")),
      allow_sbgnml_0_2 = TRUE
    )$valid)
  }
})

test_that("custom schemas rebind only the sbgn prefix", {
  root <- Sys.getenv("LIBSBGN_REPO_ROOT")
  skip_if(root == "", "requires the libSBGN source fixture tree")
  document <- file.path(
    root,
    "tests",
    "fixtures",
    "compatibility",
    "custom-sbgnml-0.2.sbgn"
  )
  expect_true(validate_sbgn(
    document,
    file.path(root, "tests", "fixtures", "compatibility", "custom-sbgn.sch"),
    allow_sbgnml_0_2 = TRUE
  )$valid)
  expect_error(
    validate_sbgn(
      document,
      file.path(
        root,
        "tests",
        "fixtures",
        "compatibility",
        "custom-unsafe-sbgn.sch"
      ),
      allow_sbgnml_0_2 = TRUE
    ),
    "^SCHEMATRON_NAMESPACE_ERROR:"
  )
})
