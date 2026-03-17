import React from "react";

import { EmployeeDetailView } from "@/components/directory/employee-detail-view";
import { getDirectoryEmployeeDetail } from "@/lib/api/directory";

export default async function DirectoryEmployeePage({
  params,
}: {
  params: Promise<{ employeeId: string }>;
}) {
  const { employeeId } = await params;
  const detailResponse = await getDirectoryEmployeeDetail(employeeId);

  return <EmployeeDetailView detail={detailResponse.detail} />;
}
