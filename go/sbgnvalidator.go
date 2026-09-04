// Package sbgnvalidator validates SBGN-ML with built-in or explicit Schematron rules.
package sbgnvalidator

import (
	"context"

	"github.com/cannin/sbgn_validator/go/internal/rules"
	"github.com/cannin/sbgn_validator/go/internal/validator"
)

// Report is the normalized validation result.
type Report = validator.Report

// RuleInfo is provenance for the built-in ruleset.
type RuleInfo = rules.Info

// RulesInfo is provenance for the rules embedded in the Go package and binary.
func RulesInfo() (RuleInfo, error) {
	return rules.RulesInfo()
}

// Validate uses the built-in schema selected from the document language.
func Validate(ctx context.Context, documentPath, phase string) (Report, error) {
	schema, err := validator.CompileBuiltin(documentPath, phase)
	if err != nil {
		return Report{}, err
	}
	return schema.Validate(ctx, documentPath)
}

// ValidateWithRules uses an explicit Schematron file instead of built-in rules.
func ValidateWithRules(
	ctx context.Context,
	documentPath string,
	rulesPath string,
	phase string,
) (Report, error) {
	schema, err := validator.CompileSchema(rulesPath, phase)
	if err != nil {
		return Report{}, err
	}
	return schema.Validate(ctx, documentPath)
}
