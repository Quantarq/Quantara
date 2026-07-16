/// <reference types="vite/client" />
/// <reference types="vite-plugin-svgr/client" />

// ── SVG imports ──────────────────────────────────────────────────────────────
// Plain SVG import → string URL (e.g. `import logo from './logo.svg'`)
declare module '*.svg' {
  const src: string;
  export default src;
}

// SVG imported as a React component via vite-plugin-svgr
// (e.g. `import { ReactComponent as Logo } from './logo.svg?react'`)
declare module '*.svg?react' {
  import type { FC, SVGProps } from 'react';
  const ReactComponent: FC<SVGProps<SVGSVGElement>>;
  export { ReactComponent };
  export default ReactComponent;
}

// ── Image assets ─────────────────────────────────────────────────────────────
declare module '*.png' {
  const src: string;
  export default src;
}

declare module '*.jpg' {
  const src: string;
  export default src;
}

declare module '*.jpeg' {
  const src: string;
  export default src;
}

declare module '*.gif' {
  const src: string;
  export default src;
}

declare module '*.webp' {
  const src: string;
  export default src;
}

// ── CSS modules ──────────────────────────────────────────────────────────────
declare module '*.module.css' {
  const classes: Record<string, string>;
  export default classes;
}

declare module '*.module.scss' {
  const classes: Record<string, string>;
  export default classes;
}

// ── Environment variables ────────────────────────────────────────────────────
// Extend the Vite-generated ImportMetaEnv with project-specific env vars so
// that `import.meta.env.VITE_*` accesses are type-safe.
interface ImportMetaEnv {
  /** Backend API base URL */
  readonly VITE_API_URL: string;
  /** Stellar network identifier (testnet | mainnet | futurenet) */
  readonly VITE_STELLAR_NETWORK: string;
  /** Stellar Horizon REST API URL */
  readonly VITE_STELLAR_HORIZON_URL: string;
  /** Soroban RPC endpoint */
  readonly VITE_STELLAR_SOROBAN_RPC_URL: string;
  // Add further VITE_* vars here as they are introduced.
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
