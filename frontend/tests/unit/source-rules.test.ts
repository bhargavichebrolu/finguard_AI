/**
 * Rules checked across the application's source: wording, hardcoded figures, browser storage,
 * inline HTML, and that the generated API types are current.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

import openapiTS, { astToString } from "openapi-typescript";
import { describe, expect, it } from "vitest";

const FRONTEND = join(__dirname, "..", "..");
const SOURCE = join(FRONTEND, "src");
const GENERATED = join(SOURCE, "types", "api.generated.ts");

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx)$/.test(name) && path !== GENERATED ? [path] : [];
  });
}

const FILES = sourceFiles(SOURCE).map((path) => ({
  name: relative(FRONTEND, path),
  text: readFileSync(path, "utf8"),
}));

describe("source rules", () => {
  it("finds the application's source files", () => {
    expect(FILES.length).toBeGreaterThan(10);
  });

  it("never calls a score a probability or a flag a fraud finding", () => {
    const forbidden = [/fraud probability/i, /probability of fraud/i, /% chance/i, /fraud detected/i, /confirmed fraud/i, /is fraudulent/i];
    for (const file of FILES) {
      for (const pattern of forbidden) {
        expect(pattern.test(file.text), `${file.name} matches ${pattern}`).toBe(false);
      }
    }
  });

  it("contains none of the saved Phase 2 figures, which must come from the API", () => {
    const figures = ["0.282", "45.9", "21.9", "56.1", "40.7", "0.4242", "0.3499", "0.0284191", "0.02842"];
    for (const file of FILES) {
      for (const figure of figures) {
        expect(file.text.includes(figure), `${file.name} contains ${figure}`).toBe(false);
      }
    }
  });

  it("never touches browser storage, where tokens must not live", () => {
    for (const file of FILES) {
      expect(/localStorage|sessionStorage|indexedDB/.test(file.text), file.name).toBe(false);
    }
  });

  it("never injects raw HTML", () => {
    for (const file of FILES) {
      expect(file.text.includes("dangerouslySetInnerHTML"), file.name).toBe(false);
    }
  });

  it("uses no inline style attributes, which the Content Security Policy forbids", () => {
    for (const file of FILES) {
      expect(/\sstyle=\{\{/.test(file.text), file.name).toBe(false);
    }
  });

  it("has generated API types that match frontend/openapi.json", async () => {
    const schema = new URL(`file:///${join(FRONTEND, "openapi.json").replace(/\\/g, "/")}`);
    const expected = astToString(await openapiTS(schema));
    const committed = readFileSync(GENERATED, "utf8");
    const body = (text: string) => text.slice(text.indexOf("export"));
    expect(body(committed).replace(/\r\n/g, "\n")).toBe(body(expected).replace(/\r\n/g, "\n"));
  });
});
