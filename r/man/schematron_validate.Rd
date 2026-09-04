\name{schematron_validate}
\alias{schematron_validate}
\title{Validate an SBGN-ML Document}
\usage{
schematron_validate(schema, document_path)
}
\arguments{
\item{schema}{Compiled schema returned by \code{schematron_compile()}.}
\item{document_path}{Path to an SBGN-ML document.}
}
\value{A list containing validity, SVRL-aligned normalized findings, and backend metadata.}
\description{
Evaluates a compiled Schematron schema directly against an SBGN-ML document.
}
