import { AccordionGroup, Column } from "@once-ui-system/core";
import { faq } from "@/content/faq";
import { SectionTitle } from "./SectionTitle";

export const Faq = ({ ...flex }: React.ComponentProps<typeof Column>) => (
  <Column fillWidth gap="40" {...flex}>
    <SectionTitle eyebrow="FAQ" title="Questions people ask first" />
    <AccordionGroup fillWidth background="surface" items={faq} />
  </Column>
);
