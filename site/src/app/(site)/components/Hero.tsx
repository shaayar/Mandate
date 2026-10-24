import { Background, Button, Column, Heading, Row, Tag, Text } from "@once-ui-system/core";
import { CodeBlock } from "@once-ui-system/core/code";
import { installCommand, repoUrl } from "@/resources";

const policy = `# policies/agent.yaml
# Anything no rule allows is denied.
rules:
  - name: never_delete
    action: deny
    condition:
      tool_name: file_delete

  - name: exports_need_a_person
    action: require_approval
    condition:
      tool_name: data_export

  - name: github_api_only
    action: allow
    condition:
      tool_name: http_get
      parameters:
        url:
          operator: regex
          value: '^https://api\\.github\\.com/'`;

const dispatch = `from mandate import Guard, ALLOW, REQUIRE_APPROVAL

guard = Guard(
    policies=["policies/agent.yaml"],
    approval_mechanism=ask_a_person,
)

def call_tool(name, args):
    result = guard.evaluate(name, args)

    if result["decision"] == REQUIRE_APPROVAL:
        approval = guard.request_approval(name, args)
        if not guard.consume_approval(approval["id"]):
            raise PermissionError("not approved")
    elif result["decision"] != ALLOW:
        raise PermissionError(result["reason"])  # DENY

    return TOOLS[name](**args)`;

export const Hero: React.FC<React.ComponentProps<typeof Column>> = ({ ...flex }) => (
  <Column fillWidth horizontal="center" gap="64" paddingTop="80" {...flex}>
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
        y: 0,
        width: 150,
        height: 70,
        opacity: 60,
      }}
      dots={{ display: true, color: "neutral-alpha-weak", size: "2", opacity: 40 }}
      style={{ maskImage: "linear-gradient(to bottom, black 50%, transparent)" }}
    />
    <Column zIndex={1} maxWidth="s" horizontal="center" align="center" gap="24">
      <Tag size="l" scheme="brand" prefixIcon="security" label="Python library · 0.1.0, early release" />
      <Heading as="h1" variant="display-strong-l" wrap="balance">
        Give your agent authority, <Text onBackground="neutral-weak">not unrestricted power</Text>
      </Heading>
      <Text variant="body-default-xl" onBackground="neutral-medium" wrap="balance">
        Mandate sits between your agent and its tools. Before a tool runs, it decides: allow, deny,
        or ask a human. Approvals are bound to the exact call and work once.
      </Text>
      <Row gap="12" horizontal="center" paddingTop="8" s={{ direction: "column" }}>
        <Button href={repoUrl} prefixIcon="github" arrowIcon>
          Follow on GitHub
        </Button>
        <Button variant="secondary" href="#guarantees">
          Read the guarantees
        </Button>
      </Row>
      <Row
        paddingX="12"
        paddingY="8"
        radius="m"
        border
        background="surface"
        textVariant="code-default-s"
        onBackground="neutral-medium"
        style={{ overflowX: "auto", whiteSpace: "nowrap", maxWidth: "100%" }}
      >
        {installCommand}
      </Row>
    </Column>
    <Column zIndex={1} fillWidth maxWidth="m" gap="12">
      <CodeBlock
        fillWidth
        background="page"
        radius="xl"
        lineNumbers
        copyButton
        codes={[
          { code: policy, language: "yaml", label: "policy.yaml" },
          { code: dispatch, language: "python", label: "dispatch.py" },
        ]}
      />
      <Text variant="label-default-s" onBackground="neutral-weak" align="center">
        Written against Mandate 0.1.0. The API may change before 1.0.
      </Text>
    </Column>
  </Column>
);
