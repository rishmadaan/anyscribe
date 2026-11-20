/** A transcript's History slug (its file name without .md), from a path
 * written with either / (macOS, Linux) or \ (Windows). */
export const transcriptSlug = (filePath: string) =>
  (filePath.split(/[\\/]/).pop() ?? "").replace(/\.md$/, "");
