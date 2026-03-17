import React, { type CSSProperties } from "react";

import { EmployeeDirectoryTable } from "@/components/directory/employee-directory-table";
import { SectionCard } from "@/components/section-card";
import { getDirectoryEmployees } from "@/lib/api/directory";

export default async function DirectoryPage() {
  const directory = await getDirectoryEmployees();

  return (
    <div style={styles.page}>
      <SectionCard
        eyebrow="Internal App"
        title="Employee Directory"
        description={`Seed ${directory.seed}. Browse seeded employees, devices, and access context for helpdesk workflows.`}
      >
        <EmployeeDirectoryTable employees={directory.employees} />
      </SectionCard>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: { display: "grid", gap: "20px" },
};
