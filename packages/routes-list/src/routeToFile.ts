#!/usr/bin/env node
import ignore from "ignore";
import listPaths from "list-paths";
import * as fs from "node:fs";
import { existsSync } from "node:fs";
import * as path from "node:path";

interface RouteMapping {
  route: string;
  filePath: string;
}

// Add the loadGitignore function
function loadGitignore(baseDir: string) {
  const ig = ignore();
  const gitignorePath = path.join(baseDir, ".gitignore");

  if (fs.existsSync(gitignorePath)) {
    const gitignoreContent = fs.readFileSync(gitignorePath, "utf8");
    ig.add(gitignoreContent);
  }

  // Always ignore node_modules regardless of gitignore
  ig.add("node_modules");

  return ig;
}

function getProjectRoots(baseDir: string): string[] {
  const roots = [];

  // Check for common Next.js directory structures
  const possiblePaths = [
    "", // ./app or ./pages
    "src/", // ./src/app or ./src/pages
    "source/", // ./source/app or ./source/pages
  ];

  for (const prefix of possiblePaths) {
    const fullPath = path.join(baseDir, prefix);
    if (
      existsSync(path.join(fullPath, "app")) ||
      existsSync(path.join(fullPath, "pages"))
    ) {
      roots.push(fullPath);
    }
  }

  return roots;
}

export function getRouteToFileMappings(
  baseDir = "./",
  extensions = ["tsx", "ts", "js", "jsx", "mdx"],
): RouteMapping[] {
  const mappings: RouteMapping[] = [];
  const ig = loadGitignore(baseDir);

  // Get all possible root directories
  const projectRoots = getProjectRoots(baseDir);

  for (const root of projectRoots) {
    // App router mappings
    if (existsSync(path.join(root, "app"))) {
      const appPaths = listPaths(path.join(root, "app"), { includeFiles: true })
        .filter((filePath) => {
          // Convert absolute path to relative path for ignore filtering
          const relativePath = path.relative(baseDir, filePath);
          return !ig.ignores(relativePath);
        })
        .filter((path) => {
          const file = path.split("/").at(-1);
          const filename = file?.split(".").at(-2);
          const extension = file?.split(".").at(-1);
          return (
            extension && extensions.includes(extension) && filename === "page"
          );
        });

      for (const filePath of appPaths) {
        const parts = filePath.split(root)[1]?.split("/").filter(Boolean) ?? [];
        const url: string[] = [];
        let shouldInclude = true;

        for (let i = 0; i < parts.length; i++) {
          const part = parts[i];
          if (!part) {
            continue;
          }

          if (i === 0 && part === "app") {
            continue;
          }

          // Skip the file if it's in a private route
          if (part.startsWith("_")) {
            shouldInclude = false;
            break;
          }

          // Skip group segments in the route but keep the file
          if (part.startsWith("(") && part.endsWith(")")) {
            continue;
          }

          // Skip intercepting routes
          if (part.startsWith("(") && !part.endsWith(")")) {
            shouldInclude = false;
            break;
          }

          // Skip parallel routes
          if (part.startsWith("@")) {
            shouldInclude = false;
            break;
          }

          // Skip the page.tsx part in the route
          if (i === parts.length - 1) continue;

          url.push(part);
        }

        if (shouldInclude) {
          mappings.push({
            route: `/${url.join("/")}`,
            filePath: filePath,
          });
        }
      }
    }

    // Pages router mappings
    if (existsSync(path.join(root, "pages"))) {
      const pagePaths = listPaths(path.join(root, "pages"), {
        includeFiles: true,
      })
        .filter((filePath) => {
          const relativePath = path.relative(baseDir, filePath);
          return !ig.ignores(relativePath);
        })
        .filter((path) => {
          if (path?.includes("/pages/api/")) {
            return false;
          }
          const file = path.split("/").at(-1);
          const extension = file?.split(".").at(-1);
          return extension && extensions.includes(extension);
        });

      for (const filePath of pagePaths) {
        const parts = filePath.split(root)[1]?.split("/").filter(Boolean) ?? [];
        const url: string[] = [];

        for (let i = 0; i < parts.length; i++) {
          let part = parts[i];
          if (!part) {
            continue;
          }

          if (i === 0 && part === "pages") {
            continue;
          }

          if (i === parts.length - 1) {
            part = part.split(".").at(-2) ?? "";
            if (part === "index") {
              continue;
            }
          }

          url.push(part);
        }

        mappings.push({
          route: `/${url.join("/")}`,
          filePath: filePath,
        });
      }
    }
  }

  return mappings;
}

export function findFilePathForRoute(route: string, src = "./"): string | null {
  // Resolve the source directory to an absolute path
  const absoluteSrc = path.resolve(src);

  const mappings = getRouteToFileMappings(absoluteSrc);

  // First try exact match
  const exactMatch = mappings.find((m) => m.route === route);
  if (exactMatch) {
    return exactMatch.filePath;
  }

  // If no exact match, try matching dynamic routes
  for (const mapping of mappings) {
    const routeParts = route.split("/").filter(Boolean);
    const mappingParts = mapping.route.split("/").filter(Boolean);

    if (routeParts.length !== mappingParts.length) {
      continue;
    }

    let matches = true;
    for (let i = 0; i < routeParts.length; i++) {
      const routePart = routeParts[i];
      const mappingPart = mappingParts[i];

      // If mapping part is dynamic (contains [ ]) then it matches anything
      if (mappingPart.includes("[") && mappingPart.includes("]")) {
        continue;
      }

      // Otherwise parts should match exactly
      if (routePart !== mappingPart) {
        matches = false;
        break;
      }
    }

    if (matches) {
      return mapping.filePath;
    }
  }

  return null;
}
