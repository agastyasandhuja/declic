// Public surface of @hackumass/mobile-academics (owner: Amogh).
//
// Adi imports from here and wires components into the app's navigation, passing
// a real AcademicsApiClient, the current Identity, and the app theme.

export { AcademicsScreen } from './screens/AcademicsScreen';
export type { AcademicsScreenProps } from './screens/AcademicsScreen';

export { CanvasConnection } from './components/CanvasConnection';
export type { CanvasConnectionProps } from './components/CanvasConnection';
export { CourseList } from './components/CourseList';
export type { CourseListProps } from './components/CourseList';
export { CourseProfile } from './components/CourseProfile';
export type { CourseProfileProps } from './components/CourseProfile';
export { ImportProgress } from './components/ImportProgress';
export type { ImportProgressProps } from './components/ImportProgress';
export { StatusBadge } from './components/StatusBadge';

export { defaultTheme } from './theme';
export type { AcademicsTheme } from './theme';

export { FakeAcademicsApiClient } from './api/fakeClient';

export type {
  AcademicsApiClient,
  CanvasConnectionSummary,
  ConnectionMode,
  ConnectionStatus,
  CourseSummary,
  CourseProfileDetail,
  CourseTiming,
  Identity,
  ImportStatus,
  LessonRequestView,
  ProfileCorrection,
  Unit,
  Assessment,
  AcademicDate,
} from './api/types';
