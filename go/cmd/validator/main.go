// Command validator validates one XML document with an original Schematron file.
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/cannin/sbgn_validator/go/internal/rules"
	"github.com/cannin/sbgn_validator/go/internal/validator"
)

func main() {
	schemaPath := flag.String("schema", "", "path to the original Schematron schema")
	documentPath := flag.String("document", "", "path to the SBGN-ML document")
	phase := flag.String("phase", "basic", "Schematron phase")
	includeBackend := flag.Bool("backend", false, "include backend metadata")
	rulesInfo := flag.Bool("rules-info", false, "print built-in rule provenance")
	allowSBGNML02 := flag.Bool(
		"allow-sbgnml-0.2", false,
		"allow legacy SBGN-ML 0.2 semantic validation",
	)
	flag.Parse()
	if *rulesInfo {
		info, err := rules.RulesInfo()
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		encoder := json.NewEncoder(os.Stdout)
		encoder.SetIndent("", "  ")
		if err := encoder.Encode(info); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		return
	}
	if *documentPath == "" && flag.NArg() == 1 {
		*documentPath = flag.Arg(0)
	}
	if *documentPath == "" {
		fmt.Fprintln(os.Stderr, "SCHEMATRON_SCHEMA_ERROR: document path is required")
		os.Exit(2)
	}
	policy := validator.Strict03
	if *allowSBGNML02 {
		policy = validator.AllowSBGNML02
	}
	var schema *validator.Schema
	var err error
	if *schemaPath == "" {
		schema, err = validator.CompileBuiltinWithPolicy(*documentPath, *phase, policy)
	} else {
		schema, err = validator.CompileSchemaForDocument(
			*schemaPath, *documentPath, *phase, policy,
		)
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	report, err := schema.Validate(context.Background(), *documentPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if !*includeBackend {
		report.Backend = nil
	}
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(report); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
