/** The learner dashboard. */

import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { progress } from '@/api/endpoints';
import { EmptyState, ErrorNotice, MasteryBar, Spinner } from '@/components/ui';

const RECOMMENDATION_TONE: Record<string, string> = {
  remediate: 'badge-danger',
  review: 'badge-warning',
  continue: 'badge-accent',
  advance: 'badge-success',
  project: 'badge-accent',
};

export function DashboardPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: progress.dashboard,
  });

  if (isLoading) return <Spinner label="Loading your dashboard" />;
  if (error) return <ErrorNotice error={error} onRetry={() => void refetch()} />;
  if (!data) return null;

  const { counters, level, streak } = data;
  const maxActivity = Math.max(
    1,
    ...data.activity_series.map((day) => day.runs + day.submissions),
  );

  return (
    <div className="stack">
      <header>
        <h1>
          {greeting()}, {data.user.display_name}
        </h1>
        <p className="muted">
          {data.user.goal
            ? `Goal: ${data.user.goal}`
            : 'Set a goal in Settings to sharpen your recommendations.'}
        </p>
      </header>

      <section className="stat-grid" aria-label="Progress summary">
        <div className="stat">
          <div className="stat-label">Overall mastery</div>
          <div className="stat-value">{Math.round(data.overall_mastery * 100)}%</div>
          <div className="stat-hint">
            {counters.concepts_mastered} concept{counters.concepts_mastered === 1 ? '' : 's'} mastered
          </div>
        </div>

        <div className="stat">
          <div className="stat-label">Level {level.level}</div>
          <div className="stat-value">{level.title}</div>
          <div className="stat-hint">
            {level.xp_into_level} / {level.xp_for_next_level} XP to level {level.level + 1}
          </div>
          <div className="meter" style={{ marginTop: 8 }}>
            <div className="meter-fill" style={{ width: `${level.progress * 100}%` }} />
          </div>
        </div>

        <div className="stat">
          <div className="stat-label">Streak</div>
          <div className="stat-value">{streak.current_days}d</div>
          <div className="stat-hint">Longest: {streak.longest_days} days</div>
        </div>

        <div className="stat">
          <div className="stat-label">Exercises passed</div>
          <div className="stat-value">{counters.exercises_passed}</div>
          <div className="stat-hint">
            {Math.round(counters.attempt_accuracy * 100)}% of attempts succeeded
          </div>
        </div>

        <div className="stat">
          <div className="stat-label">Lessons</div>
          <div className="stat-value">
            {counters.lessons_completed}
            <span className="muted" style={{ fontSize: '1rem' }}>
              /{counters.lessons_total}
            </span>
          </div>
          <div className="stat-hint">{counters.coding_hours}h coding time</div>
        </div>

        <div className="stat">
          <div className="stat-label">Projects</div>
          <div className="stat-value">
            {counters.projects_completed}
            <span className="muted" style={{ fontSize: '1rem' }}>
              /{counters.projects_total}
            </span>
          </div>
          <div className="stat-hint">
            <Link to="/projects">Open the academy</Link>
          </div>
        </div>
      </section>

      <section className="card">
        <h2>What to do next</h2>
        {data.recommendations.length === 0 ? (
          <EmptyState title="Nothing queued" hint="Start a lesson from the Learn tab." />
        ) : (
          data.recommendations.map((item) => (
            <Link
              key={`${item.kind}-${item.lesson_slug ?? item.exercise_slug ?? item.concept_slug}`}
              to={
                item.exercise_slug
                  ? `/practice/${item.exercise_slug}`
                  : item.lesson_slug
                    ? `/learn/${item.lesson_slug}`
                    : '/progress'
              }
              className="list-row"
            >
              <div style={{ minWidth: 0 }}>
                <div className="row" style={{ gap: 8 }}>
                  <span className={`badge ${RECOMMENDATION_TONE[item.kind] ?? ''}`}>
                    {item.kind}
                  </span>
                  <strong>{item.title}</strong>
                </div>
                <div className="small muted" style={{ marginTop: 4 }}>
                  {item.reason}
                </div>
              </div>
              <span aria-hidden>→</span>
            </Link>
          ))
        )}
      </section>

      <div className="section-grid">
        <section className="card">
          <h2>Weak areas</h2>
          {data.weak_areas.length === 0 ? (
            <p className="small muted">
              Nothing flagged yet — mastery data appears once you submit exercises.
            </p>
          ) : (
            data.weak_areas.map((area) => (
              <MasteryBar
                key={area.concept_slug}
                label={area.concept_name}
                percent={Math.round(area.score * 100)}
                weak
              />
            ))
          )}
        </section>

        <section className="card">
          <h2>Strongest</h2>
          {data.strong_areas.length === 0 ? (
            <p className="small muted">Complete an exercise to start building a profile.</p>
          ) : (
            data.strong_areas.map((area) => (
              <MasteryBar
                key={area.concept_slug}
                label={area.concept_name}
                percent={Math.round(area.score * 100)}
                mastered={area.score >= 0.85}
              />
            ))
          )}
        </section>

        <section className="card">
          <h2>Repeated mistakes</h2>
          {data.repeated_mistakes.length === 0 ? (
            <p className="small muted">No recurring patterns detected.</p>
          ) : (
            <ul style={{ paddingLeft: 18, margin: 0 }}>
              {data.repeated_mistakes.map((mistake) => (
                <li key={mistake.misconception} className="small">
                  {mistake.label} <span className="muted">(×{mistake.count})</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="card">
        <h2>Last 30 days</h2>
        <div className="activity-chart" role="img" aria-label="Daily activity for the last 30 days">
          {data.activity_series.slice(-30).map((day) => {
            const total = day.runs + day.submissions;
            return (
              <div
                key={day.date}
                className={`activity-bar${total > 0 ? ' has-activity' : ''}`}
                style={{ height: `${Math.max(4, (total / maxActivity) * 100)}%` }}
                title={`${day.date}: ${day.runs} runs, ${day.submissions} submissions`}
              />
            );
          })}
        </div>
      </section>

      {data.achievements.length > 0 && (
        <section className="card">
          <h2>Recent achievements</h2>
          <div className="row wrap">
            {data.achievements.map((achievement) => (
              <span key={achievement.slug} className="badge badge-success" title={achievement.description}>
                {achievement.name}
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}
