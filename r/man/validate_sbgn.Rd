\name{validate_sbgn}
\alias{validate_sbgn}
\title{Validate an SBGN-ML Document}
\usage{
validate_sbgn(
  document_path,
  rules_path = NULL,
  phase = "basic",
  allow_sbgnml_0_2 = FALSE
)
}
\arguments{
  \item{document_path}{Path to an SBGN-ML document.}
  \item{rules_path}{Optional path to an explicit Schematron override.}
  \item{phase}{Schematron phase name.}
  \item{allow_sbgnml_0_2}{Allow legacy SBGN-ML 0.2 semantic validation.}
}
\value{An SVRL-aligned normalized validation report list.}
\description{
Selects the packaged Schematron schema from the document's map language unless
an explicit rule path is supplied.
}
