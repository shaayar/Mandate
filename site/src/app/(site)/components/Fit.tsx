import { Column, Grid, Heading, Icon, Text } from "@once-ui-system/core";
import type { IconName } from "@/resources/icons";
import { SectionTitle } from "./SectionTitle";

const cases: { icon: IconName; situation: string; answer: string; highlight?: boolean }[] = [
  {
    icon: "terminal",
    situation: "You use a coding agent someone else built",
    answer:
      "Use its permission settings and hooks. They sit where that agent calls its tools; Mandate is for agents you build.",
  },
  {
    icon: "organization",
    situation: "You need one policy platform across a company",
    answer:
      "Look at general policy engines such as OPA or Cedar, or a full agent governance toolkit. Mandate is one library for one boundary.",
  },
  {
    icon: "code",
    situation: "You write your own agent's tool loop in Python",
    answer:
      "That's Mandate. One dependency, no server, policies in YAML, and approvals that can't be replayed.",
    highlight: true,
  },
];

export const Fit = ({ ...flex }: React.ComponentProps<typeof Column>) => (
  <Column fillWidth gap="40" {...flex}>
    <SectionTitle
      eyebrow="Where it fits"
      title="Small on purpose"
      lead="Mandate does one job: deciding at the tool-call boundary. Sometimes a different tool is the right one."
    />
    <Grid fillWidth columns={3} m={{ columns: 1 }} gap="12">
      {cases.map((item) => (
        <Column
          key={item.situation}
          fillWidth
          gap="12"
          padding="32"
          radius="xl"
          border={item.highlight ? "brand-alpha-medium" : "neutral-alpha-weak"}
          background={item.highlight ? "brand-alpha-weak" : "surface"}
        >
          <Icon
            name={item.icon}
            size="s"
            marginBottom="8"
            onBackground={item.highlight ? "brand-medium" : "neutral-medium"}
          />
          <Heading as="h3" variant="heading-strong-m" wrap="balance">
            {item.situation}
          </Heading>
          <Text onBackground="neutral-weak" variant="body-default-s" wrap="balance">
            {item.answer}
          </Text>
        </Column>
      ))}
    </Grid>
  </Column>
);
