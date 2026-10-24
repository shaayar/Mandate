import { Button, Media, Row, SmartLink, Text, ToggleButton } from "@once-ui-system/core";
import { repoUrl, schema } from "@/resources";

const sections = [
  { href: "/#how-it-works", label: "How it works" },
  { href: "/#approvals", label: "Approvals" },
  { href: "/#guarantees", label: "Guarantees" },
  { href: "/#faq", label: "FAQ" },
];

/**
 * The Authority Gate mark and the name, linking home. The brand guide calls
 * for the icon-only mark on compact surfaces; the mark is a copy of
 * assets/logos/mandate-authority-gate.svg.
 */
export const Wordmark: React.FC = () => (
  <SmartLink href="/" unstyled aria-label={`${schema.name} home`}>
    <Row gap="8" vertical="center">
      <Media src="/brand/mandate-mark.svg" alt="" width={1.5} height={1.5} unoptimized />
      <Text
        variant="heading-strong-s"
        onBackground="neutral-strong"
        style={{ letterSpacing: "0.14em", textTransform: "uppercase" }}
      >
        {schema.name}
      </Text>
    </Row>
  </SmartLink>
);

export const Header: React.FC = () => (
  <Row
    as="header"
    fillWidth
    horizontal="center"
    position="sticky"
    zIndex={2}
    background="page"
    borderBottom
  >
    <Row
      maxWidth="l"
      paddingX="l"
      paddingY="12"
      vertical="center"
      horizontal="between"
      s={{ paddingX: "16" }}
    >
      <Wordmark />
      <Row gap="4" vertical="center">
        <Row as="nav" aria-label="Sections" gap="4" vertical="center" m={{ hide: true }}>
          {sections.map((section) => (
            <ToggleButton key={section.href} href={section.href} label={section.label} />
          ))}
        </Row>
        <Button size="s" variant="secondary" prefixIcon="github" href={repoUrl} label="GitHub" />
      </Row>
    </Row>
  </Row>
);
