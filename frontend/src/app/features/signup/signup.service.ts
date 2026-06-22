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
export type LaunchCountryOption = {
  code: LaunchCountry;
  label: string;
  currency: string;
  market: string;
  taxLabel: string;
};

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

export interface MarketProfile {
  country: string;
  market: string;
  country_name: string;
  base_currency: string;
  locale: string;
  timezone: string;
  tax_label: string;
  tax_registration_label: string;
  invoice_tax_label: string;
  tax_authority_label: string;
  tax_collection_model: string;
  default_tax_rate_code: string | null;
  reporting_periods: string[];
  fiscal_year_label: string;
}

export const LAUNCH_COUNTRIES: LaunchCountryOption[] = [
  { code: 'US', label: 'United States', currency: 'USD', market: 'US', taxLabel: 'Sales tax' },
  { code: 'GB', label: 'United Kingdom', currency: 'GBP', market: 'UK', taxLabel: 'VAT' },
  { code: 'SG', label: 'Singapore', currency: 'SGD', market: 'SG', taxLabel: 'GST' },
  { code: 'IN', label: 'India', currency: 'INR', market: 'IN', taxLabel: 'GST' },
  { code: 'AU', label: 'Australia', currency: 'AUD', market: 'AU', taxLabel: 'GST' },
];

const LAUNCH_COUNTRY_CODES = new Set<string>(['US', 'GB', 'SG', 'IN', 'AU']);

function isLaunchCountry(value: string): value is LaunchCountry {
  return LAUNCH_COUNTRY_CODES.has(value);
}

export function launchCountriesFromProfiles(profiles: MarketProfile[]): LaunchCountryOption[] {
  const options = profiles
    .flatMap((profile): LaunchCountryOption[] => {
      if (!isLaunchCountry(profile.country)) return [];
      return [
        {
          code: profile.country,
          label: profile.country_name,
          currency: profile.base_currency,
          market: profile.market,
          taxLabel: profile.tax_label,
        },
      ];
    });
  return options.length === 0 ? LAUNCH_COUNTRIES : options;
}

@Injectable({ providedIn: 'root' })
export class SignupService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private supabaseSvc = inject(SupabaseService);

  private get supabaseClient() {
    return this.supabaseSvc.client;
  }

  async fetchMarketProfiles(): Promise<MarketProfile[]> {
    const headers = new HttpHeaders({ 'skip-auth': '1' });
    return firstValueFrom(
      this.http.get<MarketProfile[]>(
        `${environment.apiUrl}/api/v1/localization/market-profiles`,
        { headers },
      ),
    );
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
