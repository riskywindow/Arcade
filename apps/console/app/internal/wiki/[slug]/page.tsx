import React from "react";

import { WikiDocumentView } from "@/components/wiki/wiki-document-view";
import { getWikiDocument } from "@/lib/api/wiki";

type WikiDocumentPageProps = {
  params: Promise<{ slug: string }>;
};

export default async function WikiDocumentPage({ params }: WikiDocumentPageProps) {
  const { slug } = await params;
  const response = await getWikiDocument(slug);

  return <WikiDocumentView document={response.document} />;
}
