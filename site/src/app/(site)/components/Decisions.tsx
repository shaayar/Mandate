import { Column, Grid, Heading, Icon, Row, Text } from "@once-ui-system/core";
import type { IconName } from "@/resources/icons";
import { SectionTitle } from "./SectionTitle";

type Scheme = "success" | "danger" | "warning";

const decisions: { name: string; icon: IconName; scheme: Scheme; description: string }[] = [
  {
    name: "ALLOW",
    icon: "check",
    scheme: "success",
    description: "The call matches a rule that permits it. Your dispatcher runs the tool.",
  },
  {
    name: "DENY",
    icon: "close",
    scheme: "danger",
    description: "A rule forbids the call, or no rule allows it. The tool does not run.",
  },
  {
    name: "REQUIRE_APPROVAL",
    icon: "person",
    scheme: "warning",
    description: "The call may run once a person approves it. Until then, it doesn't.",
  },
];

const precedence = ["Explicit deny", "Require approval", "Allow", "Nothing matched: deny"];

export const Decisions = ({ ...flex }: React.ComponentProps<typeof Column>) => (
  <Column fillWidth gap="40" {...flex}>
    <SectionTitle
      eyebrow="How it works"
      title="Your agent proposes. Mandate decides."
      lead="Choosing a tool is a proposal, not permission. Call the guard in your dispatcher, before the tool executes, and enforce the answer it gives."
    />
    <Grid fillWidth columns={3} m={{ columns: 1 }} gap="12">
      {decisions.map((decision) => (
        <Column
          key={decision.name}
          fillWidth
          gap="12"
          padding="32"
          radius="xl"
          border="neutral-alpha-weak"
          background="surface"
        >
          <Row gap="12" vertical="center" marginBottom="8">
            <Icon
              name={decision.icon}
              size="s"
              padding="8"
              radius="m"
              border={`${decision.scheme}-alpha-weak`}
              background={`${decision.scheme}-alpha-weak`}
              onBackground={`${decision.scheme}-medium`}
            />
            <Text variant="code-strong-s" onBackground={`${decision.scheme}-medium`}>
              {decision.name}
            </Text>
          </Row>
          <Text onBackground="neutral-weak" variant="body-default-s" wrap="balance">
            {decision.description}
          </Text>
        </Column>
      ))}
    </Grid>
    <Column fillWidth gap="16" padding="24" radius="xl" border="neutral-alpha-weak">
      <Heading as="h3" variant="heading-strong-s">
        One precedence rule, across every policy file
      </Heading>
      <Row gap="8" vertical="center" wrap>
        {precedence.map((step, index) => (
          <Row key={step} gap="8" vertical="center">
            {index > 0 && <Icon name="chevronRight" size="xs" onBackground="neutral-weak" />}
            <Row
              paddingX="12"
              paddingY="4"
              radius="full"
              background="neutral-alpha-weak"
              textVariant="label-default-s"
              onBackground="neutral-strong"
            >
              {step}
            </Row>
          </Row>
        ))}
      </Row>
      <Text variant="body-default-s" onBackground="neutral-weak">
        Policies are plain YAML or JSON: no <Text variant="code-default-s">eval</Text>, no policy
        language to learn, and every change shows up in a pull request. An evaluation error never
        produces an allow.
      </Text>
    </Column>
  </Column>
);
