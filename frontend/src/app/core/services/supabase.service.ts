/**
 * SupabaseService — single shared SupabaseClient instance for the SPA.
 *
 * Every component and service that needs Supabase Auth or Supabase Data must
 * inject this service and use `.client` rather than calling `createClient()`
 * themselves.  Having multiple `SupabaseClient` instances means each instance
 * maintains its own in-memory session store, so a session minted in
 * SignupService would be invisible to ChangePasswordComponent (bug #131).
 *
 * Providing at root ensures one instance for the entire app lifetime.
 */
import { Injectable } from '@angular/core';
import { createClient, processLock, SupabaseClient } from '@supabase/supabase-js';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class SupabaseService {
  readonly client: SupabaseClient = createClient(
    environment.supabaseUrl,
    environment.supabaseAnonKey,
    {
      auth: {
        lock: processLock,
      },
    },
  );
}
