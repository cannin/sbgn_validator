import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { rulesInfo } from "../src/rules.js";
import { SchematronValidator, validateSbgn } from "../src/validator.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

test("original PD schema emits pd10110", () => {
    const validator = new SchematronValidator(path.join(root, "validation/rules/sbgn_pd.sch"));
    const report = validator.validate(path.join(root, "tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn"));
    assert(report.findings.some((finding) => finding.id === "pd10110"));
});

test("built-in rules detect language and report digest", () => {
    const document = path.join(root, "tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn");
    const report = validateSbgn(document);
    const canonical = validateSbgn(document, {
        schemaPath: path.join(root, "validation/rules/sbgn_pd.sch"),
    });
    assert.equal(report.schema, "sbgn_pd.sch");
    assert(report.findings.some((finding) => finding.id === "pd10110"));
    assert.deepEqual(report, canonical);
    assert.match(rulesInfo().ruleset_digest, /^sha256:/);
});

test("legacy policy runs semantic rules", () => {
    const schema = path.join(root, "validation/rules/sbgn_pd.sch");
    const document = path.join(root, "tests/examples/go_mf_conflicts.sbgn");
    const report = new SchematronValidator(schema).validate(document);
    assert.equal(report.valid, false);
    assert.deepEqual(report.findings.map((finding) => finding.id), ["sbgn-namespace-0.3"]);
    const compatible = validateSbgn(document, {
        schemaPath: schema,
        allowSbgnml02: true,
    });
    assert.equal(compatible.phase, "basic-allow-sbgnml-0.2");
    assert.equal(compatible.valid, false);
    const ids = new Set(compatible.findings.map((finding) => finding.id));
    for (const id of ["pd10102", "pd10132", "pd10141"]) assert(ids.has(id));
    const expectedTest = "$port-class='process' or $port-class='omitted process' or "
        + "$port-class='uncertain process' or $port-class='association' or "
        + "$port-class='dissociation' or $port-class='phenotype'";
    for (const finding of compatible.findings.filter((item) => item.id === "pd10102")) {
        assert.equal(finding.test, expectedTest);
    }
});

test("namespace policy accepts only SBGN-ML 0.3 and explicit legacy 0.2", () => {
    assert.throws(
        () => validateSbgn(path.join(root, "tests/examples/go_mf_conflicts.sbgn")),
        /^Error: SBGN_NAMESPACE_ERROR:/,
    );
    for (const name of ["missing-namespace", "unrelated-namespace", "future-namespace"]) {
        const document = path.join(root, `tests/fixtures/compatibility/${name}.sbgn`);
        assert.throws(() => validateSbgn(document), /^Error: SBGN_NAMESPACE_ERROR:/);
        assert.throws(
            () => validateSbgn(document, { allowSbgnml02: true }),
            /^Error: SBGN_NAMESPACE_ERROR:/,
        );
    }
});

test("legacy policy supports AF, ER, PD, and custom rules without contamination", () => {
    const cases = new Map([
        ["af", "sbgnml-0.2-af-valid.sbgn"],
        ["er", "sbgnml-0.2-er-valid.sbgn"],
        ["pd", "sbgnml-0.2-pd-valid.sbgn"],
    ]);
    for (const [language, name] of cases) {
        const document = path.join(root, "tests/fixtures/compatibility", name);
        assert.equal(validateSbgn(document, { allowSbgnml02: true }).valid, true);
        assert.equal(validateSbgn(document, {
            schemaPath: path.join(root, `validation/rules/sbgn_${language}.sch`),
            allowSbgnml02: true,
        }).valid, true);
    }
    const legacy = path.join(root, "tests/fixtures/compatibility/sbgnml-0.2-pd-valid.sbgn");
    const current = path.join(root, "tests/fixtures/error-test-files/PD/pd10110-pass.sbgn");
    for (const document of [legacy, current, legacy, current]) {
        assert.equal(validateSbgn(document, { allowSbgnml02: true }).valid, true);
    }
});

test("custom schemas rebind only the sbgn prefix", () => {
    const document = path.join(root, "tests/fixtures/compatibility/custom-sbgnml-0.2.sbgn");
    assert.equal(validateSbgn(document, {
        schemaPath: path.join(root, "tests/fixtures/compatibility/custom-sbgn.sch"),
        allowSbgnml02: true,
    }).valid, true);
    assert.throws(
        () => validateSbgn(document, {
            schemaPath: path.join(
                root,
                "tests/fixtures/compatibility/custom-unsafe-sbgn.sch",
            ),
            allowSbgnml02: true,
        }),
        /^Error: SCHEMATRON_NAMESPACE_ERROR:/,
    );
});
