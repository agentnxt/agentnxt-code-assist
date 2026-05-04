'use client';

import { useEffect, useState } from 'react';

interface DailySummary {
  date: string;
  tasks_completed_count: number;
  bugs_fixed: number;
  completed_tasks: { task_name: string }[];
  blockers: { description: string; severity: string }[];
  projects_on_track: { name: string }[];
  projects_at_risk: { name: string }[];
}

export default function DailyPage() {
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/daily/summary')
      .then(res => res.json())
      .then(data => {
        setSummary(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <main className="shell">
      <section className="page-header">
        <h1>Daily Status</h1>
        <p>End-of-day reports and blockers</p>
      </section>

      <section className="content">
        {loading ? (
          <p>Loading...</p>
        ) : !summary ? (
          <div className="empty">
            <p>No summary available</p>
          </div>
        ) : (
          <>
            <div className="stats-grid">
              <div className="stat-card">
                <span className="stat-value">{summary.tasks_completed_count}</span>
                <span className="stat-label">Tasks Completed</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{summary.bugs_fixed}</span>
                <span className="stat-label">Bugs Fixed</span>
              </div>
            </div>

            {summary.completed_tasks.length > 0 && (
              <div className="section">
                <h2>Completed Tasks</h2>
                <ul>
                  {summary.completed_tasks.map((t, i) => (
                    <li key={i}>{t.task_name}</li>
                  ))}
                </ul>
              </div>
            )}

            {summary.blockers.length > 0 && (
              <div className="section warning">
                <h2>Blockers</h2>
                <ul>
                  {summary.blockers.map((b, i) => (
                    <li key={i} className={b.severity}>
                      [{b.severity}] {b.description}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </section>
    </main>
  );
}