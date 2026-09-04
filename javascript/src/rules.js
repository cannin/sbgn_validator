import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { inspectSbgnDocument } from "./namespace.js";

const RESOURCE_DIRECTORY = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)), "..", "resources", "schematron",
);
const LANGUAGE_SCHEMAS = new Map([
    ["activity flow", "sbgn_af.sch"], ["AF", "sbgn_af.sch"],
    ["entity relationship", "sbgn_er.sch"], ["ER", "sbgn_er.sch"],
    ["process description", "sbgn_pd.sch"], ["PD", "sbgn_pd.sch"],
]);

function manifest() {
    return JSON.parse(fs.readFileSync(path.join(RESOURCE_DIRECTORY, "manifest.json"), "utf8"));
}

export function rulesInfo() {
    const value = manifest();
    return {
        source: "builtin",
        ruleset: value.ruleset,
        ruleset_version: value.ruleset_version,
        ruleset_digest: value.ruleset_digest,
        source_revision: value.source_revision,
    };
}

export function loadBuiltinRule(language) {
    const name = LANGUAGE_SCHEMAS.get(language);
    if (!name) throw new Error(`SCHEMATRON_SCHEMA_ERROR: unsupported SBGN language ${language}`);
    const data = fs.readFileSync(path.join(RESOURCE_DIRECTORY, name));
    const actual = crypto.createHash("sha256").update(data).digest("hex");
    if (actual !== manifest().files[name].sha256) {
        throw new Error(`BUILTIN_RULES_CORRUPT: ${name}`);
    }
    return { name, text: data.toString("utf8") };
}

export function detectSbgnLanguage(documentPath) {
    return inspectSbgnDocument(documentPath).language;
}
