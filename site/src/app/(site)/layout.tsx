import { Column, Row } from "@once-ui-system/core";
import { Footer, Header } from "./components";

export default function SiteLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <>
      <Row
        fillWidth
        center
        paddingX="16"
        paddingY="8"
        borderBottom
        textVariant="label-default-s"
        onBackground="neutral-medium"
        align="center"
      >
        Early release: Mandate 0.1.0 installs from source, and its API may still change.
      </Row>
      <Header />
      <Column as="main" fillWidth horizontal="center" flex={1}>
        {children}
      </Column>
      <Footer />
    </>
  );
}
