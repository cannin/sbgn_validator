// Package rules provides integrity-checked Schematron resources embedded in the binary.
package rules

import (
	"crypto/sha256"
	"embed"
	"encoding/hex"
	"encoding/json"
	"fmt"
)

//go:embed data/*
var files embed.FS

type manifestFile struct {
	SHA256 string `json:"sha256"`
}

type manifestData struct {
	Ruleset        string                  `json:"ruleset"`
	RulesetVersion string                  `json:"ruleset_version"`
	RulesetDigest  string                  `json:"ruleset_digest"`
	SourceRevision *string                 `json:"source_revision"`
	Files          map[string]manifestFile `json:"files"`
}

// Info is package-independent provenance for built-in rules.
type Info struct {
	Source         string  `json:"source"`
	Ruleset        string  `json:"ruleset"`
	RulesetVersion string  `json:"ruleset_version"`
	RulesetDigest  string  `json:"ruleset_digest"`
	SourceRevision *string `json:"source_revision"`
}

func manifest() (manifestData, error) {
	data, err := files.ReadFile("data/manifest.json")
	if err != nil {
		return manifestData{}, fmt.Errorf("BUILTIN_RULES_MISSING: manifest.json: %w", err)
	}
	var value manifestData
	if err := json.Unmarshal(data, &value); err != nil {
		return manifestData{}, fmt.Errorf("BUILTIN_RULES_CORRUPT: manifest.json: %w", err)
	}
	return value, nil
}

// RulesInfo returns provenance for the rules embedded in this binary.
func RulesInfo() (Info, error) {
	value, err := manifest()
	if err != nil {
		return Info{}, err
	}
	return Info{
		Source: "builtin", Ruleset: value.Ruleset, RulesetVersion: value.RulesetVersion,
		RulesetDigest: value.RulesetDigest, SourceRevision: value.SourceRevision,
	}, nil
}

// Load returns an integrity-checked schema by SBGN language.
func Load(language string) (string, []byte, error) {
	names := map[string]string{
		"activity flow": "sbgn_af.sch", "AF": "sbgn_af.sch",
		"entity relationship": "sbgn_er.sch", "ER": "sbgn_er.sch",
		"process description": "sbgn_pd.sch", "PD": "sbgn_pd.sch",
	}
	name, ok := names[language]
	if !ok {
		return "", nil, fmt.Errorf("SCHEMATRON_SCHEMA_ERROR: unsupported SBGN language %q", language)
	}
	data, err := files.ReadFile("data/" + name)
	if err != nil {
		return "", nil, fmt.Errorf("BUILTIN_RULES_MISSING: %s: %w", name, err)
	}
	value, err := manifest()
	if err != nil {
		return "", nil, err
	}
	actual := sha256.Sum256(data)
	if hex.EncodeToString(actual[:]) != value.Files[name].SHA256 {
		return "", nil, fmt.Errorf("BUILTIN_RULES_CORRUPT: %s", name)
	}
	return name, data, nil
}
