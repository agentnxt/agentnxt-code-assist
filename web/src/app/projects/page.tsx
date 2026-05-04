'use client';

import { useEffect, useState } from 'react';

interface Project {
  project_id: string;
  name: string;
  status: string;
  tasks_completed: number;
  tasks_total: number;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/projects')
      .then(res => res.json())
      .then(data => {
        setProjects(data.projects || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <main className="shell">
      <section className="page-header">
        <h1>Projects</h1>
        <p>Manage tasks, milestones and dependencies</p>
      </section>

      <section className="content">
        {loading ? (
          <p>Loading...</p>
        ) : projects.length === 0 ? (
          <div className="empty">
            <p>No projects yet</p>
            <button>Create Project</button>
          </div>
        ) : (
          <div className="projects-grid">
            {projects.map((proj) => (
              <article key={proj.project_id} className="project-card">
                <h3>{proj.name}</h3>
                <span className="badge">{proj.status}</span>
                <div className="stats">
                  <span>Tasks: {proj.tasks_completed}/{proj.tasks_total}</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}