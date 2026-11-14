// In-memory fake AcademicsApiClient (owner: Amogh).
//
// Lets the components run standalone and lets Adi wire the UI before the real
// backend endpoints exist. Synthetic data only — mirrors the live pipeline's
// shape (real-time timing, undated exam, suggested practice vs exam scope).

import type {
  AcademicsApiClient,
  CanvasConnectionSummary,
  ConnectionMode,
  CourseProfileDetail,
  CourseSummary,
  ProfileCorrection,
} from './types';

function daysFromNow(n: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

const COURSES: CourseSummary[] = [
  {
    courseId: 'demo-calc', title: 'Multivariate Calculus', term: 'Fall 2026',
    timezone: 'America/New_York', importStatus: 'ready', missingSources: [],
    timing: {
      nextDueName: 'HW 16.1', nextDueDate: daysFromNow(2), daysUntilNext: 2,
      upcomingCount: 9, urgency: 0.95, hasUndatedExam: false,
      upcoming: [{ name: 'HW 16.1', dueDate: daysFromNow(2), daysUntil: 2, isExam: false }],
    },
  },
  {
    courseId: 'demo-dsa', title: 'Data Structures', term: 'Fall 2026',
    timezone: 'America/New_York', importStatus: 'ready', missingSources: [],
    timing: {
      nextDueName: 'PA11 Heaps and Treaps', nextDueDate: daysFromNow(6), daysUntilNext: 6,
      upcomingCount: 3, urgency: 0.86, hasUndatedExam: true,
      upcoming: [{ name: 'PA11 Heaps and Treaps', dueDate: daysFromNow(6), daysUntil: 6, isExam: false }],
    },
  },
  {
    courseId: 'demo-prob', title: 'Intro to Probability', term: 'Fall 2026',
    timezone: 'America/New_York', importStatus: 'needs_review',
    missingSources: ['syllabus'], timing: null,
  },
];

const DSA_PROFILE: CourseProfileDetail = {
  course: COURSES[1],
  units: [
    { unitId: 'u1', title: 'Heaps', order: 11, objectives: ['min-heap property', 'percolate up/down'] },
    { unitId: 'u2', title: 'Sorting', order: 12, objectives: ['merge sort partitioning'] },
  ],
  assessments: [
    {
      assessmentId: 'a1', title: 'Midterm 1', kind: 'midterm',
      scheduled: { date: null, timestamp: null, timezone: 'America/New_York', precision: 'unknown', evidenceStatus: 'unknown' },
      scopeStatus: 'unknown', coveredTopics: [],
    },
  ],
  lessons: [
    { lessonRequestId: 'lr1', title: 'Min-Heap Property', learningGoal: 'Understand heap ordering invariants.', importance: 'core', evidenceStatus: 'explicit', examScopeStatus: 'inferred', suggestedFormats: ['visual_explainer'], targetDurationSeconds: 45 },
    { lessonRequestId: 'lr2', title: 'Heap Insertion', learningGoal: 'Percolate-up to insert.', importance: 'core', evidenceStatus: 'explicit', examScopeStatus: 'inferred', suggestedFormats: ['worked_example'], targetDurationSeconds: 50 },
    { lessonRequestId: 'lr3', title: 'Merge Sort Partitioning', learningGoal: 'Recursive splitting.', importance: 'supporting', evidenceStatus: 'suggested_practice', examScopeStatus: 'unknown', suggestedFormats: ['analogy_story'], targetDurationSeconds: 40 },
  ],
};

export class FakeAcademicsApiClient implements AcademicsApiClient {
  private connection: CanvasConnectionSummary = {
    status: 'disconnected', mode: null, institutionOrigin: 'https://umamherst.instructure.com',
    availableModes: ['developer_token', 'upload'], lastSyncAt: null,
  };
  private revision = 1;

  async getConnection(): Promise<CanvasConnectionSummary> { return this.connection; }

  async connect(mode: ConnectionMode): Promise<CanvasConnectionSummary> {
    this.connection = { ...this.connection, status: 'connected', mode, lastSyncAt: new Date().toISOString() };
    return this.connection;
  }

  async disconnect(): Promise<CanvasConnectionSummary> {
    this.connection = { ...this.connection, status: 'disconnected', mode: null, lastSyncAt: null };
    return this.connection;
  }

  async sync(): Promise<{ jobId: string }> { return { jobId: 'demo-job-1' }; }

  async getCourses(): Promise<CourseSummary[]> { return COURSES; }

  async getCourseProfile(courseId: string): Promise<CourseProfileDetail> {
    if (courseId === 'demo-dsa') return { ...DSA_PROFILE, course: { ...DSA_PROFILE.course } };
    const course = COURSES.find((c) => c.courseId === courseId) ?? COURSES[0];
    return { course, units: [], assessments: [], lessons: [] };
  }

  async applyCorrections(
    courseId: string, _expectedRevision: number, corrections: ProfileCorrection[],
  ): Promise<CourseProfileDetail> {
    this.revision += 1;
    const base = await this.getCourseProfile(courseId);
    const assessments = base.assessments.map((a) => {
      const fix = corrections.find((c) => c.assessmentId === a.assessmentId);
      if (!fix) return a;
      return {
        ...a,
        scopeStatus: fix.scopeStatus ?? a.scopeStatus,
        scheduled: fix.date !== undefined
          ? { ...a.scheduled, date: fix.date, precision: (fix.date ? 'date' : 'unknown') as 'date' | 'unknown', evidenceStatus: 'user_confirmed' as const }
          : a.scheduled,
      };
    });
    return { ...base, assessments };
  }
}
