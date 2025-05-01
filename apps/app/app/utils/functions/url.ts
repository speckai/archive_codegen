/**
 * Extracts the display URL from a path by removing the preview-related segments
 * @param path The full path including preview segments
 * @returns The cleaned display URL
 */
export const getDisplayUrl = (path: string): string => {
  const pathParts = path.split("/").filter(Boolean);
  const previewIndex = pathParts.indexOf("preview");
  if (previewIndex !== -1 && pathParts.length >= previewIndex + 3) {
    const displayPath = pathParts.slice(previewIndex + 3);
    return displayPath.length > 0 ? "/" + displayPath.join("/") : "/";
  }
  return path;
};
