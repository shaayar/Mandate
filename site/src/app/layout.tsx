import '@once-ui-system/core/css/styles.css';
import '@once-ui-system/core/css/tokens.css';
import '@/resources/custom.css'

import classNames from "classnames";

import { baseURL, site, fonts, style, dataStyle } from "@/resources";
import { Meta, Schema,  Column, Flex, ThemeInit, type OnceUIStyleConfig } from "@once-ui-system/core";
import type { ChartMode } from "@once-ui-system/core/data";
import { LocaleProvider, Providers } from '@/components';
import { getLocale } from '@/lib/i18n/server';

export async function generateMetadata() {
  return Meta.generate({
    title: site.home.title,
    description: site.home.description,
    baseURL: baseURL,
    path: site.home.path,
    canonical: site.home.canonical,
    image: site.home.image,
    robots: site.home.robots,
    alternates: site.home.alternates,
  });
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();

  return (
    <Flex
      suppressHydrationWarning
      data-scroll-behavior="smooth"
      as="html"
      lang={locale}
      fillWidth
      className={classNames(
        fonts.heading.variable,
        fonts.body.variable,
        fonts.label.variable,
        fonts.code.variable,
      )}
    >
      <head>
        {/* A sync <script> is only allowed inside the document head; React 19.2
            refuses one rendered as a bare child of <html>. */}
        <Schema
          as="webPage"
          baseURL={baseURL}
          title={site.home.title}
          description={site.home.description}
          path={site.home.path}
        />
        <ThemeInit
          config={style as OnceUIStyleConfig}
          dataStyle={{ mode: dataStyle.mode as ChartMode }}
        />
      </head>
      <LocaleProvider locale={locale}>
        <Providers>
          <Column as="body" background="page" fillWidth margin="0" padding="0" minHeight="100vh">
            <Column fillWidth horizontal="center" flex={1}>
              {children}
            </Column>
          </Column>
        </Providers>
      </LocaleProvider>
    </Flex>
  );
}