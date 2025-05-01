Gets all available routes in Next

```bash
pnpm build
```

```bash
pnpm publish
```

## Install

```bash
pnpm install --save-dev list-routes@latest
```

Or run once without installing:

```bash
pnpm dlx list-routes@latest
```

## Usage

### Step 1. Run script

Add script to `package.json`:

```json
{
  "script": {
    "generate-list-routes": "generate-list-routes"
  }
}
```

Or if you using `src` directory:

```json
{
  "script": {
    "generate-list-routes": "cd src && npx generate-list-routes"
  }
}
```

Or if you want specify the output file:

```json
{
  "script": {
    "generate-list-routes": "generate-list-routes -o routes.ts"
  }
}
```

Then run npm script:

```shell
pnpm run generate-list-routes
```

### Step 2. Import routes

```ts
import { routes } from "list-routes";
// or if you specify the output file
import { routes } from "./routes.ts";

console.log(routes);
/**
[
  '/',
  '/about',
  '/posts/[id]',
  ...
]
*/
```

## Options

| Option | Type   | Description                     | Example                                      |
| ------ | ------ | ------------------------------- | -------------------------------------------- |
| `-o`   | string | set the output routes file path | `npx generate-list-routes-next -o routes.ts` |

## Finding Imports

To find which files import a specific file:

```bash
npx find-imports-next <base-directory> <tsconfig-path> <relative-path-to-target-file>
```

Example:

```bash
npx find-imports-next ./src ./tsconfig.json components/Button.tsx
```

This will output a list of all files that import the specified target file.

## Finding File Path for a Route

To find the corresponding file path for a given route:

```bash
npx find-route-file-next <route> [base-directory]
```

Example:

```bash
npx find-route-file-next /blog/my-post ./src
```

This will output the file path that corresponds to the given route. For example:

```bash
/src/app/blog/[slug]/page.tsx
```

The tool handles:

- App Router routes (`/app` directory)
- Pages Router routes (`/pages` directory)
- Dynamic routes (e.g., `[slug]`, `[...catchAll]`)
- Route groups (directories with parentheses)
- Parallel routes (`@folder`)
- Intercepting routes

## Development

### Local Setup

1. Build the package:

```bash
pnpm build
```

2. Link the package globally:

```bash
npm link
```

3. Now you can use the CLI commands locally:

```bash
npx generate-list-routes-next
npx find-imports-next
npx find-route-file-next
```

### Making Changes

1. Make your changes in the source files
2. Rebuild the package:

```bash
pnpm build
```

3. The linked projects will automatically use the new version

### Unlinking

To remove the global link:

```bash
pnpm unlink --global list-routes-next
```

### Alternative: Local Installation

Instead of linking, you can install directly from the local filesystem:

```bash
pnpm add --save-dev /absolute/path/to/packages/routes-list
```
