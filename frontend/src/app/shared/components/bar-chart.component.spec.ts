import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BarChartComponent, BarChartDatum } from './bar-chart.component';

describe('BarChartComponent', () => {
  let fixture: ComponentFixture<BarChartComponent>;

  async function setup(data: BarChartDatum[], inputs: Record<string, unknown> = {}): Promise<void> {
    await TestBed.configureTestingModule({ imports: [BarChartComponent] }).compileComponents();
    fixture = TestBed.createComponent(BarChartComponent);
    fixture.componentRef.setInput('data', data);
    for (const [k, v] of Object.entries(inputs)) fixture.componentRef.setInput(k, v);
    fixture.detectChanges();
  }

  it('renders a bar per datum with widths relative to the max', async () => {
    await setup([
      { label: 'Current', value: 100 },
      { label: '30 days', value: 50 },
    ]);
    const bars = fixture.componentInstance.bars();
    expect(bars.length).toBe(2);
    expect(bars[0].pct).toBe(100); // max
    expect(bars[1].pct).toBe(50); // half of max
    const rows = fixture.nativeElement.querySelectorAll('figure .grid');
    expect(rows.length).toBe(2);
  });

  it('formats currency values', async () => {
    await setup([{ label: 'AR', value: 1234.5 }], { format: 'currency', currency: 'SGD' });
    expect(fixture.componentInstance.bars()[0].display).toBe('SGD 1,234.50');
  });

  it('formats percent values', async () => {
    await setup([{ label: 'Utilisation', value: 82.4 }], { format: 'percent' });
    expect(fixture.componentInstance.bars()[0].display).toBe('82.4%');
  });

  it('exposes an accessible summary label', async () => {
    await setup([{ label: 'Current', value: 10 }], { title: 'AR aging' });
    const fig = fixture.nativeElement.querySelector('figure');
    expect(fig.getAttribute('role')).toBe('img');
    expect(fig.getAttribute('aria-label')).toContain('AR aging');
    expect(fig.getAttribute('aria-label')).toContain('Current: 10');
  });

  it('shows an empty state with no data', async () => {
    await setup([]);
    expect(fixture.nativeElement.textContent).toContain('No data to chart');
  });

  it('handles a zero-only dataset without dividing by zero', async () => {
    await setup([{ label: 'a', value: 0 }]);
    expect(fixture.componentInstance.bars()[0].pct).toBe(0);
  });
});
