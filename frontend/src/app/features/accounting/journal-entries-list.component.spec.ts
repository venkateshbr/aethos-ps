import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { JournalEntriesListComponent } from './journal-entries-list.component';

describe('JournalEntriesListComponent close period', () => {
  let fixture: ComponentFixture<JournalEntriesListComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [JournalEntriesListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(JournalEntriesListComponent);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lets an end user select June and reloads that close checklist', () => {
    const component = fixture.componentInstance;
    component.closePeriod.set('2026-07');
    spyOn(component, 'loadCloseTasks');

    fixture.detectChanges();
    http.expectOne('/api/v1/accounting/journal-entries').flush([]);
    http.expectOne('/api/v1/accounting/recurring-journal-templates').flush({ templates: [] });
    fixture.detectChanges();

    const input = fixture.nativeElement.querySelector(
      'input[aria-label="Close period"]',
    ) as HTMLInputElement | null;
    expect(input).not.toBeNull();
    expect(input?.value).toBe('2026-07');

    input!.value = '2026-06';
    input!.dispatchEvent(new Event('change'));

    expect(component.closePeriod()).toBe('2026-06');
    expect(component.loadCloseTasks).toHaveBeenCalledTimes(2);
  });
});
