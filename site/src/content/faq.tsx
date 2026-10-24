import { InlineCode, Text } from "@once-ui-system/core";
import { installCommand } from "@/resources";

export const faq = [
  {
    title: "Is Mandate a sandbox?",
    content: (
      <Text onBackground="neutral-medium">
        No. Mandate decides whether a call may run; your code enforces that decision. It doesn't
        isolate processes, filter network traffic or protect tools that are called without going
        through the guard. Use it alongside those controls, not instead of them.
      </Text>
    ),
  },
  {
    title: "Does it stop prompt injection?",
    content: (
      <Text onBackground="neutral-medium">
        It doesn't detect injection. It limits what an injected instruction can get a tool to do:
        a call the policy doesn't allow is denied, whoever asked for it.
      </Text>
    ),
  },
  {
    title: "Which agent frameworks does it work with?",
    content: (
      <Text onBackground="neutral-medium">
        Any setup where you control the code that calls your tools. The core has no framework
        dependency. 0.1 ships without framework adapters; which ones come first depends on what
        early users run.
      </Text>
    ),
  },
  {
    title: "Which tools can it guard?",
    content: (
      <Text onBackground="neutral-medium">
        Any tool, matched by its name and parameters. The 0.1 tests and examples cover file
        access, data export and HTTP requests.
      </Text>
    ),
  },
  {
    title: "Does Mandate send my data anywhere?",
    content: (
      <Text onBackground="neutral-medium">
        No. It runs in your process, and audit events stay with your application, with
        secret-like values redacted first. Redaction is pattern-based, so treat it as a safety net
        rather than a promise.
      </Text>
    ),
  },
  {
    title: "Can I use it today?",
    content: (
      <Text onBackground="neutral-medium">
        Yes, as an early release. Install 0.1.0 from source with{" "}
        <InlineCode>{installCommand}</InlineCode>. Note that <InlineCode>mandate</InlineCode> on
        PyPI is a different, unrelated package. Expect the API to change before 1.0.
      </Text>
    ),
  },
  {
    title: "Is it open source?",
    content: (
      <Text onBackground="neutral-medium">
        Yes. Mandate is MIT-licensed and developed in the open on GitHub.
      </Text>
    ),
  },
];
