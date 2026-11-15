import { Platform } from 'react-native';
import { saveStartupDiagnostics } from './NativeMediaFiles';
import { StartupTrace } from './StartupTrace';
export const startupTrace = new StartupTrace(async value => { if (Platform.OS !== 'web') await saveStartupDiagnostics(value); });
