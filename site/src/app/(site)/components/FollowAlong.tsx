import { Background, Button, Column, Heading, Row, Text } from "@once-ui-system/core";
import { designDocUrl, repoUrl } from "@/resources";

/** The page's call to action: follow the public repository. */
export const FollowAlong = ({ ...flex }: React.ComponentProps<typeof Column>) => (
  <Column
    fillWidth
    gap="24"
    paddingX="40"
    paddingY="64"
    radius="xl"
    border
    overflow="hidden"
    horizontal="center"
    align="center"
    s={{ paddingX: "24" }}
    {...flex}
  >
    <Background
      position="absolute"
      top="0"
      left="0"
      fill
      pointerEvents="none"
      gradient={{
        display: true,
        colorStart: "brand-alpha-medium",
        colorEnd: "static-transparent",
        x: 50,
        y: 100,
        width: 120,
        height: 100,
        opacity: 50,
      }}
    />
    <Column zIndex={1} maxWidth="xs" gap="12" horizontal="center">
      <Heading as="h2" variant="display-strong-xs" wrap="balance">
        Follow along
      </Heading>
      <Text variant="body-default-m" onBackground="neutral-weak" wrap="balance">
        Mandate is built in the open. Watch the repository and choose Custom, then Releases, to
        hear about each release, or read the design it is built and tested against.
      </Text>
    </Column>
    <Row zIndex={1} gap="12" s={{ direction: "column" }}>
      <Button href={repoUrl} prefixIcon="github" arrowIcon>
        Watch on GitHub
      </Button>
      <Button variant="secondary" href={designDocUrl} suffixIcon="arrowUpRight">
        Read the design
      </Button>
    </Row>
  </Column>
);
