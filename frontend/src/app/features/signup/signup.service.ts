/**
 * SignupService — orchestrates the 3-step signup flow.
 *
 * Step 1 (Account): POST /api/v1/auth/signup
 *   - Backend creates Supabase user, tenant row, Stripe customer, SetupIntent.
 *   - Response carries `tenant_id` and `stripe_setup_intent_client_secret`
 *     but NOT a JWT.  To mint a session we follow up with a direct call to
 *     `supabase.auth.signInWithPassword()` using the credentials the user
 *     just submitted (option (a) from the build brief — keeps the surface
 *     change minimal and lives entirely in the frontend).
 *
 * Step 2 (Plan): GET /api/v1/billing/prices  (requires JWT from step 1)
 *
 * Step 3 (Card): stripe.confirmCardSetup(client_secret, ...)
 *                then POST /api/v1/billing/start-trial { setup_intent_id, price_id }
 *
 * After success: persist JWT in AuthService (mirrors to localStorage under
 * `aethos_token` — same key the auth-interceptor reads).
 */

import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth.service';
import { SupabaseService } from '../../core/services/supabase.service';

// ── Public types ───────────────────────────────────────────────────────────

export type PlanTier = 'starter' | 'growth' | 'pro';
export type BillingInterval = 'monthly' | 'annual';
export type LaunchCountry = 'US' | 'GB' | 'SG' | 'IN' | 'AU';

export interface SignupAccountPayload {
  email: string;
  password: string;
  tenant_name: string;
  country: LaunchCountry;
  plan_tier: PlanTier;
}

export interface SignupApiResponse {
  tenant_id: string;
  stripe_setup_intent_client_secret: string;
  message?: string;
}

export interface PriceEntry {
  tier: string;
  monthly_id: string | null;
  annual_id: string | null;
}

export interface PriceCatalogue {
  currency: string;
  plans: PriceEntry[];
}

export interface StartTrialPayload {
  setup_intent_id: string;
  price_id: string;
}

export interface StartTrialResponse {
  subscription_id: string;
  status: string;
  trial_ends_at: number | null;
}

// ── Country → currency mirror (matches backend country_to_currency) ────────
// Kept in lock-step with `backend/app/services/billing/stripe_service.py`.
export const COUNTRY_TO_CURRENCY: Record<LaunchCountry, string> = {
  US: 'USD',
  GB: 'GBP',
  SG: 'SGD',
  IN: 'INR',
  AU: 'AUD',
};

export const LAUNCH_COUNTRIES: Array<{ code: LaunchCountry; label: string; currency: string }> = [
  { code: 'US', label: 'United States', currency: 'USD' },
  { code: 'GB', label: 'United Kingdom', currency: 'GBP' },
  { code: 'SG', label: 'Singapore', currency: 'SGD' },
  { code: 'IN', label: 'India', currency: 'INR' },
  { code: 'AU', label: 'Australia', currency: 'AUD' },
];

@Injectable({ providedIn: 'root' })
export class SignupService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private supabaseSvc = inject(SupabaseService);

  private get supabaseClient() {
    return this.supabaseSvc.client;
  }

  /**
   * Step 1 — POST /auth/signup, then sign in to mint a JWT.
   * Returns the SetupIntent client_secret (needed for step 3) and the tenant_id.
   *
   * The signup endpoint is idempotent on email (browser-refresh safe).  If
   * Supabase rejects the sign-in (e.g. signup confirmation email required and
   * not yet clicked), we surface a clear error so the user knows what to do.
   */
  async signupAndSignIn(payload: SignupAccountPayload): Promise<SignupApiResponse> {
    // Backend signup — strip auth interceptor (we have no token yet).
    const headers = new HttpHeaders({ 'skip-auth': '1' });
    const signupResp = await firstValueFrom(
      this.http.post<SignupApiResponse>(
        `${environment.apiUrl}/api/v1/auth/signup`,
        payload,
        { headers },
      ),
    );

    // Mint a JWT via Supabase Auth so subsequent /billing calls authenticate.
    const { data, error } = await this.supabaseClient.auth.signInWithPassword({
      email: payload.email,
      password: payload.password,
    });

    if (error || !data.session?.access_token) {
      // Distinguish "email confirmation required" from other failures — Supabase
      // returns the user with no session when confirm_email is enabled. If that
      // happens on a fresh project, the Founder must disable email confirmation
      // in Supabase dashboard (tracked separately as #116 — email allowlist).
      const msg =
        error?.message?.toLowerCase().includes('confirm')
          ? 'Please confirm your email address before continuing. Check your inbox.'
          : error?.message
            || 'Could not sign you in after signup. Please reload and try again.';
      throw new Error(msg);
    }

    this.auth.setToken(data.session.access_token);
    // Persist the tenant_id so the auth interceptor can attach X-Tenant-ID on
    // subsequent calls (/billing/prices, /billing/start-trial). Without this
    // those calls hit the membership-check dep and return 403 "Tenant context
    // missing". See the Pick-a-plan error the Founder hit during dogfood.
    this.auth.setTenantId(signupResp.tenant_id);
    return signupResp;
  }

  /** Step 2 — fetch the price catalogue (requires JWT). */
  async fetchPrices(): Promise<PriceCatalogue> {
    return firstValueFrom(
      this.http.get<PriceCatalogue>(`${environment.apiUrl}/api/v1/billing/prices`),
    );
  }

  /** Step 3b — after Stripe confirms the SetupIntent, kick off the trial. */
  async startTrial(payload: StartTrialPayload): Promise<StartTrialResponse> {
    return firstValueFrom(
      this.http.post<StartTrialResponse>(
        `${environment.apiUrl}/api/v1/billing/start-trial`,
        payload,
      ),
    );
  }
}
