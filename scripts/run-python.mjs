// Pick the first Python with `ssl`, then exec the given script.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";

const candidates = [
  process.env.PYTHON,
  "/opt/homebrew/bin/python3",
  "/usr/local/bin/python3",
  "python3",
  "python",
].filter(Boolean);

function works(py) {
  const r = spawnSync(py, ["-c", "import ssl, urllib.request"], { stdio: "ignore" });
  return r.status === 0;
}

const py = candidates.find((p) => {
  if (p.startsWith("/")) return existsSync(p) && works(p);
  return works(p);
});

if (!py) {
  console.error(
    "No Python with SSL support found. Set $PYTHON or install via Homebrew (`brew install python`).",
  );
  process.exit(2);
}

const args = process.argv.slice(2);
const r = spawnSync(py, args, { stdio: "inherit" });
process.exit(r.status ?? 1);
