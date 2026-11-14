// Public types for the academics mobile feature package (owner: Amogh).
//
// These mirror contracts/academics.md. The components NEVER talk to Canvas,
// Gemini or the database directly — they receive an AcademicsApiClient that Adi
// implements against the real backend, and an identity/theme by prop injection.
// No navigation, no auth store, no provider secrets live in this package.

export type ConnectionMode = 'oauth' | 'developer_token' | 'upload';
export type ConnectionStatus = 'connected' | 'reconnect_required' | 'disconnected' | 'error';

export interface CanvasConnectionSummary {
  status: ConnectionStatus;
  mode: ConnectionMode | null;
  institutionOrigin: string | null;
  availableModes: ConnectionMode[];
  lastSyncAt: string | null; // ISO timestamp with zone, or null
}

export type ImportStatus =
  | 'queued' | 'fetching' | 'extracting' | 'planning'
  | 'ready' | 'needs_review' | 'partial' | 'error';

export type EvidenceStatus = 'explicit' | 'inferred' | 'user_confirmed' | 'unknown';
export type DatePrecision = 'date' | 'datetime' | 'unknown';

export interface AcademicDate {
  date: string | null;        // YYYY-MM-DD or null
  timestamp: string | null;   // ISO or null — never invented from a date-only source
  timezone: string | null;    // IANA
  precision: DatePrecision;
  evidenceStatus: EvidenceStatus;
}

export interface UpcomingItem {
  name: string;
  dueDate: string;   // YYYY-MM-DD
  daysUntil: number;
  isExam: boolean;
}

export interface CourseTiming {
  nextDueName: string | null;
  nextDueDate: string | null;
  daysUntilNext: number | null;
  upcomingCount: number;
  urgency: number;          // 0..1
  hasUndatedExam: boolean;
  upcoming: UpcomingItem[];
}

export interface CourseSummary {
  courseId: string;
  title: string | null;
  term: string | null;
  timezone: string | null;
  importStatus: ImportStatus;
  missingSources: string[];
  timing: CourseTiming | null;
}

export interface Assessment {
  assessmentId: string;
  title: string;
  kind: 'midterm' | 'final' | 'quiz' | 'assignment' | 'other';
  scheduled: AcademicDate;
  scopeStatus: EvidenceStatus;
  coveredTopics: string[];
}

export interface Unit {
  unitId: string;
  title: string;
  order: number;
  objectives: string[];
}

export interface LessonRequestView {
  lessonRequestId: string;
  title: string;
  learningGoal: string;
  importance: 'core' | 'supporting' | 'optional';
  evidenceStatus: 'explicit' | 'inferred' | 'suggested_practice' | 'user_confirmed';
  examScopeStatus: EvidenceStatus;
  suggestedFormats: string[];
  targetDurationSeconds: number;
}

export interface CourseProfileDetail {
  course: CourseSummary;
  units: Unit[];
  assessments: Assessment[];
  lessons: LessonRequestView[];
}

// A student correction to a date or exam scope. Produces a new profile revision.
export interface ProfileCorrection {
  assessmentId: string;
  date?: string | null;           // YYYY-MM-DD the student confirms
  scopeStatus?: EvidenceStatus;   // e.g. user_confirmed
}

// The contract Adi's real client must satisfy. Every call is for the current
// authenticated user; the client supplies identity, not the component.
export interface AcademicsApiClient {
  getConnection(): Promise<CanvasConnectionSummary>;
  connect(mode: ConnectionMode): Promise<CanvasConnectionSummary>;
  disconnect(): Promise<CanvasConnectionSummary>;
  sync(): Promise<{ jobId: string }>;
  getCourses(): Promise<CourseSummary[]>;
  getCourseProfile(courseId: string): Promise<CourseProfileDetail>;
  applyCorrections(
    courseId: string,
    expectedRevision: number,
    corrections: ProfileCorrection[],
  ): Promise<CourseProfileDetail>;
}

export interface Identity {
  userId: string;
}
