import { Column, Meta, Schema } from "@once-ui-system/core";
import { baseURL, site } from "@/resources";
import {
  Approvals,
  Decisions,
  Faq,
  Fit,
  FollowAlong,
  Guarantees,
  Hero,
} from "./components";

export async function generateMetadata() {
  return Meta.generate({
    title: site.home.title,
    description: site.home.description,
    baseURL: baseURL,
    path: site.home.path,
    canonical: site.home.canonical,
    image: site.home.image,
    robots: site.home.robots,
    alternates: site.home.alternates,
  });
}

export default function Home() {
  return (
    <Column fillWidth horizontal="center" gap="104" paddingBottom="104">
      <Schema
        as="webPage"
        baseURL={baseURL}
        title={site.home.title}
        description={site.home.description}
        path={site.home.path}
      />
      <Hero paddingX="l" s={{ paddingX: "16" }} />
      <Decisions id="how-it-works" maxWidth="l" paddingX="l" s={{ paddingX: "16" }} />
      <Approvals id="approvals" maxWidth="l" paddingX="l" s={{ paddingX: "16" }} />
      <Guarantees id="guarantees" maxWidth="l" paddingX="l" s={{ paddingX: "16" }} />
      <Fit id="fit" maxWidth="l" paddingX="l" s={{ paddingX: "16" }} />
      <Faq id="faq" maxWidth="l" paddingX="l" s={{ paddingX: "16" }} />
      <Column fillWidth maxWidth="l" paddingX="l" s={{ paddingX: "16" }}>
        <FollowAlong />
      </Column>
    </Column>
  );
}
