import React from 'react';
import { ArrowUpDown, MoreHorizontal } from 'lucide-react';

export const DataTable = ({
  columns = ["ID", "Name", "Status", "Date"],
  data = [
    { id: "1", name: "Project Alpha", status: "Active", date: "2026-07-10" },
    { id: "2", name: "Database Migration", status: "Completed", date: "2026-07-09" },
    { id: "3", name: "UI Overhaul", status: "Pending", date: "2026-07-11" }
  ]
}) => {
  return (
    <div className="w-full overflow-hidden rounded-md border border-border bg-card text-card-foreground shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full caption-bottom text-sm">
          <thead className="border-b border-border/50 bg-muted/50">
            <tr className="border-b transition-colors hover:bg-muted/50">
              {columns.map((col, idx) => (
                <th key={idx} className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">
                  <div className="flex items-center space-x-2">
                    <span>{col}</span>
                    <ArrowUpDown className="h-4 w-4 opacity-50" />
                  </div>
                </th>
              ))}
              <th className="h-12 px-4 align-middle font-medium text-muted-foreground text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="[&_tr:last-child]:border-0">
            {data.map((row, i) => (
              <tr key={i} className="border-b transition-colors hover:bg-muted/50">
                {Object.values(row).map((val, j) => (
                  <td key={j} className="p-4 align-middle">
                    {j === 2 ? (
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        val === 'Active' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                        val === 'Completed' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' :
                        'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                      }`}>
                        {val}
                      </span>
                    ) : val}
                  </td>
                ))}
                <td className="p-4 align-middle text-right">
                  <button className="p-2 text-muted-foreground hover:bg-muted rounded-md transition-colors">
                    <MoreHorizontal className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-end space-x-2 py-4 px-4 border-t border-border/50">
        <button className="h-8 px-3 text-xs border border-border rounded-md hover:bg-muted">Previous</button>
        <button className="h-8 px-3 text-xs border border-border rounded-md hover:bg-muted">Next</button>
      </div>
    </div>
  );
};
