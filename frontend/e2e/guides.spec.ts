import { expect, test } from '@playwright/test';

test.describe('Public guides and tutorials', () => {
  test('discovers the guide library from the homepage', async ({ page }) => {
    await page.goto('/');

    const guides = page.getByRole('region', { name: /user guides and tutorials/i });
    await expect(guides).toBeVisible();
    await expect(guides.getByRole('heading', { name: /user guides & tutorials/i })).toBeVisible();

    await guides.getByRole('link', { name: /browse all guides/i }).click();
    await expect(page).toHaveURL(/\/guides$/);
    await expect(page.getByRole('heading', { name: /learn aethos at your pace/i })).toBeVisible();
  });

  test('filters the library and reads a formatted guide', async ({ page }) => {
    await page.goto('/guides');

    await expect(page.getByRole('link', { name: /aethos ps platform user guide/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /scenario-based demo guide v2/i })).toBeVisible();

    await page.getByRole('searchbox', { name: /search guides/i }).fill('prompt');
    await expect(page.getByRole('link', { name: /aethos nous prompt library/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /scenario-based demo guide v2/i })).toBeHidden();

    await page.getByRole('link', { name: /aethos nous prompt library/i }).click();
    await expect(page).toHaveURL(/\/guides\/nous-prompt-library$/);
    await expect(page.getByRole('heading', { level: 1, name: /aethos nous prompt library/i })).toBeVisible();
    await expect(page.getByRole('navigation', { name: /on this page/i })).toBeVisible();
    await expect(page.locator('article table').first()).toBeVisible();
    await expect(page.locator('article code').first()).toBeVisible();
  });

  test('keeps guide content usable on a narrow viewport', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/guides/platform-user-guide');

    await expect(page.getByRole('heading', { level: 1, name: /aethos ps platform user guide/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /all guides/i })).toBeVisible();

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    expect(overflow).toBe(false);
  });
});
