// Command generate-results validates every case in the shared manifest.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/cannin/sbgn_validator/go/internal/validator"
)

type manifestCase struct {
	Schema          string `json:"schema"`
	Phase           string `json:"phase"`
	Input           string `json:"input"`
	Oracle          string `json:"oracle"`
	NamespacePolicy string `json:"namespace_policy"`
}

type manifest struct {
	Cases []manifestCase `json:"cases"`
}

func main() {
	benchmarkRoot, err := filepath.Abs("..")
	if err != nil {
		panic(err)
	}
	repositoryRoot := benchmarkRoot
	data, err := os.ReadFile(filepath.Join(benchmarkRoot, "conformance/manifest.json"))
	if err != nil {
		panic(err)
	}
	var cases manifest
	if err := json.Unmarshal(data, &cases); err != nil {
		panic(err)
	}
	cache := make(map[string]*validator.Schema)
	for _, item := range cases.Cases {
		document := filepath.Join(repositoryRoot, item.Input)
		var schema *validator.Schema
		if item.NamespacePolicy == "allow-sbgnml-0.2" {
			schema, err = validator.CompileSchemaForDocument(
				filepath.Join(repositoryRoot, item.Schema),
				document,
				item.Phase,
				validator.AllowSBGNML02,
			)
		} else {
			key := item.Schema + "#" + item.Phase
			schema = cache[key]
			if schema == nil {
				schema, err = validator.CompileSchema(
					filepath.Join(repositoryRoot, item.Schema), item.Phase,
				)
				cache[key] = schema
			}
		}
		if err != nil {
			panic(err)
		}
		report, err := schema.Validate(context.Background(), document)
		if err != nil {
			panic(err)
		}
		relative := strings.TrimPrefix(item.Oracle, "conformance/oracle/java/")
		output := filepath.Join(benchmarkRoot, "build/results/go", relative)
		if err := os.MkdirAll(filepath.Dir(output), 0o755); err != nil {
			panic(err)
		}
		encoded, err := json.MarshalIndent(report, "", "  ")
		if err != nil {
			panic(err)
		}
		if err := os.WriteFile(output, append(encoded, '\n'), 0o644); err != nil {
			panic(err)
		}
	}
	fmt.Printf("generated %d Go reports\n", len(cases.Cases))
}
