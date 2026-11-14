import 'react-native-url-polyfill/auto';
import { createClient } from '@supabase/supabase-js';
import { config, authConfigured } from '../../config';
import { sessionStorage } from './sessionStorage';

export const supabase = authConfigured ? createClient(config.supabaseUrl, config.supabasePublishableKey, {
  auth: { storage: sessionStorage, persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
}) : null;
