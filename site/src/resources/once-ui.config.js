import { site } from "./seo";

// IMPORTANT: Replace with your own domain address - it's used for SEO in meta tags and schema
const baseURL = "https://mandate.example";

// Brand typography (assets/guidelines/BRAND_GUIDE.md): Space Grotesk for
// headings, Inter for body and UI.
import { Geist_Mono, Inter, Space_Grotesk } from "next/font/google";

const heading = Space_Grotesk({
  variable: "--font-heading",
  subsets: ["latin", "latin-ext"],
  display: "swap",
});

const body = Inter({
  variable: "--font-body",
  subsets: ["latin", "latin-ext"],
  display: "swap",
});

const label = Inter({
  variable: "--font-label",
  subsets: ["latin", "latin-ext"],
  display: "swap",
});

const code = Geist_Mono({
  variable: "--font-code",
  subsets: ["latin", "latin-ext"],
  display: "swap",
});

const fonts = {
  heading: heading,
  body: body,
  label: label,
  code: code,
};

// The app's languages, as BCP 47 tags ("en", "hu", "de-AT"). The first is the
// default: it sets <html lang>, how prices are formatted and which entry of
// each labels file (src/content/<surface>/labels.ts) the UI shows. More than
// one turns on language URLs (/hu/store) when the app has the i18n slice;
// without it the app always renders the first.
const i18n = {
  locales: ["en"],
};

// default customization applied to the HTML in the main layout.tsx
const style = {
  theme: "system", // dark | light - not needed when using ThemeProvider
  neutral: "slate", // sand | gray | slate
  // Brand palette (assets/guidelines/BRAND_GUIDE.md): Electric Teal and
  // Deep Teal on Midnight Navy.
  brand: "custom",
  brandSeed: "#14DBA6",
  accent: "custom",
  accentSeed: "#0E8F80",
  pageBackground: { dark: "#0B1F26" },
  surfaceBackground: { dark: "#10252B" },
  solid: "contrast", // color | contrast | inverse
  solidStyle: "flat", // flat | plastic
  border: "conservative", // rounded | playful | conservative
  surface: "filled", // filled | translucent
  transition: "all", // all | micro | macro
  scaling: "100", // 90 | 95 | 100 | 105 | 110
};

const dataStyle = {
  variant: "gradient", // flat | gradient | outline
  mode: "categorical", // categorical | divergent | sequential
  height: 24, // default chart height
  axis: {
    stroke: "var(--neutral-alpha-weak)",
  },
  tick: {
    fill: "var(--neutral-on-background-weak)",
    fontSize: 11,
    line: false
  },
};

// default schema data
const schema = {
  logo: "",
  type: "Organization",
  name: "Mandate",
  description: site.home.description,
  email: "",
};

/** @type {{ name: string; icon: import("@once-ui-system/core").IconName; link: string }[]} */
const social = [
  // Links are automatically displayed.
  // Import new icons in /once-ui/icons.ts
  {
    name: "GitHub",
    icon: "github",
    link: "https://github.com/shaayar/Mandate",
  },
];

export { baseURL, fonts, i18n, style, schema, social, dataStyle };
