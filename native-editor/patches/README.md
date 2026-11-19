# Zod 3 upper-bound backport

The embedded editor requires Zod 3's function API. Upgrading its dependency to Zod 4 without adapting the SDK breaks that API.

GHSA-mrhx-c7xc-m3w5 / CVE-2023-54404 is reported by npm for Zod <4.6.6. The upstream [fix a0ebf970f2d752e5f58527cd2942ff48be4f46bd](https://github.com/colinhacks/zod/commit/a0ebf970f2d752e5f58527cd2942ff48be4f46bd) makes collection upper bounds fail before element validation. This local backport applies that behavior to Zod 3.25.76's bounded arrays (max/exact length) and sets (max/size), preserving its function API.

`scripts/security-patch.mjs` checks the exact original or patched SHA-256 for ESM, CommonJS and TypeScript source files. A changed vendor file or version blocks the build. It does not execute an unverified downloaded script. Run it explicitly before tests and the native build; lifecycle installation scripts remain disabled.

The manifest records all insertion offsets and original/patched hashes. No upstream copyright or license file is removed. Zod is MIT; retain its copyright and license with the bundled distribution. The added gate is local project code informed by the upstream change.

Tests first reproduced six failures, then exercise ESM/CommonJS sync/async rejection before visiting oversized collections, while valid collections and legacy function APIs still work. This is a bounded regression check, not an attempt to crash a shared host with an out-of-memory payload.

Limits: unconstrained collections still need input-size limits, as do arbitrarily deep documents. Zod 3 maps do not expose the same size API as Zod 4. npm still reports the installed version as affected; the local backport is a documented mitigation, not an official patched Zod release or a zero-advisory claim. Real municipal deployment requires a fresh review of the SDK and all remaining advisory paths. The hosted staging uses only fictitious data and authenticated access.
