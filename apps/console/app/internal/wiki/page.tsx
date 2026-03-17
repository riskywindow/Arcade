import React, { type CSSProperties } from "react";

import { SectionCard } from "@/components/section-card";
import { WikiDocumentList } from "@/components/wiki/wiki-document-list";
import { WikiSearchForm } from "@/components/wiki/wiki-search-form";
import { getWikiDocuments, searchWikiDocuments } from "@/lib/api/wiki";

type WikiPageProps = {
  searchParams?: Promise<{ q?: string }>;
};

export default async function WikiPage({ searchParams }: WikiPageProps) {
  const params = searchParams ? await searchParams : {};
  const query = params.q?.trim() ?? "";
  const data = query
    ? await searchWikiDocuments(query)
    : await getWikiDocuments();

  return (
    <div style={styles.page}>
      <SectionCard
        eyebrow="Internal App"
        title="Internal Wiki"
        description={`Seed ${data.seed}. Browse deterministic runbooks, policies, and troubleshooting docs for Phase 3 workflows.`}
      >
        <WikiSearchForm query={query} />
      </SectionCard>

      <SectionCard
        title={query ? "Search Results" : "Seeded Documents"}
        description={
          query
            ? "Simple token-based search over the seeded corpus."
            : "Public docs only. Hidden scenario notes remain out of this surface."
        }
      >
        {"results" in data ? (
          <WikiDocumentList query={query} results={data.results} />
        ) : (
          <WikiDocumentList documents={data.documents} />
        )}
      </SectionCard>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: { display: "grid", gap: "20px" },
};
