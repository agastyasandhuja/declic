import 'react-native-url-polyfill/auto';
import { createClient } from '@supabase/supabase-js';
import { config, authConfigured } from '../../config';
import { sessionStorage } from './sessionStorage';

// Matches Supabase's default so existing installed sessions remain readable.
const storageKey = authConfigured ? `sb-${new URL(config.supabaseUrl).hostname.split('.')[0]}-auth-token` : '';
const newClient = () => authConfigured ? createClient(config.supabaseUrl, config.supabasePublishableKey, {
  auth: { storage: sessionStorage, storageKey, persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
}) : null;
export let supabase = newClient();

export async function clearSavedSession() {
  // Explicit recovery for corrupt SecureStore data, without requiring a network call.
  await supabase?.auth.stopAutoRefresh();
  if (storageKey) await sessionStorage.removeItem(storageKey);
  supabase = newClient();
}
