import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { AuthService } from '../../core/services/auth.service';
import { CopilotComponent } from './copilot.component';

function dragEvent(files: File[]): DragEvent {
  return {
    preventDefault: () => undefined,
    dataTransfer: { types: files.length ? ['Files'] : [], files },
  } as unknown as DragEvent;
}

describe('CopilotComponent drag & drop upload (#406)', () => {
  let fixture: ComponentFixture<CopilotComponent>;
  let component: CopilotComponent;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CopilotComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: AuthService,
          useValue: { getToken: () => 'tok', getTenantId: () => 'tenant-1' },
        },
      ],
    }).compileComponents();
    // Do NOT detectChanges — that would run ngOnInit (loadThreads/SSE). We only
    // exercise the drag-drop handlers here.
    fixture = TestBed.createComponent(CopilotComponent);
    component = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
  });

  it('activates the drop overlay when files are dragged over', () => {
    component.onDragOver(dragEvent([new File(['x'], 'a.pdf')]));
    expect(component.dragActive()).toBeTrue();
  });

  it('ignores non-file drags (e.g. text selection)', () => {
    component.onDragOver(dragEvent([]));
    expect(component.dragActive()).toBeFalse();
  });

  it('clears the overlay on drag leave', () => {
    component.dragActive.set(true);
    component.onDragLeave(dragEvent([]));
    expect(component.dragActive()).toBeFalse();
  });

  it('uploads a dropped document and clears the overlay', () => {
    const file = new File(['pdf'], 'invoice.pdf', { type: 'application/pdf' });
    component.onDrop(dragEvent([file]));

    expect(component.dragActive()).toBeFalse();
    const req = http.expectOne('/api/v1/documents/upload');
    expect(req.request.method).toBe('POST');
    expect(req.request.body instanceof FormData).toBeTrue();
    req.flush({ id: 'doc-1', status: 'uploaded' });

    expect(component.uploadDocumentId()).toBe('doc-1');
    expect(component.uploadStatus()).toBe('attached');
  });

  it('does not upload when a drop carries no file', () => {
    component.onDrop(dragEvent([]));
    http.expectNone('/api/v1/documents/upload');
  });

  afterEach(() => http.verify());
});
