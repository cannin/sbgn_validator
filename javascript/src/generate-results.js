import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SchematronValidator, validateSbgn } from "./validator.js";

const benchmarkRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const repoRoot = benchmarkRoot;
const manifest = JSON.parse(fs.readFileSync(path.join(benchmarkRoot, "conformance/manifest.json"), "utf8"));
const validators = new Map();

for (const testCase of manifest.cases) {
    let result;
    if (testCase.namespace_policy === "allow-sbgnml-0.2") {
        result = validateSbgn(path.join(repoRoot, testCase.input), {
            schemaPath: path.join(repoRoot, testCase.schema),
            phase: testCase.phase,
            allowSbgnml02: true,
        });
    } else {
        const key = `${testCase.schema}#${testCase.phase}`;
        if (!validators.has(key)) {
            validators.set(
                key,
                new SchematronValidator(path.join(repoRoot, testCase.schema), testCase.phase),
            );
        }
        result = validators.get(key).validate(path.join(repoRoot, testCase.input));
    }
    const relative = testCase.oracle.replace("conformance/oracle/java/", "");
    const output = path.join(benchmarkRoot, "build/results/javascript", relative);
    fs.mkdirSync(path.dirname(output), { recursive: true });
    fs.writeFileSync(output, `${JSON.stringify(result, null, 2)}\n`);
}
