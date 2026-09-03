import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { InboxComponent } from './inbox.component';

/**
 * Regression cover for #494.
 *
 * The queue shortcuts (J/K/A/R/E) used to be registered twice — once via
 * @HostListener and once via a (keydown) binding on the template root — so a
 * single keypress ran the handler twice: J advanced two rows and A fired two
 * approvals. The handler also had no guard for text fields, so typing the
 * mandatory duplicate-review reason inside the edit drawer approved, rejected
 * and re-opened the focused task letter by letter.
 */
describe('InboxComponent keyboard shortcuts', () => {
  function createComponent(): InboxComponent {
    TestBed.configureTestingModule({
      imports: [InboxComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    // Deliberately no detectChanges(): ngOnInit would kick off the task fetch.
    const component = TestBed.createComponent(InboxComponent).componentInstance;
    // `tasks` is a computed over `allTasks` + the kind/role filters.
    component.allTasks.set([
      { id: 'task-1', title: 'First', status: 'open' },
      { id: 'task-2', title: 'Second', status: 'open' },
      { id: 'task-3', title: 'Third', status: 'open' },
    ] as never);
    component.focusedIdx.set(0);
    return component;
  }

  function keydown(key: string, target?: Partial<HTMLElement>): KeyboardEvent {
    const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true });
    if (target) Object.defineProperty(event, 'target', { value: target });
    return event;
  }

  it('advances exactly one row per J keypress', () => {
    const component = createComponent();

    component.onKeydown(keydown('j'));

    expect(component.focusedIdx()).toBe(1);
  });

  it('retreats exactly one row per K keypress', () => {
    const component = createComponent();
    component.focusedIdx.set(2);

    component.onKeydown(keydown('k'));

    expect(component.focusedIdx()).toBe(1);
  });

  it('ignores shortcuts typed into a text field', () => {
    const component = createComponent();
    const approve = spyOn(component, 'approve');
    const reject = spyOn(component, 'reject');
    const textarea = document.createElement('textarea');

    component.onKeydown(keydown('a', textarea));
    component.onKeydown(keydown('r', textarea));
    component.onKeydown(keydown('j', textarea));

    expect(approve).not.toHaveBeenCalled();
    expect(reject).not.toHaveBeenCalled();
    expect(component.focusedIdx()).toBe(0);
  });

  it('ignores shortcuts while the approve-with-edits drawer is open', () => {
    const component = createComponent();
    const approve = spyOn(component, 'approve');
    component.editingTask.set({ id: 'task-1', title: 'First', status: 'open' } as never);

    component.onKeydown(keydown('a'));

    expect(approve).not.toHaveBeenCalled();
  });

  it('ignores shortcuts pressed with a modifier', () => {
    const component = createComponent();
    const approve = spyOn(component, 'approve');
    const event = new KeyboardEvent('keydown', { key: 'a', metaKey: true, cancelable: true });

    component.onKeydown(event);

    expect(approve).not.toHaveBeenCalled();
  });

  it('approves the focused task exactly once for a bare A', () => {
    const component = createComponent();
    const approve = spyOn(component, 'approve');

    component.onKeydown(keydown('a'));

    expect(approve).toHaveBeenCalledTimes(1);
  });
});
