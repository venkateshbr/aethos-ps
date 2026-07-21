import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FxRatesInspectorComponent } from './fx-rates-inspector.component';
import { SettingsComponent } from './settings.component';

describe('SettingsComponent FX provenance section', () => {
  let fixture: ComponentFixture<SettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SettingsComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    })
      .overrideComponent(SettingsComponent, {
        set: {
          imports: [FxRatesInspectorComponent],
          schemas: [NO_ERRORS_SCHEMA],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(SettingsComponent);
    fixture.detectChanges();
  });

  it('exposes the compact read-only FX inspector to authenticated Settings users', () => {
    const section = fixture.nativeElement.querySelector(
      'section[aria-labelledby="fx-rates-heading"]',
    ) as HTMLElement | null;
    expect(section).not.toBeNull();
    const text = section!.textContent?.replace(/\s+/g, ' ').trim() ?? '';
    expect(text).toContain('FX Rates');
    expect(text).toContain('Read-only lookup');
    expect(section!.querySelector('app-fx-rates-inspector')).not.toBeNull();
    expect(text).not.toMatch(/\b(?:add|edit|save|configure)\b/i);
  });
});
