/**
 * Portions Copyright 2014-2022 Grist Labs Inc. Apache-2.0.
 * Source: gristlabs/grist-core commit a3c557ac1bc4bd55b9b9d4333842bec255586ff4.
 * Files: app/common/gutil.ts and app/client/lib/sanitizeUrl.ts.
 * Changes: TypeScript annotations removed; function bodies unchanged.
 * Licence/notice: GRIST-LICENSE.txt and GRIST-NOTICE.txt in this directory.
 */
export function tryParseUrl(url) {
  try { return new URL(url ?? ""); } catch { return undefined; }
}

export function sanitizeHttpUrl(url) {
  const parsedUrl = tryParseUrl(url);
  if (!parsedUrl || !["http:", "https:"].includes(parsedUrl.protocol)) {
    return null;
  }

  return parsedUrl.href;
}
