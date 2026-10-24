import { Column, Heading, Text } from "@once-ui-system/core";

interface SectionTitleProps extends Omit<React.ComponentProps<typeof Column>, "title"> {
  eyebrow: string;
  title: React.ReactNode;
  lead?: React.ReactNode;
}

/** Left-aligned eyebrow, title and lead that open each section. */
export const SectionTitle: React.FC<SectionTitleProps> = ({ eyebrow, title, lead, ...flex }) => (
  <Column maxWidth={40} gap="12" {...flex}>
    <Text variant="label-default-s" onBackground="brand-medium">
      {eyebrow}
    </Text>
    <Heading as="h2" variant="display-strong-xs" wrap="balance">
      {title}
    </Heading>
    {lead && (
      <Text variant="body-default-l" onBackground="neutral-weak" wrap="balance">
        {lead}
      </Text>
    )}
  </Column>
);
