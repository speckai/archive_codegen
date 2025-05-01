#!/usr/bin/env node

import { findFilePathForRoute } from "./routeToFile";

const route = process.argv[2];
const baseDir = process.argv[3];

if (!route || !baseDir) {
  console.error("Usage: find-route-file-next <route> <base-directory>");
  console.error("Example: find-route-file-next /blog/my-post ./");
  process.exit(1);
}

// Add debug logging
console.error(`Searching for route: "${route}" in directory: "${baseDir}"`);

// Normalize the route - ensure single forward slash for root route
const normalizedRoute =
  route === "/" ? "/" : route.replace(/\/+/g, "/").replace(/\/$/, "");

const filePath = findFilePathForRoute(normalizedRoute, baseDir);

if (filePath) {
  console.log(filePath);
} else {
  console.error(`No file found for route: ${normalizedRoute}`);
  process.exit(1);
}
