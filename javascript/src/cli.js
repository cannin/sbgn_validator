#!/usr/bin/env node

import { rulesInfo } from "./rules.js";
import { validateSbgn } from "./validator.js";

const args = process.argv.slice(2);
const includeBackend = args.includes("--backend");
const allowSbgnml02 = args.includes("--allow-sbgnml-0.2");
if (args.includes("--rules-info")) {
    console.log(JSON.stringify(rulesInfo(), null, 2));
    process.exit(0);
}
const valueOptions = new Set(["--schema", "--document", "--phase"]);
const flags = new Set(["--backend", "--allow-sbgnml-0.2"]);
const values = {};
const positional = [];
for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (flags.has(argument)) continue;
    if (valueOptions.has(argument)) {
        if (index + 1 >= args.length) throw new Error(`missing value for ${argument}`);
        values[argument] = args[index + 1];
        index += 1;
    } else if (argument.startsWith("--")) {
        throw new Error(`unknown option: ${argument}`);
    } else {
        positional.push(argument);
    }
}
let schemaPath = values["--schema"];
let document = values["--document"];
if (!document && positional.length === 1) document = positional[0];
if (!document && positional.length === 2 && !schemaPath) {
    [schemaPath, document] = positional;
}
if (!document || positional.length > 2) {
    throw new Error(
        "usage: sbgn-validator DOCUMENT [--schema PATH] [--phase NAME] "
        + "[--backend] [--allow-sbgnml-0.2]",
    );
}
const report = validateSbgn(document, {
    schemaPath,
    phase: values["--phase"] ?? "basic",
    allowSbgnml02,
});
if (!includeBackend) delete report.backend;
console.log(JSON.stringify(report, null, 2));
