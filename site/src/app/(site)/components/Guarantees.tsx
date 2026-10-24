import { Column, Grid, Heading, Icon, Row, Text } from "@once-ui-system/core";
import type { IconName } from "@/resources/icons";
import { SectionTitle } from "./SectionTitle";

const columns: {
  icon: IconName;
  bullet: IconName;
  highlight?: boolean;
  title: string;
  lead: string;
  items: string[];
}[] = [
  {
    icon: "security",
    bullet: "check",
    highlight: true,
    title: "Mandate guarantees",
    lead: "Inside the boundary, for every call that goes through the guard.",
    items: [
      "Default-deny: no matching allow rule means DENY",
      "Explicit deny wins over every other rule, in every file",
      "Evaluation errors and invalid policies never produce ALLOW",
      "Approvals are bound to one call, single-use and expiring",
      "An audit event for every decision, with best-effort secret redaction",
    ],
  },
  {
    icon: "code",
    bullet: "arrowRight",
    title: "Your integration must",
    lead: "Mandate decides. The code that calls your tools enforces.",
    items: [
      "Route every protected tool through the guard",
      "Enforce the decision in the real dispatch path",
      "Show approval requests to a person and return the answer",
      "Persist approvals if they must survive a restart",
    ],
  },
  {
    icon: "warning",
    bullet: "minus",
    title: "Other layers handle",
    lead: "An authorization layer is not a sandbox.",
    items: [
      "OS and process isolation",
      "Network egress, redirects and SSRF",
      "Path traversal inside tool implementations",
      "Secrets storage and credential management",
      "Tools called without going through the guard",
    ],
  },
];

export const Guarantees = ({ ...flex }: React.ComponentProps<typeof Column>) => (
  <Column fillWidth gap="40" {...flex}>
    <SectionTitle
      eyebrow="Guarantees"
      title="What Mandate guarantees, and what it doesn't"
      lead="Security tools earn trust by being exact about their edges. These are the guarantees Mandate is designed and tested against; the repository tracks which ones still need hardening."
    />
    <Grid fillWidth columns={3} m={{ columns: 1 }} gap="12">
      {columns.map((column) => (
        <Column
          key={column.title}
          fillWidth
          gap="16"
          padding="32"
          radius="xl"
          border={column.highlight ? "brand-alpha-medium" : "neutral-alpha-weak"}
          background={column.highlight ? "brand-alpha-weak" : "surface"}
        >
          <Row gap="12" vertical="center">
            <Icon name={column.icon} size="s" onBackground={column.highlight ? "brand-medium" : "neutral-medium"} />
            <Heading as="h3" variant="heading-strong-m">
              {column.title}
            </Heading>
          </Row>
          <Text variant="body-default-s" onBackground="neutral-weak">
            {column.lead}
          </Text>
          <Column as="ul" fillWidth gap="12" margin="0" padding="0" style={{ listStyle: "none" }}>
            {column.items.map((item) => (
              <Row as="li" key={item} gap="8" textVariant="body-default-s" onBackground="neutral-strong">
                <Icon
                  name={column.bullet}
                  size="xs"
                  marginTop="2"
                  onBackground={column.highlight ? "brand-medium" : "neutral-weak"}
                />
                {item}
              </Row>
            ))}
          </Column>
        </Column>
      ))}
    </Grid>
  </Column>
);
