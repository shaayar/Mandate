import { Column, Grid, Heading, Icon, Row, Text } from "@once-ui-system/core";
import { CodeBlock } from "@once-ui-system/core/code";
import type { IconName } from "@/resources/icons";
import { SectionTitle } from "./SectionTitle";

const rules: { icon: IconName; title: string; description: string }[] = [
  {
    icon: "link",
    title: "Bound to the exact call",
    description:
      "Tool name, parameters and context. Change one parameter and it is a new request.",
  },
  {
    icon: "lock",
    title: "Used once",
    description:
      "Consuming an approval is atomic. Two concurrent attempts cannot both run the tool.",
  },
  {
    icon: "time",
    title: "Expires",
    description: "An approval left unused past its window authorizes nothing.",
  },
  {
    icon: "refresh",
    title: "Retries ask again",
    description: "If the tool fails after running, a retry needs a fresh approval.",
  },
];

const timeline = `approval = guard.request_approval(
    "data_export", {"dest": "s3://reports"}
)

# A different destination is a different call:
guard.is_approval_valid(
    approval["id"], "data_export", {"dest": "s3://elsewhere"}
)  # False

guard.consume_approval(approval["id"])  # True: runs once
guard.consume_approval(approval["id"])  # False: already used`;

export const Approvals = ({ ...flex }: React.ComponentProps<typeof Column>) => (
  <Column fillWidth gap="40" {...flex}>
    <SectionTitle
      eyebrow="Approvals"
      title="A yes means this call, once"
      lead="Many approval flows stop at a yes/no prompt. In Mandate, a person's yes authorizes exactly the call they reviewed, one time."
    />
    <Row fillWidth gap="24" m={{ direction: "column" }}>
      <Grid fillWidth columns={2} s={{ columns: 1 }} gap="12">
        {rules.map((rule) => (
          <Column
            key={rule.title}
            fillWidth
            gap="8"
            padding="24"
            radius="xl"
            border="neutral-alpha-weak"
            background="surface"
          >
            <Icon
              name={rule.icon}
              size="s"
              padding="8"
              radius="m"
              border="brand-alpha-weak"
              background="brand-alpha-weak"
              onBackground="brand-medium"
              marginBottom="12"
            />
            <Heading as="h3" variant="heading-strong-s">
              {rule.title}
            </Heading>
            <Text onBackground="neutral-weak" variant="body-default-s" wrap="balance">
              {rule.description}
            </Text>
          </Column>
        ))}
      </Grid>
      <Column fillWidth gap="12">
        <CodeBlock
          fillWidth
          fillHeight
          background="page"
          radius="xl"
          copyButton
          codes={[{ code: timeline, language: "python", label: "replay.py" }]}
        />
      </Column>
    </Row>
  </Column>
);
