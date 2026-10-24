import { Column, Row, SmartLink, Text } from "@once-ui-system/core";
import { repoUrl, schema } from "@/resources";
import { Wordmark } from "./Header";

export const Footer = () => (
  <Column as="footer" fillWidth horizontal="center" borderTop>
    <Row
      maxWidth="l"
      paddingX="l"
      paddingY="40"
      gap="24"
      vertical="center"
      horizontal="between"
      s={{ direction: "column", horizontal: "center", paddingX: "16" }}
    >
      <Column gap="8" s={{ horizontal: "center" }}>
        <Wordmark />
        <Text variant="body-default-s" onBackground="neutral-weak">
          Policy enforcement for AI agents.
        </Text>
      </Column>
      <Row gap="24" textVariant="label-default-s" wrap horizontal="center">
        <SmartLink href="/#how-it-works">How it works</SmartLink>
        <SmartLink href="/#guarantees">Guarantees</SmartLink>
        <SmartLink href="/#faq">FAQ</SmartLink>
        <SmartLink href={repoUrl}>GitHub</SmartLink>
      </Row>
    </Row>
    <Row
      maxWidth="l"
      paddingX="l"
      paddingBottom="24"
      textVariant="label-default-s"
      onBackground="neutral-weak"
      s={{ horizontal: "center", paddingX: "16" }}
    >
      © {new Date().getFullYear()} {schema.name}
    </Row>
  </Column>
);
