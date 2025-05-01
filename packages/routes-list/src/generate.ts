#!/usr/bin/env node
import { writeFileSync } from "node:fs";
import { getNextRoutes } from "./getRoutes";

const routes = getNextRoutes();

console.log(JSON.stringify(routes, null, 2));

// If an output file path is supplied via the '-o' flag, write to that file:
if (process.argv[2] === "-o") {
  const outputPath = process.argv[3];
  if (outputPath) {
    writeFileSync(
      outputPath,
      `export const routes = ${JSON.stringify(routes)};`,
    );
    console.log(`Routes list save to ${outputPath}`);
  }
}
